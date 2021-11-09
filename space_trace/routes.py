from space_trace import app
from space_trace.models import User


@app.route("/")
def home():
    return "Hey boyyy"
