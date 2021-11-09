# space-trace

Tracing service for the spaceteam.

## Quick-Start

Install Python3.9 and zbar

Install all dependencies with:

```bash
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=space_trace
export FLASK_ENV=development
flask run
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

- [ ] Login with SAML
- [ ] Upload Picture of QR Code (no verification)
- [ ] Register for a day
- [ ] Export contacts on day basis

### Beta

- [ ] Allow PDF upload
- [ ] Allow taking pictures from the browser
- [ ] Verify Certificates

### Final Release

- [ ] Smart export (by selecting infected member not dates)
- [ ] public & private APIs so other services can integrate
