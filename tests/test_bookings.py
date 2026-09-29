import pytest

from backend.app import create_app
from backend.extensions import db
from backend.models import User, Resource, Booking


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
def users_and_resource(app):

    with app.app_context():

        user = User(
            name="Test User",
            email="bookinguser@test.com",
            department="IT",
            role="USER"
        )

        user.set_password("User@123")

        admin = User(
            name="Test Admin",
            email="bookingadmin@test.com",
            department="IT",
            role="ADMIN"
        )

        admin.set_password("Admin@123")

        db.session.add_all([
            user,
            admin
        ])

        db.session.commit()

        resource = Resource(
            name="Test Computer Lab",
            resource_type="LAB",
            description="Testing laboratory",
            location="IT Block",
            capacity=50,
            status="AVAILABLE",
            created_by=admin.id
        )

        db.session.add(resource)
        db.session.commit()

        return user.id, admin.id, resource.id


def login(client, email, password):

    return client.post(
        "/login",
        data={
            "email": email,
            "password": password
        },
        follow_redirects=True
    )


def test_booking_page_requires_login(client):

    response = client.get(
        "/bookings/",
        follow_redirects=False
    )

    assert response.status_code == 302


def test_user_can_create_booking(
    client,
    users_and_resource
):

    user_id, admin_id, resource_id = users_and_resource

    login(
        client,
        "bookinguser@test.com",
        "User@123"
    )

    response = client.post(
        f"/bookings/create/{resource_id}",
        data={
            "booking_date": "2026-10-05",
            "start_time": "10:00",
            "end_time": "12:00",
            "purpose": "Project review"
        },
        follow_redirects=True
    )

    assert response.status_code == 200

    with client.application.app_context():

        booking = Booking.query.first()

        assert booking is not None
        assert booking.user_id == user_id
        assert booking.resource_id == resource_id
        assert booking.purpose == "Project review"
        assert booking.status == "BOOKED"


def test_overlapping_booking_is_rejected(
    client,
    users_and_resource
):

    user_id, admin_id, resource_id = users_and_resource

    with client.application.app_context():

        booking = Booking(
            user_id=user_id,
            resource_id=resource_id,
            booking_date=__import__("datetime").date(
                2026,
                10,
                5
            ),
            start_time=__import__("datetime").time(
                10,
                0
            ),
            end_time=__import__("datetime").time(
                12,
                0
            ),
            purpose="Existing booking",
            status="BOOKED"
        )

        db.session.add(booking)
        db.session.commit()

    login(
        client,
        "bookinguser@test.com",
        "User@123"
    )

    response = client.post(
        f"/bookings/create/{resource_id}",
        data={
            "booking_date": "2026-10-05",
            "start_time": "11:00",
            "end_time": "13:00",
            "purpose": "Overlapping booking"
        },
        follow_redirects=True
    )

    assert b"already booked" in response.data

    with client.application.app_context():

        bookings = Booking.query.all()

        assert len(bookings) == 1


def test_non_overlapping_booking_is_allowed(
    client,
    users_and_resource
):

    user_id, admin_id, resource_id = users_and_resource

    with client.application.app_context():

        booking = Booking(
            user_id=user_id,
            resource_id=resource_id,
            booking_date=__import__("datetime").date(
                2026,
                10,
                5
            ),
            start_time=__import__("datetime").time(
                10,
                0
            ),
            end_time=__import__("datetime").time(
                12,
                0
            ),
            purpose="Morning booking",
            status="BOOKED"
        )

        db.session.add(booking)
        db.session.commit()

    login(
        client,
        "bookinguser@test.com",
        "User@123"
    )

    response = client.post(
        f"/bookings/create/{resource_id}",
        data={
            "booking_date": "2026-10-05",
            "start_time": "12:00",
            "end_time": "14:00",
            "purpose": "Afternoon booking"
        },
        follow_redirects=True
    )

    assert response.status_code == 200

    with client.application.app_context():

        bookings = Booking.query.all()

        assert len(bookings) == 2


def test_unavailable_resource_cannot_be_booked(
    client,
    users_and_resource
):

    user_id, admin_id, resource_id = users_and_resource

    with client.application.app_context():

        resource = db.session.get(
            Resource,
            resource_id
        )

        resource.status = "MAINTENANCE"

        db.session.commit()

    login(
        client,
        "bookinguser@test.com",
        "User@123"
    )

    response = client.post(
        f"/bookings/create/{resource_id}",
        data={
            "booking_date": "2026-10-05",
            "start_time": "10:00",
            "end_time": "12:00",
            "purpose": "Maintenance test"
        },
        follow_redirects=True
    )

    assert b"currently unavailable" in response.data

    with client.application.app_context():

        assert Booking.query.count() == 0


def test_invalid_time_is_rejected(
    client,
    users_and_resource
):

    user_id, admin_id, resource_id = users_and_resource

    login(
        client,
        "bookinguser@test.com",
        "User@123"
    )

    response = client.post(
        f"/bookings/create/{resource_id}",
        data={
            "booking_date": "2026-10-05",
            "start_time": "14:00",
            "end_time": "12:00",
            "purpose": "Invalid time"
        },
        follow_redirects=True
    )

    assert b"End time must be later" in response.data

    with client.application.app_context():

        assert Booking.query.count() == 0


def test_user_can_cancel_own_booking(
    client,
    users_and_resource
):

    user_id, admin_id, resource_id = users_and_resource

    with client.application.app_context():

        from datetime import date, time

        booking = Booking(
            user_id=user_id,
            resource_id=resource_id,
            booking_date=date(2026, 10, 5),
            start_time=time(10, 0),
            end_time=time(12, 0),
            purpose="Cancellation test",
            status="BOOKED"
        )

        db.session.add(booking)
        db.session.commit()

        booking_id = booking.id

    login(
        client,
        "bookinguser@test.com",
        "User@123"
    )

    response = client.get(
        f"/bookings/cancel/{booking_id}",
        follow_redirects=True
    )

    assert response.status_code == 200

    with client.application.app_context():

        booking = db.session.get(
            Booking,
            booking_id
        )

        assert booking.status == "CANCELLED"


def test_cancelled_booking_does_not_block_new_booking(
    client,
    users_and_resource
):

    user_id, admin_id, resource_id = users_and_resource

    with client.application.app_context():

        from datetime import date, time

        booking = Booking(
            user_id=user_id,
            resource_id=resource_id,
            booking_date=date(2026, 10, 5),
            start_time=time(10, 0),
            end_time=time(12, 0),
            purpose="Cancelled booking",
            status="CANCELLED"
        )

        db.session.add(booking)
        db.session.commit()

    login(
        client,
        "bookinguser@test.com",
        "User@123"
    )

    response = client.post(
        f"/bookings/create/{resource_id}",
        data={
            "booking_date": "2026-10-05",
            "start_time": "10:00",
            "end_time": "12:00",
            "purpose": "Replacement booking"
        },
        follow_redirects=True
    )

    assert response.status_code == 200

    with client.application.app_context():

        bookings = Booking.query.filter_by(
            resource_id=resource_id
        ).all()

        assert len(bookings) == 2

        active_bookings = [
            booking
            for booking in bookings
            if booking.status == "BOOKED"
        ]

        assert len(active_bookings) == 1