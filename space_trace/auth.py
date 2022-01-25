from functools import wraps

import flask
from flask import (
    abort,
    render_template,
    request,
    session,
    redirect,
    url_for,
    flash,
)
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from space_trace import app, db
from space_trace.models import User


def maybe_load_user(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = None
        if "username" in session:
            user = User.query.filter(User.email == session["username"]).first()

        flask.g.user = user
        return f(*args, **kwargs)

    return wrapper


def require_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))

        user = User.query.filter(User.email == session["username"]).first()
        if user is None:
            session.pop("username", None)
            return redirect(url_for("login"))

        flask.g.user = user
        return f(*args, **kwargs)

    return wrapper


def require_admin(f):
    @wraps(f)
    @require_login
    def wrapper(*args, **kwargs):
        if not flask.g.user.is_admin():
            flash("You are not an admin, what were you thinking?", "danger")
            return redirect(url_for("home"))

        return f(*args, **kwargs)

    return wrapper


def require_vaccinated(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = flask.g.user
        if not user.is_vaccinated():
            flash("You need to upload a vaccination certificate.", "info")
            return redirect(url_for("cert"))

        return f(*args, **kwargs)

    return wrapper


def init_saml_auth(req):
    auth = OneLogin_Saml2_Auth(
        req, custom_base_path=app.config["SAML_ST_PATH"]
    )
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
    session.permanent = True

    self_url = OneLogin_Saml2_Utils.get_self_url(req)
    if "RelayState" in request.form and self_url != request.form["RelayState"]:
        # To avoid 'Open Redirect' attacks, before execute the redirection
        # confirm the value of the request.form['RelayState'] is a trusted URL.
        return redirect(auth.redirect_to(request.form["RelayState"]))

    return redirect(url_for("home"))


@app.get("/login-debug")
def login_debug():
    if app.env != "development":
        abort(404)

    email = app.config["DEBUG_EMAIL"]
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
