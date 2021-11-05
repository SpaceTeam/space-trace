import cv2
import sys
import base45
import zlib
import flynn
import json
from pyzbar.pyzbar import decode


# Usage: `python3 decode-example.py qr.png`


def main():
    # initalize the cam
    if len(sys.argv) == 2:
        img = cv2.imread(sys.argv[1])
    else:
        img = cv2.imread("qr.jpeg")
    # initialize the cv2 QRCode detector
    # detect and decode
    result = decode(img)
    if result == []:
        print("Not Detected!")
        sys.exit(1)

    # decode base45
    data_zlib = base45.b45decode(result[0].data[4:])

    # decompress zlib
    cose_data = zlib.decompress(data_zlib)

    # decode cose
    cbor_data = flynn.decoder.loads(cose_data)[1][2]

    # decode cbor
    data = flynn.decoder.loads(cbor_data)

    # show the data
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
