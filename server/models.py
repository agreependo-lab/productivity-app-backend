from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import validates

db = SQLAlchemy()
bcrypt = Bcrypt()


class User(db.Model):
    __tablename__ = "users"

    __table_args__ = (
        db.CheckConstraint("length(username) >= 3", name="ck_user_username_length"),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)
    _password_hash = db.Column(db.String, nullable=False)

    notes = db.relationship(
        "Note", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def password_hash(self):
        raise AttributeError("Password hashes may not be viewed.")

    @password_hash.setter
    def password_hash(self, password):
        self._password_hash = bcrypt.generate_password_hash(
            password.encode("utf-8")
        ).decode("utf-8")

    def authenticate(self, password):
        return bcrypt.check_password_hash(self._password_hash, password.encode("utf-8"))

    @validates("username")
    def validate_username(self, key, value):
        if not isinstance(value, str) or len(value.strip()) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        return value.strip()

    def __repr__(self):
        return f"<User {self.id}: {self.username}>"


class Note(db.Model):
    __tablename__ = "notes"

    __table_args__ = (
        db.CheckConstraint("length(title) > 0", name="ck_note_title_not_empty"),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String, nullable=False, default="general")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    user = db.relationship("User", back_populates="notes")

    @validates("title")
    def validate_title(self, key, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Title cannot be empty.")
        return value.strip()

    @validates("content")
    def validate_content(self, key, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Content cannot be empty.")
        return value

    def __repr__(self):
        return f"<Note {self.id}: {self.title}>"