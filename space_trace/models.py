from space_trace import db


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)

    def __init__(self, name=None, email=None):
        self.name = name
        self.email = email

    def __repr__(self):
        return f"<User {self.name!r}>"


class Certificate(db.Model):
    __tablename__ = "certificates"
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Text, unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False)
    add_date = db.Column(db.Date, nullable=False, default=db.func.now())
    user = db.Column(db.ForeignKey("users.id"), nullable=False)

    def __init__(self, data=None, date=None, user=None):
        self.data = data
        self.date = date
        self.user = user

    def __repr__(self):
        return "<Certificate>"


class Visit(db.Model):
    __tablename__ = "visits"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    user = db.Column(db.ForeignKey("users.id"), nullable=False)

    def __init__(self, date=None, user=None):
        self.date = date
        self.user = user

    def __repr__(self):
        return "<Visit>"
