from datetime import date, datetime, timedelta
from io import BytesIO
from flask import session, redirect, url_for, request, flash, abort
from flask.templating import render_template
from sqlalchemy.exc import IntegrityError
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from space_trace import app, db
from space_trace.certificates import detect_cert, is_cert_expired
from space_trace.models import Certificate, User, Visit


def init_saml_auth(req):
    auth = OneLogin_Saml2_Auth(req, custom_base_path=app.config["SAML_PATH"])
    return auth


def prepare_flask_request(request):
    # If server is behind proxys or balancers use the HTTP_X_FORWARDED fields
    return {
        "https": "on" if request.scheme == "https" else "off",
        "http_host": request.host,
        "script_name": request.path,
        "get_data": request.args.copy(),
        "post_data": request.form.copy(),
    }


def get_last_cert(user: User) -> Certificate:
    return (
        Certificate.query.filter(Certificate.user == user.id)
        .order_by(Certificate.date.desc())
        .first()
    )


def get_active_visit(user: User) -> Visit:
    # A visit that is less than 12h old
    cutoff_timestamp = datetime.now() - timedelta(hours=12)
    return Visit.query.filter(
        db.and_(Visit.user == user.id, Visit.timestamp > cutoff_timestamp)
    ).first()


@app.get("/")
def home():
    # Load the user
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter(User.email == session["username"]).first()
    if user is None:
        return redirect(url_for("login"))

    # Load the certificate
    cert = get_last_cert(user)
    if cert is None or is_cert_expired(cert):
        return redirect(url_for("cert"))

    # Load if currently visited
    visit = get_active_visit(user)
    visit_deadline = None
    if visit is not None:
        visit_deadline = visit.timestamp + timedelta(hours=12)

    return render_template(
        "visit.html",
        user=user,
        certificate=cert,
        visit=visit,
        visit_deadline=visit_deadline,
    )


@app.post("/")
def add_visit():
    # Load the user
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter(User.email == session["username"]).first()
    if user is None:
        return redirect(url_for("login"))

    # Verify that the user has a valid certificate
    cert = get_last_cert(user)
    if cert is None or is_cert_expired(cert):
        return redirect(url_for("cert"))

    # Don't enter a visit if there is already one for today
    visit = get_active_visit(user)
    if visit is not None:
        flash("You are already registered for today", "warning")
        return redirect(url_for("home"))

    visit = Visit(date.today(), user.id)
    db.session.add(visit)
    db.session.commit()
    return redirect(url_for("home"))


@app.get("/cert")
def cert():
    # load the user
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter(User.email == session["username"]).first()
    if user is None:
        return redirect(url_for("login"))

    certs = Certificate.query.filter(Certificate.user == user.id).order_by(
        Certificate.date.desc()
    )

    return render_template("cert.html", user=user, certificates=certs)


@app.post("/cert")
def upload_cert():
    # load the user
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter(User.email == session["username"]).first()
    if user is None:
        return redirect(url_for("login"))

    file = request.files["file"]
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == "":
        flash("No file seleceted", "warning")
        return redirect(request.url)

    try:
        cert = detect_cert(file, user)
    except Exception as e:
        if hasattr(e, "message"):
            message = e.message
        else:
            message = str(e)
        flash(message, "warning")
        return redirect(request.url)

    if is_cert_expired(cert):
        flash("This certificate is already expired", "danger")
        return redirect(request.url)

    try:
        db.session.add(cert)
        db.session.commit()
    except IntegrityError:
        flash("This certificate was already uploaded", "warning")
        return redirect(request.url)

    return redirect(url_for("home"))


@app.get("/help")
def help():
    return render_template("help.html")


@app.get("/statistic")
def statistic():
    return render_template("statistic.html")


@app.get("/login")
def login():
    return render_template("login.html")


@app.post("/login")
def add_login():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)

    return_to = "https://covid.tust.at/"
    sso_built_url = auth.login(return_to)
    session["AuthNRequestID"] = auth.get_last_request_id()
    return redirect(sso_built_url)


@app.route("/saml", methods=["POST", "GET"])
def saml_response():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    errors = []

    request_id = None
    if "AuthNRequestID" in session:
        request_id = session["AuthNRequestID"]

    auth.process_response(request_id=request_id)
    errors = auth.get_errors()
    if len(errors) != 0:
        flash(f"An error occured during login: {errors}", "danger")
        return redirect(url_for("login"))

    if "AuthNRequestID" in session:
        del session["AuthNRequestID"]
    username = str(auth.get_nameid())

    user = User.query.filter(User.email == username).first()
    if user is None:
        firstname = username.split(".", 1)[0].capitalize()
        user = User(firstname, username)
        db.session.add(user)
        db.session.commit()

    session["username"] = username

    self_url = OneLogin_Saml2_Utils.get_self_url(req)
    if "RelayState" in request.form and self_url != request.form["RelayState"]:
        # To avoid 'Open Redirect' attacks, before execute the redirection confirm
        # the value of the request.form['RelayState'] is a trusted URL.
        return redirect(auth.redirect_to(request.form["RelayState"]))

    return redirect(url_for("home"))


@app.get("/login-debug")
def login_debug():
    if app.env != "development":
        abort(404)

    email = "debug@email.com"
    firstname = "Testuser"
    session["username"] = email
    try:
        user = User(firstname, email)
        db.session.add(user)
        db.session.commit()
    except Exception:
        pass
    return redirect(url_for("home"))


@app.get("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))
