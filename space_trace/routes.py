from datetime import date
from flask import session, redirect, url_for, request, flash
from flask.templating import render_template
from space_trace import app, db
from space_trace.certificates import detect_cert, is_cert_expired
from space_trace.models import Certificate, User, Visit


@app.route("/")
def home():
    if "username" not in session:
        return "You are not logged in"

    user = User.query.filter(User.email == session["username"]).first()
    return f"You are: id={user.id}, name={user.name}"


@app.get("/visit")
def visit():
    # load the user
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter(User.email == session["username"]).first()
    if user is None:
        return redirect(url_for("login"))

    cert = (
        Certificate.query.filter(Certificate.user == user.id)
        .order_by(Certificate.date.desc())
        .first()
    )
    if cert is None or is_cert_expired(cert):
        return redirect(url_for("cert"))

    visit = Visit.query.filter(
        Visit.date == date.today() and Visit.user == user.id
    ).first()

    return render_template(
        "visit.html", user=user, certificate=cert, visit=visit
    )


@app.post("/visit")
def add_visit():
    # load the user
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter(User.email == session["username"]).first()
    if user is None:
        return redirect(url_for("login"))

    cert = (
        Certificate.query.filter(Certificate.user == user.id)
        .order_by(Certificate.date.desc())
        .first()
    )
    if cert is None or is_cert_expired(cert):
        return redirect(url_for("cert"))

    visit = Visit.query.filter(
        Visit.date == date.today() and Visit.user == user.id
    ).first()
    if visit is not None:
        return redirect(url_for("visit"))

    visit = Visit(date.today(), user.id)
    db.session.add(visit)
    db.session.commit()
    return redirect(url_for("visit"))


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
        flash("No selected file")
        return redirect(request.url)

    # bytes = file.read()

    cert = detect_cert(file)
    cert.user = user.id
    db.session.add(cert)
    db.session.commit()
    return redirect("visit")


# TODO: theses are test logins, they will be removed
@app.get("/login")
def login():
    return render_template("login.html")


@app.post("/login")
def add_login():
    session["username"] = "flotschi@email.com"
    return redirect(url_for("visit"))


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))
