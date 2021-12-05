from datetime import date

_jokes = [
    "Are you sure you wanna enter?",
    "There is still time to go back home.",
    "Couldn't you have brought someone who is actually likable instead?",
    "Oh look there is a fire behind you. You must investigate this and spare "
    "the poor souls in the spaceteam.",
    "I wish you were a rocket than you would be far always very quickly.",
    "No one forces you to press this button, you can still turn around.",
    "I'd rather `run rm -rf / ` than see you inside there.",
    'Sure, chemical weapons are "inhumane" but somehow it is still legal that '
    "you can tortue innocent engineers with you presence.",
    "You know looking at you I am not so sure anymore if hitting children is "
    "**always** bad.",
    "By pressing this button you also agree that you voluntarily give up your "
    "right to a dark theme.",
    "#FFFFFF, yes exactly and there is more of that if you enter.",
    "You may be unatractive, stupid and socially awkward but you also smell "
    "bad.",
    "Clicking buttons is fun. Go fetch yourself a remote and press those "
    "buttons instead. (They are way more satisfyable to press anyway).",
    "FIRE! ... with such a huge erection I wouldn't enter HQ either.",
    "Explosions are fun, and my fun-levels always explode when you're far "
    "away.",
    "Oh no the button is broken. But no worries a team of very active sloths "
    "is working on it. So there is really no point in pressing it. Come back "
    "tomorrow and see if it is fixed.",
    "Every time you press the button a little rocket won't fly. Why would you "
    "do such an awful thing? Why?",
    "Press the button and enjoy your lifetime supply of virginity",
    "With face like yours you really don't have to post in r/roastme as "
    "everyone already does this without you even asking.",
    "I really wish I had something brighter than #FFFFFF, just for you.",
]


def get_daily_joke() -> str:
    return _jokes[(date.today().toordinal() + 4) % len(_jokes)]
