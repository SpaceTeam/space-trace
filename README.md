# space-trace

Tracing service for the [TU Wien Spaceteam](https://spaceteam.at/?lang=en).
![image](https://user-images.githubusercontent.com/21206831/142742633-6771a208-5791-4d08-a6c3-34dc1459ab33.png)


## Quick-Start

Install Python3.9 and zbar

Install all dependencies with:

```bash
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=space_trace FLASK_ENV=development
```

Create the database file with:

```
$ python
>>> from space_trace import db
>>> db.create_all()
```

Start the server with

```
flask run
```

This launces a simple webserver which can only be accessed from the localhost.

**Note:** Don't use this server in production, it is insecure and low
performance.

## Development

- Use [`black`](https://github.com/psf/black) to format code
- Try to follow the python style guide [PEP 8](https://www.python.org/dev/peps/pep-0008/)

## Roadmap

### Alpha 1

- [x] Decode a EU Certificate

### Alpha 2

- [x] Login with SAML
- [x] Upload Picture of QR Code (no verification)
- [x] Register for a day
- [ ] Export contacts on day basis

### Beta

- [ ] Allow PDF upload
- [ ] Allow taking pictures from the browser
- [ ] Verify Certificates
- [ ] Admin interface

### Final Release

- [ ] Smart export (by selecting infected member not dates)
- [ ] public & private APIs so other services can integrate

## Ressources
Some links I found helpful in dealing with the certificate:

- [What's Inside the EU Green Pass QR Code?](https://gir.st/blog/greenpass.html)
- [Decoding the EU Digital Covid Certificate QR code](https://www.bartwolff.com/Blog/2021/08/08/decoding-the-eu-digital-covid-certificate-qr-code)
