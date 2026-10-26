import random

from faker import Faker

from app import app
from models import Note, User, db

fake = Faker()
CATEGORIES = ["work", "personal", "ideas", "todo", "study"]

with app.app_context():
    print("Clearing old data...")
    Note.query.delete()
    User.query.delete()

    print("Seeding users...")
    users = []
    for username in ["alice", "bob", "carol"]:
        user = User(username=username)
        user.password_hash = "password123"
        users.append(user)
    db.session.add_all(users)
    db.session.commit()

    print("Seeding notes...")
    for user in users:
        for _ in range(random.randint(8, 12)):
            db.session.add(
                Note(
                    title=fake.sentence(nb_words=4).rstrip("."),
                    content=fake.paragraph(nb_sentences=3),
                    category=random.choice(CATEGORIES),
                    user_id=user.id,
                )
            )
    db.session.commit()
    print("Done seeding! Log in as alice, bob or carol with password: password123")