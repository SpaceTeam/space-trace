from PIL import Image
import base45
import zlib
import flynn
import json
from pyzbar.pyzbar import decode
from datetime import date

from space_trace.models import Certificate

CERT_EXPIRE_DURATION = 270


def is_cert_expired(cert) -> bool:
    days_since = abs((date.today() - cert.date).days)
    return days_since > CERT_EXPIRE_DURATION


def detect_cert(file, user) -> Certificate:
    # decode the qr code
    img = Image.open(file)
    result = decode(img)
    if result == []:
        print("Not Detected!")
        return None

    # decode base45
    data_zlib = base45.b45decode(result[0].data[4:])

    # decompress zlib
    cose_data = zlib.decompress(data_zlib)

    # decode cose
    cbor_data = flynn.decoder.loads(cose_data)[1][2]

    # decode cbor
    data = flynn.decoder.loads(cbor_data)

    # TODO: verify the data now
    # TODO: verify that the user belongs to that certificate

    # create a certificate object
    json_dump = json.dumps(data)
    vaccination_date = date.fromisoformat(data[-260][1]["v"][0]["dt"])
    return Certificate(json_dump, vaccination_date, user.id)
