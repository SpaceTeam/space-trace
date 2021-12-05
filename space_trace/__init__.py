import toml
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, instance_relative_config=True)
app.config.from_file("config.toml", load=toml.load)
db = SQLAlchemy(app)


@app.before_first_request
def create_table():
    db.create_all()


from space_trace import routes
