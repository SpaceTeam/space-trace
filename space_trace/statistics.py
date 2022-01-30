from space_trace.models import User, Visit
import flask
from space_trace import db
from datetime import datetime, timedelta


def total_users() -> int:
    return User.query.count()


def total_visits() -> int:
    return Visit.query.count()


def active_visits() -> int:
    cutoff_timestamp = datetime.now() - timedelta(hours=12)
    return Visit.query.filter(
        Visit.timestamp > cutoff_timestamp
    ).count()


def active_users(team: str = None) -> list[User]:
    if flask.g.user is None:
        return None

    cutoff_timestamp = datetime.now() - timedelta(hours=12)
    query = (
        db.session.query(User)
        .filter(User.id == Visit.user)
        .filter(Visit.timestamp > cutoff_timestamp)
    )

    if team is not None:
        query = query.filter(User.team == team)

    users = query.order_by(User.email).all()
    return sorted(users, key=lambda u: u.email)
