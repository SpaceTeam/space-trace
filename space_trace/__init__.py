import toml
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, instance_relative_config=True)
app.config.from_file("config.toml", load=toml.load)
app.config.update(
    SESSION_COOKIE_SECURE=app.env == "production",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=90 * 24 * 60 * 60,
)
db = SQLAlchemy(app)


@app.before_first_request
def create_table():
    db.create_all()


from space_trace import views, cli
