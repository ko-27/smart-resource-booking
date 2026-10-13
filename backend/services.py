import os
import threading
import time
from datetime import datetime

from .extensions import db
from .models import Booking, Resource

# Thread synchronization lock to prevent duplicate schedulers
_scheduler_lock = threading.Lock()
_scheduler_started = False


def update_booking_lifecycles(current_dt=None):
    """
    Identifies overdue bookings and transitions their lifecycle status:
      - BOOKED reservations past their scheduled end time -> COMPLETED
      - PENDING requests past their scheduled end time -> EXPIRED
    
    Preserves terminal statuses (REJECTED, CANCELLED, COMPLETED, EXPIRED).
    Preserves Resource administrative status (AVAILABLE, UNAVAILABLE, MAINTENANCE).
    Is safe to run repeatedly (idempotent) and runs in a database transaction.
    
    Returns a dict with transition counts: {"completed": int, "expired": int}
    """
    if current_dt is None:
        now = datetime.now()
    else:
        now = current_dt

    current_date = now.date()
    current_time = now.time()

    completed_count = 0
    expired_count = 0

    try:
        # Overdue bookings are those where:
        # 1. Date is strictly in the past (< current_date), OR
        # 2. Date is today (== current_date) AND end_time <= current_time
        overdue_bookings = Booking.query.filter(
            Booking.status.in_(["PENDING", "BOOKED"]),
            db.or_(
                Booking.booking_date < current_date,
                db.and_(
                    Booking.booking_date == current_date,
                    Booking.end_time <= current_time
                )
            )
        ).all()

        for booking in overdue_bookings:
            if booking.status == "BOOKED":
                booking.status = "COMPLETED"
                completed_count += 1
            elif booking.status == "PENDING":
                booking.status = "EXPIRED"
                expired_count += 1

        if completed_count > 0 or expired_count > 0:
            db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    return {
        "completed": completed_count,
        "expired": expired_count
    }


def start_booking_lifecycle_scheduler(app, interval_seconds=30):
    """
    Starts a background daemon thread that periodically calls update_booking_lifecycles.
    Safely ignores start requests when:
      - Running inside automated tests (app.config['TESTING'])
      - Running in Werkzeug reload master process
      - Already started
    """
    global _scheduler_started

    if app.config.get("TESTING"):
        return

    # In Flask debug / reload mode, avoid starting in the parent monitoring process
    if os.environ.get("WERKZEUG_RUN_MAIN") == "false":
        return

    with _scheduler_lock:
        if _scheduler_started:
            return
        _scheduler_started = True

        def run_periodic_updates():
            while True:
                time.sleep(interval_seconds)
                with app.app_context():
                    try:
                        update_booking_lifecycles()
                    except Exception as e:
                        app.logger.error(f"Error in booking lifecycle background update: {e}")

        worker_thread = threading.Thread(
            target=run_periodic_updates,
            name="BookingLifecycleScheduler",
            daemon=True
        )
        worker_thread.start()
