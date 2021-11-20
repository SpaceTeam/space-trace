import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY="dev",
    SAML_PATH=os.path.join(os.path.dirname(os.path.abspath(__file__)), "saml"),
    SQLALCHEMY_DATABASE_URI="sqlite:///trace.db",
)
db = SQLAlchemy(app)

from space_trace import routes
