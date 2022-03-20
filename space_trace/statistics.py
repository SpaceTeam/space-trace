r"""Statistics referes here to read-only access to the database. However, these 
functions might not only be used to strictly create statistics or graphs.
"""


from typing import Any, Dict, List, Tuple
from space_trace.models import User, Visit
from space_trace import db
from datetime import datetime, timedelta


def total_users() -> int:
    """Count of the total number users registered in the system"""
    return User.query.count()


def total_visits() -> int:
    """Count of the total number of visits"""
    return Visit.query.count()


def active_visits() -> int:
    """Count of currently active visits (users that are counted as in the HQ)"""
    cutoff_timestamp = datetime.now() - timedelta(hours=12)
    return Visit.query.filter(Visit.timestamp > cutoff_timestamp).count()


def active_users(team: str = None) -> List[User]:
    """List the currently active users in the HQ.

    :param team: Filter the users by team, if None all teams are considered.
    :return: List of users
    """
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


def checkins_per_hour() -> Dict[str, Any]:
    """Show at which times users log in.

    This data is meant for a graph, the returned dict has the keys 'labels' for
    the x axis and 'data' with a numeric value.
    """
    rows = db.session.query(
        db.func.strftime("%H", Visit.timestamp), db.func.count(Visit.id)
    ).group_by(db.func.strftime("%H", Visit.timestamp))

    checkins = dict()
    checkins["labels"] = [f"{i}h" for i in range(24)]
    checkins["data"] = [0 for _ in range(24)]

    for row in rows:
        checkins["data"][int(row[0])] = row[1]

    return checkins


def most_frequent_users(limit: int = 16) -> List[Tuple[int, User]]:
    """Show the users with the most visits.

    :param limit: Limits the number of returned users.
    """
    rows = (
        db.session.query(db.func.count(User.id), User)
        .filter(Visit.user == User.id)
        .group_by(User)
        .order_by(db.func.count(User.id).desc())
        .limit(limit)
        .all()
    )
    return [(count, user) for count, user in rows]


def daily_usage() -> Dict[str, Any]:
    """Show the usage per day (last 30)."""
    cutoff_timestamp = datetime.now() - timedelta(days=30)
    cutoff_timestamp = cutoff_timestamp.replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    visits = (
        db.session.query(
            db.func.strftime("%Y-%m-%d", Visit.timestamp), db.func.count(Visit.id)
        )
        .filter(Visit.timestamp >= cutoff_timestamp)
        .group_by(db.func.strftime("%Y-%m-%d", Visit.timestamp))
        .order_by(db.func.strftime("%Y-%m-%d", Visit.timestamp))
        .all()
    )

    visits_st = (
        db.session.query(
            db.func.strftime("%Y-%m-%d", Visit.timestamp), db.func.count(Visit.id)
        )
        .filter(Visit.timestamp >= cutoff_timestamp)
        .filter(User.id == Visit.user)
        .filter(User.team == "space")
        .group_by(db.func.strftime("%Y-%m-%d", Visit.timestamp))
        .order_by(db.func.strftime("%Y-%m-%d", Visit.timestamp))
        .all()
    )

    # TODO: I don't like this code but it is the best solution I can come up with
    # Maybe future developers will find a better way to fill missing indexes
    # with zeros.
    all_index = 0
    st_index = 0
    st_users = []
    while all_index < len(visits):
        if len(visits_st) > st_index and visits_st[st_index][0] == visits[all_index][0]:
            st_users.append(visits_st[st_index][1])
            st_index += 1
        else:
            st_users.append(0)

        all_index += 1

    rt_users = []
    for i, visit in enumerate(visits):
        rt_users.append(visit[1] - st_users[i])

    return {
        "labels": [v[0] for v in visits],
        "visits": [v[1] for v in visits],
        "visits_st": st_users,
        "visits_rt": rt_users,
    }


def monthly_usage() -> Dict[str, Any]:
    """Show the usage per month.

    This data is meant for a graph, the returned dict has the keys 'labels' for
    the x axis and 'data' with a numeric value.
    """
    visits = (
        db.session.query(
            db.func.strftime("%Y-%m", Visit.timestamp), db.func.count(Visit.id)
        )
        .group_by(db.func.strftime("%Y-%m", Visit.timestamp))
        .order_by(db.func.strftime("%Y-%m", Visit.timestamp))
        .all()
    )

    active_users = (
        db.session.query(
            db.func.strftime("%m-%Y", Visit.timestamp),
            db.func.count(db.func.distinct(User.id)),
        )
        .filter(User.id == Visit.user)
        .group_by(db.func.strftime("%m-%Y", Visit.timestamp))
        .order_by(db.func.strftime("%Y-%m", Visit.timestamp))
        .all()
    )

    data = {
        "labels": [r[0] for r in visits],
        "visits": [r[1] for r in visits],
        "active_users": [r[1] for r in active_users],
    }

    return data
