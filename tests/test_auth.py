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


def test_phone_otp_login_flow(client, app):

    # 1. Register a user with phone number
    client.post(
        "/register",
        data={
            "name": "OTP User",
            "email": "otpuser@example.com",
            "department": "IT",
            "phone": "9876543210",
            "password": "Password@123"
        },
        follow_redirects=True
    )

    # 2. Request OTP
    resp = client.post(
        "/login/phone/request-otp",
        data={"phone": "9876543210"},
        follow_redirects=True
    )
    assert resp.status_code == 200

    with client.session_transaction() as sess:
        otp_code = sess.get("login_otp")
        assert otp_code is not None
        assert len(otp_code) == 6

    # 3. Verify OTP
    verify_resp = client.post(
        "/login/phone/verify-otp",
        data={"otp": otp_code},
        follow_redirects=False
    )
    # Redirects to dashboard upon successful login
    assert verify_resp.status_code == 302
    assert "/dashboard" in verify_resp.headers["Location"]


def test_phone_otp_invalid_code(client, app):

    client.post(
        "/register",
        data={
            "name": "OTP User 2",
            "email": "otpuser2@example.com",
            "department": "ECE",
            "phone": "9123456780",
            "password": "Password@123"
        },
        follow_redirects=True
    )

    client.post(
        "/login/phone/request-otp",
        data={"phone": "9123456780"},
        follow_redirects=True
    )

    verify_resp = client.post(
        "/login/phone/verify-otp",
        data={"otp": "000000"},
        follow_redirects=True
    )
    assert verify_resp.status_code == 200
    assert b"Invalid OTP" in verify_resp.data


def test_edit_profile_contact_details(client, app):

    client.post(
        "/register",
        data={
            "name": "Contact User",
            "email": "contactuser@example.com",
            "department": "Mechanical",
            "phone": "9000000001",
            "password": "Password@123"
        },
        follow_redirects=True
    )

    # Login
    client.post(
        "/login",
        data={
            "email": "contactuser@example.com",
            "password": "Password@123"
        },
        follow_redirects=True
    )

    # Update contact details
    resp = client.post(
        "/profile/edit",
        data={
            "name": "Contact User Updated",
            "department": "Robotics",
            "phone": "9998887776"
        },
        follow_redirects=True
    )
    assert resp.status_code == 200

    with app.app_context():
        u = User.query.filter_by(email="contactuser@example.com").first()
        assert u.name == "Contact User Updated"
        assert u.department == "Robotics"
        assert u.phone == "9998887776"