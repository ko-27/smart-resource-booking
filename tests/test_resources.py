import pytest

from backend.app import create_app
from backend.extensions import db
from backend.models import User, Resource


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

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):

    return app.test_client()


@pytest.fixture
def admin_user(app):

    with app.app_context():

        admin = User(
            name="Test Admin",
            email="admin@test.com",
            department="IT",
            role="ADMIN"
        )

        admin.set_password("Admin@123")

        db.session.add(admin)
        db.session.commit()

        return admin.id


@pytest.fixture
def normal_user(app):

    with app.app_context():

        user = User(
            name="Test User",
            email="user@test.com",
            department="IT",
            role="USER"
        )

        user.set_password("User@123")

        db.session.add(user)
        db.session.commit()

        return user.id


def login(client, email, password):

    return client.post(
        "/login",
        data={
            "email": email,
            "password": password
        },
        follow_redirects=True
    )


def test_resource_list_requires_login(client):

    response = client.get(
        "/resources/",
        follow_redirects=False
    )

    assert response.status_code == 302


def test_admin_can_add_resource(
    client,
    admin_user
):

    login(
        client,
        "admin@test.com",
        "Admin@123"
    )

    response = client.post(
        "/resources/add",
        data={
            "name": "Computer Lab 1",
            "resource_type": "LAB",
            "description": "Computer laboratory",
            "location": "IT Block",
            "capacity": "60"
        },
        follow_redirects=True
    )

    assert response.status_code == 200

    with client.application.app_context():

        resource = Resource.query.filter_by(
            name="Computer Lab 1"
        ).first()

        assert resource is not None
        assert resource.resource_type == "LAB"
        assert resource.capacity == 60
        assert resource.status == "AVAILABLE"
        assert resource.created_by == admin_user


def test_user_cannot_add_resource(
    client,
    normal_user
):

    login(
        client,
        "user@test.com",
        "User@123"
    )

    response = client.post(
        "/resources/add",
        data={
            "name": "Unauthorized Lab",
            "resource_type": "LAB",
            "location": "Block B",
            "capacity": "30"
        },
        follow_redirects=True
    )

    assert response.status_code == 200

    with client.application.app_context():

        resource = Resource.query.filter_by(
            name="Unauthorized Lab"
        ).first()

        assert resource is None


def test_invalid_capacity_rejected(
    client,
    admin_user
):

    login(
        client,
        "admin@test.com",
        "Admin@123"
    )

    response = client.post(
        "/resources/add",
        data={
            "name": "Invalid Lab",
            "resource_type": "LAB",
            "location": "Block A",
            "capacity": "0"
        },
        follow_redirects=True
    )

    assert response.status_code == 200

    with client.application.app_context():

        resource = Resource.query.filter_by(
            name="Invalid Lab"
        ).first()

        assert resource is None


def test_admin_can_edit_resource(
    client,
    admin_user
):

    with client.application.app_context():

        resource = Resource(
            name="Old Lab",
            resource_type="LAB",
            location="Old Block",
            capacity=30,
            status="AVAILABLE",
            created_by=admin_user
        )

        db.session.add(resource)
        db.session.commit()

        resource_id = resource.id

    login(
        client,
        "admin@test.com",
        "Admin@123"
    )

    response = client.post(
        f"/resources/edit/{resource_id}",
        data={
            "name": "Updated Lab",
            "resource_type": "LAB",
            "description": "Updated description",
            "location": "New Block",
            "capacity": "50",
            "status": "AVAILABLE"
        },
        follow_redirects=True
    )

    assert response.status_code == 200

    with client.application.app_context():

        resource = db.session.get(
            Resource,
            resource_id
        )

        assert resource.name == "Updated Lab"
        assert resource.location == "New Block"
        assert resource.capacity == 50


def test_admin_can_deactivate_resource(
    client,
    admin_user
):

    with client.application.app_context():

        resource = Resource(
            name="Lab To Deactivate",
            resource_type="LAB",
            location="Block C",
            capacity=40,
            status="AVAILABLE",
            created_by=admin_user
        )

        db.session.add(resource)
        db.session.commit()

        resource_id = resource.id

    login(
        client,
        "admin@test.com",
        "Admin@123"
    )

    response = client.get(
        f"/resources/deactivate/{resource_id}",
        follow_redirects=True
    )

    assert response.status_code == 200

    with client.application.app_context():

        resource = db.session.get(
            Resource,
            resource_id
        )

        assert resource.status == "UNAVAILABLE"


def test_resource_search(
    client,
    admin_user
):

    with client.application.app_context():

        resource = Resource(
            name="Seminar Hall A",
            resource_type="HALL",
            location="Academic Block",
            capacity=100,
            status="AVAILABLE",
            created_by=admin_user
        )

        db.session.add(resource)
        db.session.commit()

    login(
        client,
        "admin@test.com",
        "Admin@123"
    )

    response = client.get(
        "/resources/?search=Seminar"
    )

    assert response.status_code == 200

    assert b"Seminar Hall A" in response.data