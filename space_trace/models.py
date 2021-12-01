from space_trace import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    created_at = db.Column(db.Date, nullable=False, default=db.func.now())
    vaccinated_till = db.Column(db.Date, nullable=True, default=None)

    __table_args__ = (db.Index("idx_users_email", email),)

    def __init__(self, name=None, email=None):
        self.name = name
        self.email = email

    def __repr__(self):
        return f"<User id={self.id}, name={self.name}, email={self.email}>"


class Visit(db.Model):
    __tablename__ = "visits"
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.ForeignKey("users.id"), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.now())

    __table_args__ = (db.Index("idx_visits_user", user),)

    def __init__(self, date=None, user=None):
        self.date = date
        self.user = user

    def __repr__(self):
        return f"<Visit id={self.id}, userId={self.user}, timestamp={self.timestamp}>"
