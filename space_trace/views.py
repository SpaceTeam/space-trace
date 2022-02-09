from datetime import date, datetime, timedelta
from io import StringIO
from traceback import format_exception
import csv

import flask
from flask import redirect, send_file, url_for, request, flash
from flask.helpers import make_response
from flask.templating import render_template
from sqlalchemy.exc import IntegrityError

from werkzeug.exceptions import InternalServerError

from space_trace import app, db
from space_trace.auth import (
    maybe_load_user,
    require_admin,
    require_login,
    require_2g,
)
from space_trace.certificates import (
    detect_and_attach_cert,
)
from space_trace.jokes import get_daily_joke
from space_trace.models import User, Visit
from space_trace.statistics import (
    active_users,
    active_visits,
    checkins_per_hour,
    daily_usage,
    monthly_usage,
    most_frequent_users,
    total_users,
    total_visits,
)


def get_active_visit(user: User) -> Visit:
    # A visit that is less than 12h old
    cutoff_timestamp = datetime.now() - timedelta(hours=12)
    return Visit.query.filter(
        db.and_(Visit.user == user.id, Visit.timestamp > cutoff_timestamp)
    ).first()


@app.get("/")
@require_login
@require_2g
def home():
    user: User = flask.g.user

    visit = get_active_visit(user)
    visit_deadline = None
    if visit is not None:
        visit_deadline = visit.timestamp + timedelta(hours=12)

    joke = None
    if user.email in app.config["JOKE_TARGETS"]:
        joke = get_daily_joke()
    elif user.email in app.config["DISAPPOINTED_USERS"]:
        joke = "So sorry that you cannot have another developer. "
        "Currently all of our developers are busy fixing edge-cases they "
        "forgot they put in last night at 3am."

    if user.is_vaccinated():
        expires_in = user.vaccinated_till - date.today()
        if expires_in < timedelta(days=21):
            color = "warning" if expires_in > timedelta(days=7) else "danger"
            flash(
                "Your vaccination certificate will expire "
                f"in {expires_in.days} day(s).",
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
@require_2g
def add_visit():
    user: User = flask.g.user

    # Don't enter a visit if there is already one for today
    visit = get_active_visit(user)
    if visit is not None:
        flash("You are already registered for today", "warning")
        return redirect(url_for("home"))

    # Create a new visit
    visit = Visit(datetime.now(), user.id)
    db.session.add(visit)
    db.session.commit()
    return redirect(url_for("home"))


@app.get("/cert")
@require_login
def cert():
    user: User = flask.g.user
    return render_template("cert.html", user=user)


@app.post("/cert")
@require_login
def upload_cert():
    user: User = flask.g.user

    file = request.files["file"]
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == "":
        flash("No file seleceted", "warning")
        return redirect(request.url)

    try:
        detect_and_attach_cert(file, user)

        db.session.query(User).filter(User.id == user.id).update(
            {
                "vaccinated_till": user.vaccinated_till,
                "tested_till": user.tested_till,
            }
        )
        user = User.query.filter(User.id == user.id).first()
        db.session.commit()

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

    # TODO: Figure out a better method to detect if a test or certificate was
    # uploaded.
    if user.vaccinated_till and user.vaccinated_till >= date.today():
        message = (
            "Successfully uploaded a certificate "
            f"which is valid till {user.vaccinated_till}"
        )
    else:
        message = f"Successfully uploaded a test which is valid till {user.tested_till}"

    flash(message, "success")
    return redirect(url_for("home"))


@app.post("/cert-delete")
@require_login
def delete_cert():
    user: User = flask.g.user

    if user.vaccinated_till is None:
        flash("You don't have a certificate to delete", "danger")
        return redirect(url_for("cert"))

    db.session.query(User).filter(User.id == user.id).update(
        {
            "vaccinated_till": None,
        }
    )
    db.session.commit()

    flash("Successfully deleted your certificate", "success")
    return redirect(url_for("cert"))


@app.post("/test-delete")
@require_login
def delete_test():
    user: User = flask.g.user

    if user.tested_till is None:
        flash("You don't have a test to delete", "danger")
        return redirect(url_for("cert"))

    db.session.query(User).filter(User.id == user.id).update(
        {
            "tested_till": None,
        }
    )
    db.session.commit()

    flash("Successfully deleted your test", "success")
    return redirect(url_for("cert"))


@app.get("/admin")
@require_admin
def admin():
    users = User.query.order_by(User.email).all()

    return render_template(
        "admin.html",
        user=flask.g.user,
        users=users,
        checkins_per_hour=checkins_per_hour(),
        most_frequent_users=most_frequent_users(),
        daily_usage=daily_usage(),
        monthly_usage=monthly_usage(),
        now=datetime.now(),
    )


@app.get("/admin/contacts.csv")
@require_admin
def contacts_csv():
    format = "%Y-%m-%d"
    start = datetime.strptime(request.args.get("startDate"), format)
    end = datetime.strptime(request.args.get("endDate"), format)
    if start > end:
        flash("End date cannot be before start date.", "warning")
        return redirect(url_for("admin"))

    # This may look weired but we need to do a bit of arithmetic with both
    # timestamps. At the moment both timestamps point to the
    # start of the day (0:00) but end should point to the last minute so if
    # both point to the same day one whole day gets selected.
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

    # Convert to a csv
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["first name", "last name", "team"])

    for user in users:
        cw.writerow([user.first_name(), user.last_name(), user.team])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@app.get("/admin/smart-contacts.csv")
@require_admin
def smart_contacts_csv():
    format = "%Y-%m-%d"
    start = datetime.strptime(request.args.get("startDate"), format)
    infected_id = int(request.args.get("infectedId"))

    # This may look weired but we need to do a bit of arithmetic with both
    # timestamps. At the moment both timestamps point to the
    # start of the day (0:00) but end should point to the last minute so if
    # both point to the same day one whole day gets selected.
    # Actually start should point to 12h before that because members that only
    # logged in 12h bevore are still considered as in the HQ.
    start = start - timedelta(hours=12)

    # Get all contacts of the infected
    visit1: User = db.aliased(Visit)
    visit2: User = db.aliased(Visit)
    users = (
        db.session.query(User)
        .filter(visit1.user == infected_id)
        .filter(visit1.timestamp > start)
        .filter(visit2.timestamp > db.func.date(visit1.timestamp, "-12 hours"))
        .filter(visit2.timestamp < db.func.date(visit1.timestamp, "+12 hours"))
        .filter(User.id == visit2.user)
        .filter(User.id != infected_id)
        .all()
    )

    if len(users) == 0:
        flash("No members were in the HQ at that time 👍", "success")
        return redirect(url_for("admin"))

    # Convert to a csv
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["first name", "last name", "team"])

    for user in users:
        cw.writerow([user.first_name(), user.last_name(), user.team])

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
    user = flask.g.user
    return render_template(
        "statistic.html",
        user=user,
        total_users=total_users(),
        total_visits=total_visits(),
        active_visits=active_visits(),
        active_users_st=None if user is None else active_users(team="space"),
        active_users_rt=None if user is None else active_users(team="racing"),
    )


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(InternalServerError)
def handle_bad_request(e):
    return (
        render_template(
            "500.html",
            traceback="".join(
                format_exception(
                    None,
                    e.original_exception,
                    e.original_exception.__traceback__,
                )
            ),
        ),
        500,
    )


@app.get("/goots")
def goots():
    return send_file("static/goots.png")


@app.get("/crash-now")
def crash_now():
    return f"{4/0}"
