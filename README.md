# space-trace

Tracing service for the [TU Wien Spaceteam](https://spaceteam.at/?lang=en).
![Screenshot](https://user-images.githubusercontent.com/21206831/143572196-43998f10-e8f0-4427-a088-1c35c15b74b8.png)


## Getting started

Setup your development environments.

Install Python3.8 or higher, zbar, popper, libxml2

Install all dependencies with:

```bash
python3 -m venv venv
source venv/bin/activate
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

## Deployment

How we deploy this app on Ubuntu.

Install the requirements with:

```bash
sudo apt -y install python3-venv python3-pip libzbar0 libxml2-dev libxmlsec1-dev libxmlsec1-openssl poppler-utils
```

Create a virtual env with:

```bash
python3 -m venv venv
```

Create the database file with:

```
$ python
>>> from space_trace import db
>>> db.create_all()
```

Copy `instance/config_example.toml` to `instance/config.toml` and edit all
the fields in it.

Open `space-trace.service` and edit the username and all paths to the working
directory.

Start the systemd service with:

```bash
sudo cp space-trace.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable space-trace.service
sudo systemctl start space-trace.service
```

The service should now be up and running 🎉

To stop the service run:

```bash
sudo systemctl stop space-trace.service
```

To update the service to a new version (commit) run:

```bash
git pull
sudo systemctl restart space-trace.service
```

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

- [x] Allow PDF upload
- [ ] Allow taking pictures from the browser
- [x] Verify Certificates
- [ ] Admin interface

### Final Release

- [ ] Smart export (by selecting infected member not dates)
- [ ] public & private APIs so other services can integrate
- [ ] Tests and CI Pipeline to check on every commit
- [ ] statically type all function and add mypy to CI

## Resources

Some links I found helpful in dealing with the certificate:

- [What's Inside the EU Green Pass QR Code?](https://gir.st/blog/greenpass.html)
- [Decoding the EU Digital Covid Certificate QR code](https://www.bartwolff.com/Blog/2021/08/08/decoding-the-eu-digital-covid-certificate-qr-code)
- [DSC TrustList Update API](https://github.com/Digitaler-Impfnachweis/certification-apis/blob/master/dsc-update/README.md)
- [Austrian implementation of the EU Digital COVID Certificates](https://github.com/Federal-Ministry-of-Health-AT/green-pass-overview#details-on-trust-listsbusiness-rulesvalue-sets)
- [inofficial hcert-trustlist-mirror dcc (covid trustlist)](https://github.com/section42/hcert-trustlist-mirror)
- [lazka / pygraz-covid-cert](https://github.com/lazka/pygraz-covid-cert)
