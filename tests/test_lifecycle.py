from datetime import date, time, datetime, timedelta
import pytest

from backend.app import create_app
from backend.extensions import db
from backend.models import User, Resource, Booking
from backend.services import update_booking_lifecycles


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
def base_data(app):
    with app.app_context():
        admin = User(
            name="Admin User",
            email="admin@test.com",
            department="IT",
            role="ADMIN"
        )
        admin.set_password("Admin@123")

        user = User(
            name="Normal User",
            email="user@test.com",
            department="IT",
            role="USER"
        )
        user.set_password("User@123")

        db.session.add_all([admin, user])
        db.session.commit()

        resource_available = Resource(
            name="Conference Room A",
            resource_type="ROOM",
            description="Main conference room",
            location="Building 1",
            capacity=20,
            status="AVAILABLE",
            created_by=admin.id
        )

        resource_maintenance = Resource(
            name="Server Lab",
            resource_type="LAB",
            description="Server equipment",
            location="Building 2",
            capacity=10,
            status="MAINTENANCE",
            created_by=admin.id
        )

        resource_unavailable = Resource(
            name="Projector 1",
            resource_type="EQUIPMENT",
            description="HD Projector",
            location="Building 1",
            capacity=1,
            status="UNAVAILABLE",
            created_by=admin.id
        )

        db.session.add_all([resource_available, resource_maintenance, resource_unavailable])
        db.session.commit()

        return {
            "admin_id": admin.id,
            "user_id": user.id,
            "res_avail_id": resource_available.id,
            "res_maint_id": resource_maintenance.id,
            "res_unavail_id": resource_unavailable.id,
        }


def test_booked_reservation_in_past_becomes_completed(app, base_data):
    """1. A booked reservation whose end time is in the past becomes COMPLETED."""
    fixed_now = datetime(2026, 10, 15, 14, 0, 0)

    with app.app_context():
        booking = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_avail_id"],
            booking_date=date(2026, 10, 15),
            start_time=time(10, 0),
            end_time=time(12, 0),
            purpose="Completed meeting",
            status="BOOKED"
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

        result = update_booking_lifecycles(current_dt=fixed_now)
        assert result["completed"] == 1

        b = db.session.get(Booking, booking_id)
        assert b.status == "COMPLETED"


def test_pending_request_in_past_becomes_expired(app, base_data):
    """2. A pending request whose end time is in the past becomes EXPIRED."""
    fixed_now = datetime(2026, 10, 15, 14, 0, 0)

    with app.app_context():
        booking = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_avail_id"],
            booking_date=date(2026, 10, 15),
            start_time=time(9, 0),
            end_time=time(11, 0),
            purpose="Unapproved request",
            status="PENDING"
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

        result = update_booking_lifecycles(current_dt=fixed_now)
        assert result["expired"] == 1

        b = db.session.get(Booking, booking_id)
        assert b.status == "EXPIRED"


def test_future_bookings_remain_unchanged(app, base_data):
    """3. Future bookings remain unchanged."""
    fixed_now = datetime(2026, 10, 15, 12, 0, 0)

    with app.app_context():
        future_booked = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_avail_id"],
            booking_date=date(2026, 10, 16),
            start_time=time(10, 0),
            end_time=time(12, 0),
            purpose="Tomorrow booking",
            status="BOOKED"
        )
        later_today_pending = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_avail_id"],
            booking_date=date(2026, 10, 15),
            start_time=time(14, 0),
            end_time=time(16, 0),
            purpose="Later today pending",
            status="PENDING"
        )
        db.session.add_all([future_booked, later_today_pending])
        db.session.commit()

        result = update_booking_lifecycles(current_dt=fixed_now)
        assert result["completed"] == 0
        assert result["expired"] == 0

        b1 = db.session.get(Booking, future_booked.id)
        b2 = db.session.get(Booking, later_today_pending.id)
        assert b1.status == "BOOKED"
        assert b2.status == "PENDING"


def test_rejected_and_cancelled_bookings_retain_status(app, base_data):
    """4. Rejected and cancelled bookings retain their status."""
    fixed_now = datetime(2026, 10, 15, 18, 0, 0)

    with app.app_context():
        rejected_booking = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_avail_id"],
            booking_date=date(2026, 10, 10),
            start_time=time(9, 0),
            end_time=time(10, 0),
            purpose="Past rejected",
            status="REJECTED"
        )
        cancelled_booking = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_avail_id"],
            booking_date=date(2026, 10, 10),
            start_time=time(11, 0),
            end_time=time(12, 0),
            purpose="Past cancelled",
            status="CANCELLED"
        )
        db.session.add_all([rejected_booking, cancelled_booking])
        db.session.commit()

        result = update_booking_lifecycles(current_dt=fixed_now)
        assert result["completed"] == 0
        assert result["expired"] == 0

        b1 = db.session.get(Booking, rejected_booking.id)
        b2 = db.session.get(Booking, cancelled_booking.id)
        assert b1.status == "REJECTED"
        assert b2.status == "CANCELLED"


def test_completed_and_expired_do_not_block_new_reservations(client, base_data):
    """5. Completed and expired bookings do not block new reservations."""
    fixed_now = datetime(2026, 10, 15, 14, 0, 0)

    with client.application.app_context():
        completed = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_avail_id"],
            booking_date=date(2026, 10, 15),
            start_time=time(10, 0),
            end_time=time(12, 0),
            purpose="Past reservation",
            status="COMPLETED"
        )
        expired = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_avail_id"],
            booking_date=date(2026, 10, 15),
            start_time=time(12, 0),
            end_time=time(13, 0),
            purpose="Past expired request",
            status="EXPIRED"
        )
        db.session.add_all([completed, expired])
        db.session.commit()

    # Log in and create booking on the exact same resource for future slot
    client.post("/login", data={"email": "user@test.com", "password": "User@123"}, follow_redirects=True)

    response = client.post(
        f"/bookings/create/{base_data['res_avail_id']}",
        data={
            "booking_date": "2026-10-15",
            "start_time": "14:00",
            "end_time": "16:00",
            "purpose": "New afternoon booking"
        },
        follow_redirects=True
    )
    assert response.status_code == 200

    with client.application.app_context():
        new_booking = Booking.query.filter_by(purpose="New afternoon booking").first()
        assert new_booking is not None
        assert new_booking.status == "PENDING"


def test_unavailable_and_maintenance_resources_remain_unchanged(app, base_data):
    """6 & 7. Resources in UNAVAILABLE or MAINTENANCE retain their operational status."""
    fixed_now = datetime(2026, 10, 15, 16, 0, 0)

    with app.app_context():
        b_maint = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_maint_id"],
            booking_date=date(2026, 10, 15),
            start_time=time(9, 0),
            end_time=time(11, 0),
            purpose="Diagnostic run",
            status="BOOKED"
        )
        b_unavail = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_unavail_id"],
            booking_date=date(2026, 10, 15),
            start_time=time(9, 0),
            end_time=time(11, 0),
            purpose="Testing run",
            status="BOOKED"
        )
        db.session.add_all([b_maint, b_unavail])
        db.session.commit()

        update_booking_lifecycles(current_dt=fixed_now)

        res_m = db.session.get(Resource, base_data["res_maint_id"])
        res_u = db.session.get(Resource, base_data["res_unavail_id"])
        assert res_m.status == "MAINTENANCE"
        assert res_u.status == "UNAVAILABLE"


def test_completed_booking_remains_visible_in_history(client, base_data):
    """8. A completed booking remains visible in booking history."""
    with client.application.app_context():
        completed = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_avail_id"],
            booking_date=date(2026, 10, 10),
            start_time=time(10, 0),
            end_time=time(12, 0),
            purpose="Historical presentation",
            status="COMPLETED"
        )
        db.session.add(completed)
        db.session.commit()

    client.post("/login", data={"email": "user@test.com", "password": "User@123"}, follow_redirects=True)
    resp = client.get("/bookings/")
    assert resp.status_code == 200
    assert b"Historical presentation" in resp.data
    assert b"COMPLETED" in resp.data


def test_idempotency_of_lifecycle_service(app, base_data):
    """9. The completion service can execute repeatedly without errors or duplicate changes."""
    fixed_now = datetime(2026, 10, 15, 14, 0, 0)

    with app.app_context():
        b1 = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_avail_id"],
            booking_date=date(2026, 10, 15),
            start_time=time(10, 0),
            end_time=time(12, 0),
            purpose="Meeting 1",
            status="BOOKED"
        )
        b2 = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_avail_id"],
            booking_date=date(2026, 10, 15),
            start_time=time(9, 0),
            end_time=time(11, 0),
            purpose="Request 1",
            status="PENDING"
        )
        db.session.add_all([b1, b2])
        db.session.commit()

        # Run 1: transitions occur
        res1 = update_booking_lifecycles(current_dt=fixed_now)
        assert res1["completed"] == 1
        assert res1["expired"] == 1

        # Run 2: immediately afterwards, no extra changes
        res2 = update_booking_lifecycles(current_dt=fixed_now)
        assert res2["completed"] == 0
        assert res2["expired"] == 0

        # Run 3: still clean
        res3 = update_booking_lifecycles(current_dt=fixed_now)
        assert res3["completed"] == 0
        assert res3["expired"] == 0


def test_time_boundary_conditions(app, base_data):
    """10. Time-zone and end-time boundary conditions are handled correctly."""
    fixed_now = datetime(2026, 10, 15, 12, 0, 0)

    with app.app_context():
        # Exact boundary: end_time == fixed_now.time() -> SHOULD complete
        exact_end = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_avail_id"],
            booking_date=date(2026, 10, 15),
            start_time=time(10, 0),
            end_time=time(12, 0),
            purpose="Exact boundary",
            status="BOOKED"
        )
        # 1 minute in future: end_time > fixed_now.time() -> SHOULD NOT complete
        future_minute = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_avail_id"],
            booking_date=date(2026, 10, 15),
            start_time=time(11, 0),
            end_time=time(12, 1),
            purpose="Future by one minute",
            status="BOOKED"
        )
        # Yesterday: booking_date < fixed_now.date() -> SHOULD complete
        yesterday_booking = Booking(
            user_id=base_data["user_id"],
            resource_id=base_data["res_avail_id"],
            booking_date=date(2026, 10, 14),
            start_time=time(16, 0),
            end_time=time(18, 0),
            purpose="Yesterday booking",
            status="BOOKED"
        )

        db.session.add_all([exact_end, future_minute, yesterday_booking])
        db.session.commit()

        res = update_booking_lifecycles(current_dt=fixed_now)
        assert res["completed"] == 2  # exact_end + yesterday_booking

        b_exact = db.session.get(Booking, exact_end.id)
        b_future = db.session.get(Booking, future_minute.id)
        b_yesterday = db.session.get(Booking, yesterday_booking.id)

        assert b_exact.status == "COMPLETED"
        assert b_future.status == "BOOKED"
        assert b_yesterday.status == "COMPLETED"
