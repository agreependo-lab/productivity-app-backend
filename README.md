# Productivity App Backend

A secure Flask REST API with full session-based authentication and a user-owned **Notes** resource, built for a productivity app frontend.

## Description
Users can sign up, log in, log out and stay logged in across page refreshes. Each user can create, read, update and delete their own notes. Notes are paginated, and users can never view or change another user's notes. Passwords are hashed with bcrypt and never returned by the API.

## Installation
```bash
python3 -m pipenv install --dev
python3 -m pipenv shell
export FLASK_APP=server/app.py
flask db init
flask db migrate -m "Initial migration"
flask db upgrade head
python server/seed.py
```

## Run
```bash
flask run -p 5555
```
The API runs at http://127.0.0.1:5555

## Seed data
`python server/seed.py` creates the users `alice`, `bob` and `carol` (password: `password123`), each with 8-12 notes.

## Tests
```bash
pytest server -v
```

## Endpoints
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | /signup | No | Create a user (`username` 3+ chars, `password` 8+ chars) and log in. Returns 201 |
| POST | /login | No | Log in with `username` and `password`. Returns 200, or 401 for bad credentials |
| DELETE | /logout | No | Log out and clear the session. Returns 204 |
| GET | /check_session | No | Return the logged-in user (200), or 401 if not logged in |
| GET | /notes?page=1&per_page=5 | Yes | Paginated list of the current user's notes |
| POST | /notes | Yes | Create a note (`title`, `content`, optional `category`). Returns 201 |
| GET | /notes/<id> | Yes | Show one of your notes (404 if missing, 403 if it belongs to someone else) |
| PATCH | /notes/<id> | Yes | Update one of your notes |
| DELETE | /notes/<id> | Yes | Delete one of your notes. Returns 204 |

Unauthenticated requests to protected routes return **401**. Accessing another user's note returns **403**.

## Models
- **User:** `username` (unique), bcrypt-hashed password, has many notes.
- **Note:** `title`, `content`, `category`, `created_at`, belongs to a user.

## Dependencies
See the `Pipfile`.