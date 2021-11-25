import os
import subprocess
from PIL import Image
import base45
import zlib
import cbor2
import flynn
import json
from pyzbar.pyzbar import decode
from datetime import date, datetime, time, timedelta, timezone
from dateutil.parser import isoparse
from cose.messages import CoseMessage
from cryptography import x509
from cose.keys import EC2Key
import cose.headers
import requests
from werkzeug.datastructures import FileStorage
from pdf2image import convert_from_bytes
import tempfile

from space_trace import app
from space_trace.models import Certificate, User

# Source: https://github.com/ehn-dcc-development/ehn-dcc-schema/blob/release/1.3.0/valuesets/disease-agent-targeted.json
COVID_19_ID = "840539006"

# TODO: we should get this from the Austria API
# Source: https://github.com/ehn-dcc-development/ehn-dcc-schema/blob/release/1.3.0/valuesets/vaccine-medicinal-product.json
VACCINE_MANUFACTURERS = {
    "ORG-100001699": "AstraZeneca AB",
    "ORG-100030215": "Biontech Manufacturing GmbH",
    "ORG-100001417": "Janssen-Cilag International",
    "ORG-100031184": "Moderna Biotech Spain S.L.",
    "ORG-100006270": "Curevac AG",
    "ORG-100013793": "CanSino Biologics",
    "ORG-100020693": "China Sinopharm International Corp. - Beijing location",
    "ORG-100010771": "Sinopharm Weiqida Europe Pharmaceutical s.r.o. - Prague location",
    "ORG-100024420": "Sinopharm Zhijun (Shenzhen) Pharmaceutical Co. Ltd. - Shenzhen location",
    "ORG-100032020": "Novavax CZ AS",
    "Gamaleya-Research-Institute": "Gamaleya Research Institute",
    "Vector-Institute": "Vector Institute",
    "Sinovac-Biotech": "Sinovac Biotech",
    "Bharat-Biotech": "Bharat Biotech",
}

# Source: https://github.com/ehn-dcc-development/ehn-dcc-schema/blob/release/1.3.0/valuesets/vaccine-medicinal-product.json
VACCINE_PRODUCTS = {
    "EU/1/20/1528": "Comirnaty",
    "EU/1/20/1507": "COVID-19 Vaccine Moderna",
    "EU/1/21/1529": "Vaxzevria",
    "EU/1/20/1525": "COVID-19 Vaccine Janssen",
    "CVnCoV": "CVnCoV",
    "Sputnik-V": "Sputnik-V",
    "Convidecia": "Convidecia",
    "EpiVacCorona": "EpiVacCorona",
    "BBIBP-CorV": "BBIBP-CorV",
    "Inactivated-SARS-CoV-2-Vero-Cell": "Inactivated SARS-CoV-2 (Vero Cell)",
    "CoronaVac": "CoronaVac",
    "Covaxin": "Covaxin (also known as BBV152 A, B, C)",
}


def is_cert_expired(cert) -> bool:
    hcert = json.loads(cert.data)["-260"]["1"]["v"][0]

    # Check if it is the last dosis
    if hcert["dn"] != hcert["sd"]:
        return True

    # Check if it is johnson then its only 270 days
    if hcert["sd"] == 1 and (date.today() - cert.date).days > 270:
        return True

    # Check if 360 days since second vaccination
    if (date.today() - cert.date).days > 360:
        return True

    return False


def canonicalize_name(name: str) -> str:
    name = name.upper()
    for c in "-.,<> ":
        name = name.replace(c, "")
    return name


def assert_cert_belong_to(cert_data: any, user: User):
    # Parse the users name form the email
    [first_name, last_name] = user.email.split("@")[0].split(".")
    first_name = canonicalize_name(first_name)
    last_name = canonicalize_name(last_name)
    first_name2 = canonicalize_name(cert_data[-260][1]["nam"]["gnt"])
    last_name2 = canonicalize_name(cert_data[-260][1]["nam"]["fnt"])

    if first_name != first_name2 or last_name != last_name2:
        raise Exception(
            f"The name in the certificate '{first_name2} {last_name2}' "
            f"does not match your name '{first_name} {last_name}'!"
        )


def fetch_austria_data(ressource: str):
    # Check if the cache is still hot
    cache_filename = os.path.join(app.instance_path, f"{ressource}.cache")
    try:
        with open(cache_filename, "rb") as f:
            cache_time = os.path.getmtime(f)
            if (time.time() - cache_time) / 3600 > 12:
                raise Exception()

            return cbor2.loads(f.read())
    except Exception:
        pass

    # Not in cache so lets download it
    r = requests.get(f"https://dgc-trust.qr.gv.at/{ressource}")
    if r.status_code != 200:
        raise Exception("Unable to reach austria public key gateway")
    content = r.content

    # Update the cache
    with open(cache_filename, "wb") as f:
        f.write(content)

    return cbor2.loads(content)


# This code is adapted from the following repository:
# https://github.com/lazka/pygraz-covid-cert
def assert_cert_sign(cose_data: bytes):
    cose_msg = CoseMessage.decode(cose_data)
    required_kid = cose_msg.get_attr(cose.headers.KID)

    trustlist = fetch_austria_data("trustlist")
    for entry in trustlist["c"]:
        kid = entry["i"]
        cert = entry["c"]
        if kid == required_kid:
            break
    else:
        raise Exception(
            "Unable validate certificate signature: "
            f"kid '{required_kid}' not found"
        )
    found_cert = cert

    NOW = datetime.now(timezone.utc)
    cert = x509.load_der_x509_certificate(found_cert)
    if NOW < cert.not_valid_before.replace(tzinfo=timezone.utc):
        raise Exception("cert not valid")
    if NOW > cert.not_valid_after.replace(tzinfo=timezone.utc):
        raise Exception("cert not valid")

    # Convert the CERT to a COSE key and verify the signature
    # WARNING: we assume ES256 here but all other algorithms are allowed too
    assert cose_msg.get_attr(cose.headers.Algorithm).fullname == "ES256"
    public_key = cert.public_key()
    x = public_key.public_numbers().x.to_bytes(32, "big")
    y = public_key.public_numbers().y.to_bytes(32, "big")
    cose_key = EC2Key(crv="P_256", x=x, y=y)
    cose_msg.key = cose_key
    if not cose_msg.verify_signature():
        raise Exception("Unable to validate certificate signature")
    print("Validated certificate :)")


def detect_cert(file: FileStorage, user: User) -> Certificate:
    # if the file is a pdf convert it to an image
    if file.filename.rsplit(".", 1)[1].lower() == "pdf":
        img = convert_from_bytes(file.read())[0]
    else:
        img = Image.open(file)

    # decode the qr code
    result = decode(img)
    if result == []:
        raise Exception("No QR Code was detected in the image")

    # decode base45
    data_zlib = base45.b45decode(result[0].data[4:])

    # decompress zlib
    cose_data = zlib.decompress(data_zlib)

    # TODO: I think cbor2 is a more modern library than flynn
    # decode cose
    cbor_data = flynn.decoder.loads(cose_data)[1][2]

    # decode cbor
    data = flynn.decoder.loads(cbor_data)

    # Verify the data now
    if COVID_19_ID != data[-260][1]["v"][0]["tg"]:
        raise Exception("The certificate must be for covid19")

    # Verify the certificate signature
    assert_cert_sign(cose_data)

    # Verify that the user belongs to that certificate
    assert_cert_belong_to(data, user)

    # create a certificate object
    json_dump = json.dumps(data)
    vaccination_date = date.fromisoformat(data[-260][1]["v"][0]["dt"])
    manufacturer = VACCINE_MANUFACTURERS[data[-260][1]["v"][0]["ma"]]
    product = VACCINE_PRODUCTS[data[-260][1]["v"][0]["mp"]]
    return Certificate(
        data=json_dump,
        date=vaccination_date,
        user=user.id,
        manufacturer=manufacturer,
        product=product,
    )
