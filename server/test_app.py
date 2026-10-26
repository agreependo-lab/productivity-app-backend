import pytest

from app import create_app
from models import Note, User, db


@pytest.fixture
def client():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "BCRYPT_LOG_ROUNDS": 4,
        }
    )
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def signup(client, username="alice", password="password123"):
    return client.post("/signup", json={"username": username, "password": password})


def login(client, username="alice", password="password123"):
    return client.post("/login", json={"username": username, "password": password})


def make_note(client, **overrides):
    body = {"title": "Groceries", "content": "Milk and eggs", "category": "personal"}
    body.update(overrides)
    return client.post("/notes", json=body)


# ---------- Sign up ----------
def test_signup_creates_user_and_logs_in(client):
    res = signup(client)
    assert res.status_code == 201
    assert res.get_json()["username"] == "alice"
    assert "password" not in res.get_json()
    assert client.get("/check_session").status_code == 200


def test_signup_hashes_password(client):
    signup(client)
    user = User.query.filter_by(username="alice").first()
    assert user._password_hash != "password123"
    assert user.authenticate("password123")
    with pytest.raises(AttributeError):
        user.password_hash


def test_signup_duplicate_username(client):
    signup(client)
    assert signup(client).status_code == 422


def test_signup_short_password(client):
    assert signup(client, password="short").status_code == 422


def test_signup_short_username(client):
    assert signup(client, username="ab").status_code == 422


def test_signup_missing_fields(client):
    assert client.post("/signup", json={}).status_code == 422


# ---------- Login / logout / check_session ----------
def test_login_success(client):
    signup(client)
    client.delete("/logout")
    res = login(client)
    assert res.status_code == 200
    assert res.get_json()["username"] == "alice"


def test_login_wrong_password(client):
    signup(client)
    client.delete("/logout")
    assert login(client, password="wrongpass1").status_code == 401


def test_login_unknown_user(client):
    assert login(client, username="ghost").status_code == 401


def test_logout_clears_session(client):
    signup(client)
    assert client.delete("/logout").status_code == 204
    assert client.get("/check_session").status_code == 401


def test_check_session_unauthorized(client):
    assert client.get("/check_session").status_code == 401


# ---------- Notes: protection ----------
def test_notes_require_login(client):
    assert client.get("/notes").status_code == 401
    assert client.post("/notes", json={"title": "x", "content": "y"}).status_code == 401
    assert client.get("/notes/1").status_code == 401
    assert client.patch("/notes/1", json={"title": "x"}).status_code == 401
    assert client.delete("/notes/1").status_code == 401


def test_user_cannot_access_other_users_notes(client):
    signup(client, "alice")
    note_id = make_note(client).get_json()["id"]
    client.delete("/logout")
    signup(client, "bobby")
    assert client.get(f"/notes/{note_id}").status_code == 403
    assert client.patch(f"/notes/{note_id}", json={"title": "hacked"}).status_code == 403
    assert client.delete(f"/notes/{note_id}").status_code == 403
    assert client.get("/notes").get_json()["total"] == 0


# ---------- Notes: CRUD ----------
def test_create_note(client):
    signup(client)
    res = make_note(client)
    assert res.status_code == 201
    assert res.get_json()["category"] == "personal"
    assert res.get_json()["user_id"] is not None


def test_create_note_validation(client):
    signup(client)
    assert make_note(client, title="").status_code == 422
    assert make_note(client, content="").status_code == 422


def test_get_note(client):
    signup(client)
    note_id = make_note(client).get_json()["id"]
    assert client.get(f"/notes/{note_id}").status_code == 200


def test_note_not_found(client):
    signup(client)
    assert client.get("/notes/999").status_code == 404


def test_update_note(client):
    signup(client)
    note_id = make_note(client).get_json()["id"]
    res = client.patch(f"/notes/{note_id}", json={"title": "Updated"})
    assert res.status_code == 200
    assert res.get_json()["title"] == "Updated"


def test_update_note_validation(client):
    signup(client)
    note_id = make_note(client).get_json()["id"]
    assert client.patch(f"/notes/{note_id}", json={"title": ""}).status_code == 422


def test_delete_note(client):
    signup(client)
    note_id = make_note(client).get_json()["id"]
    assert client.delete(f"/notes/{note_id}").status_code == 204
    assert client.get(f"/notes/{note_id}").status_code == 404


# ---------- Pagination ----------
def test_pagination(client):
    signup(client)
    for i in range(12):
        make_note(client, title=f"Note {i}")
    page1 = client.get("/notes?page=1&per_page=5").get_json()
    page3 = client.get("/notes?page=3&per_page=5").get_json()
    assert page1["total"] == 12
    assert page1["total_pages"] == 3
    assert len(page1["notes"]) == 5
    assert len(page3["notes"]) == 2


def test_pagination_defaults(client):
    signup(client)
    for i in range(7):
        make_note(client, title=f"Note {i}")
    data = client.get("/notes").get_json()
    assert data["page"] == 1
    assert data["per_page"] == 5
    assert len(data["notes"]) == 5


def test_deleting_user_deletes_notes(client):
    signup(client)
    make_note(client)
    db.session.delete(User.query.first())
    db.session.commit()
    assert Note.query.count() == 0