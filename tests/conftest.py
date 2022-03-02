import os
import tempfile
from flask_sqlalchemy import SQLAlchemy

import pytest

from space_trace import app, db


@pytest.fixture
def client():
    global app, db

    db_fd, db_path = tempfile.mkstemp()
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["TESTING"] = True

    # db = SQLAlchemy(app)
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)
