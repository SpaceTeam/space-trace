import toml
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, instance_relative_config=True)
app.config.from_file("config.toml", load=toml.load)
db = SQLAlchemy(app)

from space_trace import routes
