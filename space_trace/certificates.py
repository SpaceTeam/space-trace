import os
from typing import Any, Dict
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

from space_trace import app
from space_trace.models import User

# Source: https://github.com/ehn-dcc-development/ehn-dcc-schema/blob/release/1.3.0/valuesets/disease-agent-targeted.json
COVID_19_ID = "840539006"


class CertificateException(Exception):
    """
    A custom exception for this module. This Exception has always the message
    field set to a useful description you can show the user.
    """

    def __init__(self, message):
        super().__init__(message)


def calc_vaccinated_till(data: Any) -> date:
    """
    Processes a cose vaccine document and returns the date it will expire.

    Raises CertificateException if this is not the last shot or if the certificate is
    already expired.
    """
    hcert = data[-260][1]["v"][0]
    vaccination_date = date.fromisoformat(hcert["dt"])
    valid_until = None

    # Check if it is Johnson
    if hcert["sd"] == 1 and hcert["dn"] == 1:
        raise CertificateException(
            "With this certificate you are not fully immunized. (1/1)"
        )

    # Check if it is the last dosis (with edge-case dosis count higher than dosis total)
    elif hcert["dn"] < hcert["sd"]:
        raise CertificateException("With this certificate you are not fully immunized.")

    # First set of vaccinations is 180 days valid
    elif hcert["sd"] == 2:
        valid_until = vaccination_date + timedelta(days=180)

    # Otherwise it is 270 days
    else:
        valid_until = vaccination_date + timedelta(days=270)

    if valid_until < date.today():
        raise CertificateException("This certificate is already expired.")

    return valid_until


def canonicalize_name(name: str) -> str:
    """
    Normalize the name strings from certificates and emails so that they
    hopefully match.
    """
    name = name.upper()
    for c in "-.,<> ":
        name = name.replace(c, "")
    return name


def assert_cert_belong_to(cert_data: any, user: User):
    """
    Raises a CertificateException if the certificate doesn't belong to
    the user.
    """

    # Parse the users name form the email
    [first_name, last_name] = user.email.split("@")[0].split(".")
    first_name = canonicalize_name(first_name)
    last_name = canonicalize_name(last_name)
    first_name_cert = canonicalize_name(cert_data[-260][1]["nam"]["gnt"])
    last_name_cert = canonicalize_name(cert_data[-260][1]["nam"]["fnt"])

    # Using `in` because sometimes the emails don't contain the full name
    if first_name not in first_name_cert or last_name not in last_name_cert:
        raise CertificateException(
            "The name in the certificate "
            f" '{first_name_cert} {last_name_cert}' "
            f"does not match your name '{first_name} {last_name}'!"
        )


def fetch_austria_data(ressource: str):
    """
    Download the trustlist from the austrian national endpoint.
    Raises CertificateException if the trustlist cannot be downloaded.

    More documentation about it can be found here:
    https://github.com/Federal-Ministry-of-Health-AT/green-pass-overview#details-on-trust-listsbusiness-rulesvalue-sets
    """
    # Check if the cache is still hot
    cache_filename = os.path.join(app.instance_path, f"{ressource}.cache")
    try:
        with open(cache_filename, "rb") as f:
            cache_time = os.path.getmtime(f)
            if (time.time() - cache_time) / 3600 > 12:
                raise CertificateException()

            return cbor2.loads(f.read())
    except Exception:
        pass

    # Not in cache so lets download it
    r = requests.get(f"https://dgc-trust.qr.gv.at/{ressource}")
    if r.status_code != 200:
        raise CertificateException("Unable to reach austria public key gateway")
    content = r.content

    # Update the cache
    with open(cache_filename, "wb") as f:
        f.write(content)

    return cbor2.loads(content)


def assert_cert_sign(cose_data: bytes):
    """
    Verify that the signature of the cose document is valid.
    Raises CertificateException if the signature cannot be verified.

    This code is heavily inspired from:
    https://github.com/lazka/pygraz-covid-cert
    """
    cose_msg = CoseMessage.decode(cose_data)
    required_kid = cose_msg.get_attr(cose.headers.KID)

    trustlist = fetch_austria_data("trustlist")
    for entry in trustlist["c"]:
        kid = entry["i"]
        cert = entry["c"]
        if kid == required_kid:
            break
    else:
        raise CertificateException(
            "Unable validate certificate signature: " f"kid '{required_kid}' not found"
        )
    found_cert = cert

    NOW = datetime.now(timezone.utc)
    cert = x509.load_der_x509_certificate(found_cert)
    if NOW < cert.not_valid_before.replace(tzinfo=timezone.utc):
        raise CertificateException("cert not valid")
    if NOW > cert.not_valid_after.replace(tzinfo=timezone.utc):
        raise CertificateException("cert not valid")

    # Convert the CERT to a COSE key and verify the signature
    # WARNING: we assume ES256 here but all other algorithms are allowed too
    assert cose_msg.get_attr(cose.headers.Algorithm).fullname == "ES256"
    public_key = cert.public_key()
    x = public_key.public_numbers().x.to_bytes(32, "big")
    y = public_key.public_numbers().y.to_bytes(32, "big")
    cose_key = EC2Key(crv="P_256", x=x, y=y)
    cose_msg.key = cose_key
    if not cose_msg.verify_signature():
        raise CertificateException("Unable to validate certificate signature")
    print("Validated certificate :)")


def detect_and_attach_cert(file: FileStorage, user: User) -> None:
    """
    Detects, decodes and verfies the certificate in the file and updates the
    users fields vaccinated_till or tested_till.

    Raises CertificateException if something goes wrong.
    """

    # if the file is a pdf convert it to an image
    if file.filename.rsplit(".", 1)[1].lower() == "pdf":
        img = convert_from_bytes(file.read())[0]
    else:
        img = Image.open(file)

    # decode the qr code
    result = decode(img)
    if result == []:
        raise CertificateException("No QR Code was detected in the image")

    # decode base45
    data_zlib = base45.b45decode(result[0].data[4:])

    # decompress zlib
    cose_data = zlib.decompress(data_zlib)

    # TODO: I think cbor2 is a more modern library than flynn
    # decode cose
    cbor_data = flynn.decoder.loads(cose_data)[1][2]

    # decode cbor
    data = flynn.decoder.loads(cbor_data)

    # Verify that the user belongs to that certificate
    assert_cert_belong_to(data, user)

    # Verify the certificate signature
    assert_cert_sign(cose_data)

    if "v" in data[-260][1]:
        attach_vaccine(data, user)
    elif "r" in data[-260][1]:
        attach_recovery(data, user)
    elif "t" in data[-260][1]:
        # Only racing team members can upload tests or specially whitelisted
        # users
        if user.team == "racing" or user.medical_exception:
            attach_test(data, user)
        else:
            raise CertificateException(
                "The certificate must be for vaccination or recovery, we don't allow tests!"
            )
    else:
        raise CertificateException(
            "Cannot recognize certificate type, don't know what to do here."
        )


def attach_test(data: Dict, user: User):
    # Verify the disease in the certificate
    if COVID_19_ID != data[-260][1]["t"][0]["tg"]:
        raise CertificateException("The test must be for covid19")

    # Verify that test was negative
    if "260415000" != data[-260][1]["t"][0]["tr"]:
        id = data[-260][1]["t"][0]["tr"]
        raise CertificateException(f"The test was not negative ({id})")

    # Verify it's a pcr test
    if "nm" not in data[-260][1]["t"][0]:
        raise CertificateException("We only allow PCR tests.")

    valid_till = datetime.fromisoformat(data[-260][1]["t"][0]["sc"][:-1]) + timedelta(
        hours=48
    )

    # Verify the test is still valid
    if valid_till <= datetime.now():
        raise CertificateException("This test certificate already expired!")

    # Verify that the user hasn't already uploaded a newer test
    if user.tested_till and valid_till <= user.tested_till:
        raise CertificateException("You already have uploaded a newer test!")

    # Update the user
    user.tested_till = valid_till


def attach_recovery(data: Dict, user: User):
    # Verify the disease in the certificate
    if COVID_19_ID != data[-260][1]["r"][0]["tg"]:
        raise CertificateException("The certificate must be for covid19")

    # Recovery certificates can be issued before they are valid. Verify now that
    # the certificate is already valid.
    valid_from = date.fromisoformat(data[-260][1]["r"][0]["df"])
    if valid_from > date.today():
        raise CertificateException(
            f"The recovery certificate is not yet valid, come back at {valid_from}!"
        )

    # Verify that the recovery is newer that whatever is currently stored
    valid_till = date.fromisoformat(data[-260][1]["r"][0]["du"])
    if user.vaccinated_till is not None:
        if user.vaccinated_till > valid_till:
            raise CertificateException("You already uploaded a newer certificate")
        elif user.vaccinated_till == valid_till:
            raise CertificateException("You already uploaded this certificate")

    # Update the user
    # TODO: Yes we update the vaccinated field even though the user is recoverd,
    # we currently don't have a concept in the db for recovered and it honestly
    # doesn't make sense to differentiate between them. The solution is probably
    # to rename the DB column to something like "valid_till".
    user.vaccinated_till = valid_till


def attach_vaccine(data: Dict, user: User):
    # Verify the disease in the certificate
    if COVID_19_ID != data[-260][1]["v"][0]["tg"]:
        raise CertificateException("The certificate must be for covid19")

    # Verify that this vaccination is newer than the last one
    vaccinated_till = calc_vaccinated_till(data)
    if user.vaccinated_till is not None:
        if user.vaccinated_till > vaccinated_till:
            raise CertificateException("You already uploaded a newer certificate")
        elif user.vaccinated_till == vaccinated_till:
            raise CertificateException("You already uploaded this certificate")

    # Update the user
    user.vaccinated_till = vaccinated_till
