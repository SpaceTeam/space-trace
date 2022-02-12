import click
from space_trace import app, db
from space_trace.models import User, Visit


@app.cli.command("delete-debug-user")
def delete_debug_user():
    email = app.config["DEBUG_EMAIL"]
    user = User.query.filter(User.email == email).first()
    if user is None:
        print("😴 Debug user is not in the DB... nothing to do here")
        return

    # Delete all visits and the user
    db.session.query(Visit).filter(Visit.user == user.id).delete()
    db.session.query(User).filter(User.id == user.id).delete()
    db.session.commit()
    print("✅ Deleted debug user")


@app.cli.command("delete-debug-visits")
def delete_debug_visits():
    email = app.config["DEBUG_EMAIL"]
    user = User.query.filter(User.email == email).first()
    if user is None:
        print("😴 Debug user is not in the DB... nothing to do here")
        return

    # Delete all visits
    db.session.query(Visit).filter(Visit.user == user.id).delete()
    db.session.commit()
    print("✅ Deleted debug visits")
