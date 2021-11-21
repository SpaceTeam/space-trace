from PIL import Image
import base45
import zlib
import flynn
import json
from pyzbar.pyzbar import decode
from datetime import date

from space_trace.models import Certificate

# Source: https://github.com/ehn-dcc-development/ehn-dcc-schema/blob/release/1.3.0/valuesets/disease-agent-targeted.json
COVID_19_ID = "840539006"

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


CERT_EXPIRE_DURATION = 270


def is_cert_expired(cert) -> bool:
    # TODO: distinguish between first and second stab and Jonnson
    days_since = abs((date.today() - cert.date).days)
    return days_since > CERT_EXPIRE_DURATION


def detect_cert(file, user) -> Certificate:
    # decode the qr code
    img = Image.open(file)
    result = decode(img)
    if result == []:
        raise Exception(message="No QR Code was detected in the image")

    # decode base45
    data_zlib = base45.b45decode(result[0].data[4:])

    # decompress zlib
    cose_data = zlib.decompress(data_zlib)

    # decode cose
    cbor_data = flynn.decoder.loads(cose_data)[1][2]

    # decode cbor
    data = flynn.decoder.loads(cbor_data)

    # Verify the data now
    if COVID_19_ID != data[-260][1]["v"][0]["tg"]:
        raise Exception(message="The certificate musst be for covid19")

    # TODO: Verify the certificate signature

    # TODO: verify that the user belongs to that certificate

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
