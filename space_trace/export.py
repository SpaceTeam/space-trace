r"""
"""

import csv
from datetime import datetime, timedelta
from io import StringIO
from typing import List

from space_trace import db
from space_trace.models import User, Visit


def get_contacts_of(start: datetime, infected_id: int):
    # This may look weired but we need to do a bit of arithmetic with both
    # timestamps. At the moment both timestamps point to the
    # start of the day (0:00) but end should point to the last minute so if
    # both point to the same day one whole day gets selected.
    # Actually start should point to 12h before that because members that only
    # logged in 12h before are still considered as in the HQ.
    start = start - timedelta(hours=12)

    # Get all contacts of the infected
    visit1: Visit = db.aliased(Visit)
    visit2: Visit = db.aliased(Visit)
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

    return users


def get_users_between(start: datetime, end: datetime):
    # This may look weired but we need to do a bit of arithmetic with both
    # timestamps. At the moment both timestamps point to the
    # start of the day (0:00) but end should point to the last minute so if
    # both point to the same day one whole day gets selected.
    # Actually start should point to 12h before that because members that only
    # logged in 12h bevore are still considered as in the HQ.
    start = start - timedelta(hours=12)
    end = end + timedelta(hours=24)

    # Get all users in that time period
    users = (
        db.session.query(User)
        .filter(User.id == Visit.user)
        .filter(db.and_(Visit.timestamp > start, Visit.timestamp < end))
        .all()
    )
    return users


def users_to_csv(users: List[User]) -> str:
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["first name", "last name", "team"])

    for user in users:
        cw.writerow([user.first_name(), user.last_name(), user.team])

    return si.getvalue()
