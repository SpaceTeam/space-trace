import cv2
import sys
from pyzbar.pyzbar import decode


def main():
    # initalize the cam
    if len(sys.argv) == 2:
        img = cv2.imread(sys.argv[1])
    else:
        img = cv2.imread("qr4.jpeg")
    # initialize the cv2 QRCode detector
    # detect and decode
    result = decode(img)
    if result == []:
        print("Not Detected!")
        sys.exit(1)

    # Get the raw data from the qrcode
    print(result[0].data)


if __name__ == "__main__":
    main()
