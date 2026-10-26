import os
from functools import wraps

from flask import Flask, g, request, session
from flask_migrate import Migrate
from flask_restful import Api, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from models import Note, User, bcrypt, db
from schemas import (
    login_schema,
    note_schema,
    note_update_schema,
    notes_schema,
    user_schema,
)

migrate = Migrate()


def login_required(fn):
    """Reject the request with 401 unless a user is logged in."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id else None
        if not user:
            return {"error": "Unauthorized"}, 401
        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def get_owned_note(note_id):
    """Return (note, error_response). Users may only touch their own notes."""
    note = db.session.get(Note, note_id)
    if not note:
        return None, ({"error": "Note not found"}, 404)
    if note.user_id != g.current_user.id:
        return None, ({"error": "Forbidden"}, 403)
    return note, None


# ---------- Authentication ----------
class Signup(Resource):
    def post(self):
        try:
            data = user_schema.load(request.get_json(silent=True) or {})
            user = User(username=data["username"])
            user.password_hash = data["password"]
            db.session.add(user)
            db.session.commit()
        except ValidationError as err:
            return {"errors": err.messages}, 422
        except ValueError as err:
            db.session.rollback()
            return {"errors": {"username": [str(err)]}}, 422
        except IntegrityError:
            db.session.rollback()
            return {"errors": {"username": ["Username is already taken."]}}, 422
        session["user_id"] = user.id
        return user_schema.dump(user), 201


class Login(Resource):
    def post(self):
        try:
            data = login_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return {"errors": err.messages}, 422
        user = User.query.filter_by(username=data["username"]).first()
        if not user or not user.authenticate(data["password"]):
            return {"error": "Invalid username or password"}, 401
        session["user_id"] = user.id
        return user_schema.dump(user), 200


class Logout(Resource):
    def delete(self):
        session.pop("user_id", None)
        return "", 204


class CheckSession(Resource):
    def get(self):
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id else None
        if not user:
            return {"error": "Unauthorized"}, 401
        return user_schema.dump(user), 200


# ---------- Notes (user-owned resource) ----------
class NoteIndex(Resource):
    @login_required
    def get(self):
        page = max(request.args.get("page", 1, type=int), 1)
        per_page = min(max(request.args.get("per_page", 5, type=int), 1), 50)
        pagination = (
            Note.query.filter_by(user_id=g.current_user.id)
            .order_by(Note.created_at.desc(), Note.id.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )
        return {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "total_pages": pagination.pages,
            "notes": notes_schema.dump(pagination.items),
        }, 200

    @login_required
    def post(self):
        try:
            data = note_schema.load(request.get_json(silent=True) or {})
            note = Note(user_id=g.current_user.id, **data)
            db.session.add(note)
            db.session.commit()
        except ValidationError as err:
            return {"errors": err.messages}, 422
        except (ValueError, IntegrityError) as err:
            db.session.rollback()
            return {"errors": [str(err)]}, 422
        return note_schema.dump(note), 201


class NoteDetail(Resource):
    @login_required
    def get(self, id):
        note, error = get_owned_note(id)
        if error:
            return error
        return note_schema.dump(note), 200

    @login_required
    def patch(self, id):
        note, error = get_owned_note(id)
        if error:
            return error
        try:
            data = note_update_schema.load(request.get_json(silent=True) or {})
            for key, value in data.items():
                setattr(note, key, value)
            db.session.commit()
        except ValidationError as err:
            return {"errors": err.messages}, 422
        except (ValueError, IntegrityError) as err:
            db.session.rollback()
            return {"errors": [str(err)]}, 422
        return note_schema.dump(note), 200

    @login_required
    def delete(self, id):
        note, error = get_owned_note(id)
        if error:
            return error
        db.session.delete(note)
        db.session.commit()
        return "", 204


def create_app(config=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    if config:
        app.config.update(config)

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    api = Api(app)
    api.add_resource(Signup, "/signup")
    api.add_resource(Login, "/login")
    api.add_resource(Logout, "/logout")
    api.add_resource(CheckSession, "/check_session")
    api.add_resource(NoteIndex, "/notes")
    api.add_resource(NoteDetail, "/notes/<int:id>")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(port=5555, debug=True)