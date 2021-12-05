from datetime import date, datetime, timedelta
from functools import wraps
from io import StringIO
import csv

import flask
from flask import session, redirect, url_for, request, flash, abort
from flask.helpers import make_response
from flask.templating import render_template
from sqlalchemy.exc import IntegrityError
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from space_trace import app, db
from space_trace.certificates import (
    detect_and_attach_cert,
)
from space_trace.jokes import get_daily_joke
from space_trace.models import User, Visit

# Decorators
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
            return redirect(url_for("login"))

        flask.g.user = user
        return f(*args, **kwargs)

    return wrapper


def require_admin(f):
    @wraps(f)
    @require_login
    def wrapper(*args, **kwargs):
        if flask.g.user.email not in app.config["ADMINS"]:
            flash("You are not an admin, what were you thinking?", "danger")
            return redirect(url_for("home"))

        return f(*args, **kwargs)

    return wrapper


def require_vaccinated(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = flask.g.user
        if user.vaccinated_till is None or user.vaccinated_till < date.today():
            flash("You need to upload a vaccination certificate.", "info")
            return redirect(url_for("cert"))

        return f(*args, **kwargs)

    return wrapper


def get_active_visit(user: User) -> Visit:
    # A visit that is less than 12h old
    cutoff_timestamp = datetime.now() - timedelta(hours=12)
    return Visit.query.filter(
        db.and_(Visit.user == user.id, Visit.timestamp > cutoff_timestamp)
    ).first()


@app.get("/")
@require_login
@require_vaccinated
def home():
    user = flask.g.user

    visit = get_active_visit(user)
    visit_deadline = None
    if visit is not None:
        visit_deadline = visit.timestamp + timedelta(hours=12)

    joke = None
    if user.email in app.config["JOKE_TARGETS"]:
        joke = get_daily_joke()

    expires_in = user.vaccinated_till - date.today()
    if expires_in < timedelta(days=21):
        color = "warning" if expires_in > timedelta(days=7) else "danger"
        flash(
            f"Your vaccination certificate will expire in {expires_in} days.",
            color,
        )

    return render_template(
        "visit.html",
        user=user,
        visit=visit,
        visit_deadline=visit_deadline,
        joke=joke,
    )


@app.post("/")
@require_login
@require_vaccinated
def add_visit():
    user = flask.g.user

    # Don't enter a visit if there is already one for today
    visit = get_active_visit(user)
    if visit is not None:
        flash("You are already registered for today", "warning")
        return redirect(url_for("home"))

    # Create a new visit
    visit = Visit(date.today(), user.id)
    db.session.add(visit)
    db.session.commit()
    return redirect(url_for("home"))


@app.get("/cert")
@require_login
def cert():
    user = flask.g.user

    is_vaccinated = (
        user.vaccinated_till is not None
        and user.vaccinated_till > date.today()
    )

    return render_template("cert.html", user=user, is_vaccinated=is_vaccinated)


@app.post("/cert")
@require_login
def upload_cert():
    user = flask.g.user

    file = request.files["file"]
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == "":
        flash("No file seleceted", "warning")
        return redirect(request.url)

    try:
        detect_and_attach_cert(file, user)
    except IntegrityError:
        flash("This certificate was already uploaded", "warning")
        return redirect(request.url)
    except Exception as e:
        if hasattr(e, "message"):
            message = e.message
        else:
            message = str(e)
        flash(message, "danger")
        return redirect(request.url)

    flash(
        "Successfully uploaded certificate "
        f"which is valid till {user.vaccinated_till}",
        "success",
    )
    return redirect(url_for("home"))


@app.post("/cert-delete")
@require_login
def delete_cert():
    user = flask.g.user

    if user.vaccinated_till == None:
        flash("You don't have a certificate to delete", "warning")
        return redirect(url_for("cert"))

    db.session.query(User).filter(User.id == user.id).update(
        {"vaccinated_till": None}
    )
    db.session.commit()

    flash("Successfully deleted your certificate", "success")
    return redirect(url_for("cert"))


@app.get("/admin")
@require_admin
def admin():
    return render_template("admin.html", user=flask.g.user, now=datetime.now())


@app.get("/contacts.csv")
@require_admin
def contacts_csv():
    format = "%Y-%m-%d"
    start = datetime.strptime(request.args.get("startDate"), format)
    end = datetime.strptime(request.args.get("endDate"), format)
    if start > end:
        flash("End date cannot be before start date.", "warning")
        return redirect("admin")

    # This may look weired but we need to do a bit of arithmetic with both
    # timestamps. At the moment both timestamps point to the
    # start of the day (0:00) but end should point to the last minute so if both
    # point to the same day one whole day gets selected.
    # Actually start should point to 12h before that because members that only
    # logged in 12h bevore are still considered as in the HQ.
    start = start - timedelta(hours=12)
    end = end + timedelta(hours=24)

    # Get all email adresses of people logged in that time period
    users = (
        db.session.query(User)
        .filter(User.id == Visit.user)
        .filter(db.and_(Visit.timestamp > start, Visit.timestamp < end))
        .all()
    )

    if len(users) == 0:
        flash("No members were in the HQ at that time 👍", "success")
        return redirect("admin")

    # Convert the mails to names
    names = []
    for user in users:
        first, last = user.email.split("@")[0].split(".")
        names.append((first, last))

    # Convert to a csv
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["first name", "last name"])

    for name in names:
        cw.writerow(name)

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@app.get("/help")
@maybe_load_user
def help():
    return render_template("help.html", user=flask.g.user)


@app.get("/statistic")
@maybe_load_user
def statistic():
    total_users = User.query.count()
    total_visits = Visit.query.count()

    cutoff_timestamp = datetime.now() - timedelta(hours=12)
    active_visits = Visit.query.filter(
        Visit.timestamp > cutoff_timestamp
    ).count()

    active_users = None
    if flask.g.user is not None:
        users = (
            db.session.query(User)
            .filter(User.id == Visit.user)
            .filter(Visit.timestamp > cutoff_timestamp)
            .all()
        )

        active_users = []
        for user in users:
            first, last = user.email.split("@")[0].split(".")
            active_users.append((first.capitalize(), last.capitalize()))

        active_users = sorted(active_users, key=lambda n: n[0])

    return render_template(
        "statistic.html",
        user=flask.g.user,
        total_users=total_users,
        total_visits=total_visits,
        active_visits=active_visits,
        active_users=active_users,
    )


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
        # To avoid 'Open Redirect' attacks, before execute the redirection confirm
        # the value of the request.form['RelayState'] is a trusted URL.
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
