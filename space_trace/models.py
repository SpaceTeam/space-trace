from datetime import date, datetime
from space_trace import db


class User(db.Model):
    __tablename__ = "users"

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.Text, nullable=False)
    email: str = db.Column(db.Text, unique=True, nullable=False)
    created_at: datetime = db.Column(
        db.Date, nullable=False, default=db.func.now()
    )
    vaccinated_till: date = db.Column(db.Date, nullable=True, default=None)

    __table_args__ = (db.Index("idx_users_email", email),)

    def __init__(self, name: str = None, email: str = None):
        self.name = name
        self.email = email

    def __repr__(self):
        return f"<User id={self.id}, name={self.name}, email={self.email}>"


class Visit(db.Model):
    __tablename__ = "visits"
    id: int = db.Column(db.Integer, primary_key=True)
    user: str = db.Column(db.ForeignKey("users.id"), nullable=False)
    timestamp: datetime = db.Column(
        db.DateTime, nullable=False, default=db.func.now()
    )

    __table_args__ = (db.Index("idx_visits_user", user),)

    def __init__(self, timestamp: datetime = None, user_id: int = None):
        self.timestamp = timestamp
        self.user = user_id

    def __repr__(self):
        return (
            f"<Visit id={self.id}, userId={self.user}, "
            "timestamp={self.timestamp}>"
        )
