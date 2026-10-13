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


def test_registration_with_phone_otp_verification(client, app):

    # 1. Initiate registration with OTP verification
    resp = client.post(
        "/register",
        data={
            "name": "Verified Registrant",
            "email": "verified@cit.edu.in",
            "department": "ECE",
            "phone": "9811223344",
            "password": "SecurePassword@1",
            "require_otp": "true"
        },
        follow_redirects=False
    )
    assert resp.status_code == 302
    assert "step=verify" in resp.headers["Location"]

    with client.session_transaction() as sess:
        otp_code = sess.get("reg_otp")
        assert otp_code is not None
        assert len(otp_code) == 6

    # 2. Try invalid OTP first
    invalid_resp = client.post(
        "/register/verify-otp",
        data={"otp": "999999" if otp_code != "999999" else "888888"},
        follow_redirects=True
    )
    assert invalid_resp.status_code == 200
    assert b"Invalid OTP" in invalid_resp.data

    with app.app_context():
        # User should NOT be created yet
        assert User.query.filter_by(email="verified@cit.edu.in").first() is None

    # 3. Enter correct OTP
    valid_resp = client.post(
        "/register/verify-otp",
        data={"otp": otp_code},
        follow_redirects=False
    )
    assert valid_resp.status_code == 302
    assert "/login" in valid_resp.headers["Location"]

    # 4. User should now exist with phone verified!
    with app.app_context():
        new_user = User.query.filter_by(email="verified@cit.edu.in").first()
        assert new_user is not None
        assert new_user.name == "Verified Registrant"
        assert new_user.phone == "9811223344"
        assert new_user.department == "ECE"
        assert new_user.check_password("SecurePassword@1")

def test_admin_can_view_other_admins_in_profile(client, app):
    with app.app_context():
        admin1 = User(name="Admin One", email="admin1@example.com", department="IT", phone="9876543211", role="ADMIN")
        admin1.set_password("Admin@123")
        admin2 = User(name="Admin Two", email="admin2@example.com", department="CSE", phone="9876543212", role="ADMIN")
        admin2.set_password("Admin@123")
        user1 = User(name="Regular User", email="user1@example.com", department="MECH", phone="9876543213", role="USER")
        user1.set_password("User@123")
        db.session.add_all([admin1, admin2, user1])
        db.session.commit()

    # Login as admin1
    client.post("/login", data={"email": "admin1@example.com", "password": "Admin@123"}, follow_redirects=True)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Admin Colleagues" in html
    assert "Admin Two" in html
    assert "admin2@example.com" in html
    assert "All Administrators" in html
    assert "adminDirectoryModal" in html

    # Logout and login as regular user
    client.get("/logout")
    client.post("/login", data={"email": "user1@example.com", "password": "User@123"}, follow_redirects=True)
    resp2 = client.get("/dashboard")
    assert resp2.status_code == 200
    html2 = resp2.data.decode("utf-8")
    assert "Admin Colleagues" not in html2
    assert "adminDirectoryModal" not in html2
