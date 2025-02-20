import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
from app import create_app
from app.models import db, User

os.environ["MPLBACKEND"] = "Agg"  # Вимикає графічний інтерфейс


@pytest.fixture
def app():
    os.environ["CONFIG_TYPE"] = "app.config.TestConfig"  # Використання TestConfig

    app = create_app()
    app.config.update({
        "TESTING": True,
        'SQLALCHEMY_TRACK_MODIFICATIONS':False,
    })
    # app.config['WTF_CSRF_METHODS'] = []  # This is the magic
    # Створення бази та таблиць
    with app.app_context():
        db.create_all()

    # push app context !!!!
    app.app_context().push()

    # with app.app_context():
    #     # Очищуємо певні таблиці (наприклад, User, Post)
    #     db.session.execute("DELETE FROM user")  # або db.session.query(User).delete()
    #     db.session.execute("DELETE FROM post")
    #     db.session.commit()

    yield app

    # Очищаємо базу після кожного тесту
    with app.app_context():
        db.session.remove()
        db.drop_all()  # Видаляємо всі таблиці


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth(client):
    class AuthActions:
        def login(self, username="testuser", password="password123"):
            return client.post(
                "/login",
                data={"username": username, "password": password},
                follow_redirects=True
            )

        def logout(self):
            return client.get("/logout", follow_redirects=True)

    return AuthActions()