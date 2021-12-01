import random
from datetime import date

_jokes = [
    "Knock knock",
    "whos there",
]


def get_daily_joke() -> str:
    rgn = random.Random(date.today().toordinal())
    return rgn.choice(_jokes)
