import pytest

from backend.app import create_app
from backend.extensions import db
from backend.models import User


@pytest.fixture
def app():

    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
    })

    with app.app_context():
        db.create_all()

        yield app

        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_register_page(client):

    response = client.get("/register")

    assert response.status_code == 200


def test_login_page(client):

    response = client.get("/login")

    assert response.status_code == 200


def test_user_registration(client, app):

    response = client.post(
        "/register",
        data={
            "name": "Test User",
            "email": "test@example.com",
            "department": "IT",
            "phone": "9876543210",
            "password": "Test@123"
        },
        follow_redirects=True
    )

    assert response.status_code == 200

    with app.app_context():

        user = User.query.filter_by(
            email="test@example.com"
        ).first()

        assert user is not None
        assert user.role == "USER"

        assert user.check_password("Test@123")


def test_duplicate_registration(client):

    client.post(
        "/register",
        data={
            "name": "Test User",
            "email": "test@example.com",
            "department": "IT",
            "password": "Test@123"
        }
    )

    response = client.post(
        "/register",
        data={
            "name": "Another User",
            "email": "test@example.com",
            "department": "CSE",
            "password": "Test@456"
        },
        follow_redirects=True
    )

    assert response.status_code == 200


def test_invalid_login(client):

    response = client.post(
        "/login",
        data={
            "email": "wrong@example.com",
            "password": "WrongPassword"
        },
        follow_redirects=True
    )

    assert response.status_code == 200


def test_protected_dashboard(client):

    response = client.get(
        "/dashboard",
        follow_redirects=False
    )

    assert response.status_code == 302