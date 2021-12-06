import os
from PIL import Image
import base45
import zlib
import cbor2
import flynn
from pyzbar.pyzbar import decode
from datetime import date, datetime, time, timedelta, timezone
from cose.messages import CoseMessage
from cryptography import x509
from cose.keys import EC2Key
import cose.headers
import requests
from werkzeug.datastructures import FileStorage
from pdf2image import convert_from_bytes

from space_trace import app, db
from space_trace.models import User

# Source: https://github.com/ehn-dcc-development/ehn-dcc-schema/blob/release/1.3.0/valuesets/disease-agent-targeted.json
COVID_19_ID = "840539006"


def calc_vacinated_till(data) -> date:
    hcert = data[-260][1]["v"][0]
    vaccination_date = date.fromisoformat(hcert["dt"])
    valid_until = None

    # Check if it is the last dosis
    if hcert["dn"] != hcert["sd"]:
        raise Exception("With this certificate you are not fully immunized.")

    # Check if it is johnson then its only 270 days or till first of 2022
    if hcert["sd"] == 1:
        valid_until = min(
            vaccination_date + timedelta(days=270),
            date(2022, 1, 3),
        )

    # Otherwise it is 270 days
    else:
        valid_until = vaccination_date + timedelta(days=270)

    if valid_until < date.today():
        raise Exception("This certificate is already expired.")

    return valid_until


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
    first_name_cert = canonicalize_name(cert_data[-260][1]["nam"]["gnt"])
    last_name_cert = canonicalize_name(cert_data[-260][1]["nam"]["fnt"])

    # Using in because sometimes the emails don't contain the full name
    if first_name not in first_name_cert or last_name not in last_name_cert:
        raise Exception(
            "The name in the certificate "
            f" '{first_name_cert} {last_name_cert}' "
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


def detect_and_attach_cert(file: FileStorage, user: User) -> None:
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

    # Verify that this is a vaccine certificate
    if "v" not in data[-260][1]:
        message = "The certificate must be for a vaccination"
        if "t" in data[-260][1]:
            message += ", we don't allow tests"
        if "r" in data[-260][1]:
            message += ", we don't allow recovered"
        raise Exception(message)

    # Verify the data now
    if COVID_19_ID != data[-260][1]["v"][0]["tg"]:
        raise Exception("The certificate must be for covid19")

    # Verify the certificate signature
    assert_cert_sign(cose_data)

    # Verify that the user belongs to that certificate
    assert_cert_belong_to(data, user)

    # Verify that this vaccination is newer than the last one
    vaccinated_till = calc_vacinated_till(data)
    if user.vaccinated_till is not None:
        if user.vaccinated_till > vaccinated_till:
            raise Exception("You already uploaded a newer certificate")
        elif user.vaccinated_till == vaccinated_till:
            raise Exception("You already uploaded this certificate")

    # Update the user
    db.session.query(User).filter(User.id == user.id).update(
        {"vaccinated_till": vaccinated_till}
    )
    user = User.query.filter(User.id == user.id).first()
    db.session.commit()
