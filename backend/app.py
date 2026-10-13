from flask import Flask, render_template, request
from flask_login import current_user, login_required

from .config import Config
from .extensions import db, login_manager
from .models import User, Resource, Booking
from .auth import auth
from .resources import resources
from .bookings import bookings
from .services import update_booking_lifecycles, start_booking_lifecycle_scheduler

def create_app(test_config=None):

    app = Flask(__name__)

    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    app.register_blueprint(auth)
    app.register_blueprint(resources)
    app.register_blueprint(bookings)

    # Automatic booking lifecycle scheduler (runs periodically in background)
    start_booking_lifecycle_scheduler(app, interval_seconds=30)

    # Automatic booking lifecycle check on incoming web requests
    @app.before_request
    def check_booking_lifecycles():
        if app.config.get("TESTING"):
            return
        if not request.path.startswith("/static"):
            try:
                update_booking_lifecycles()
            except Exception:
                db.session.rollback()

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/dashboard")
    @login_required
    def dashboard():

        if current_user.role == "ADMIN":

            resource_count = Resource.query.count()

            booked_count = Booking.query.filter_by(
                status="BOOKED"
            ).count()

            pending_count = Booking.query.filter_by(
                status="PENDING"
            ).count()

            completed_count = Booking.query.filter_by(
                status="COMPLETED"
            ).count()

            expired_count = Booking.query.filter_by(
                status="EXPIRED"
            ).count()

            return render_template(
                "dashboard.html",
                user=current_user,
                resource_count=resource_count,
                booked_count=booked_count,
                pending_count=pending_count,
                completed_count=completed_count,
                expired_count=expired_count
            )

        requested_count = Booking.query.filter_by(
            user_id=current_user.id
        ).count()

        approved_count = Booking.query.filter_by(
            user_id=current_user.id,
            status="BOOKED"
        ).count()

        completed_count = Booking.query.filter_by(
            user_id=current_user.id,
            status="COMPLETED"
        ).count()

        rejected_count = Booking.query.filter_by(
            user_id=current_user.id,
            status="REJECTED"
        ).count()

        cancelled_count = Booking.query.filter_by(
            user_id=current_user.id,
            status="CANCELLED"
        ).count()

        expired_count = Booking.query.filter_by(
            user_id=current_user.id,
            status="EXPIRED"
        ).count()

        return render_template(
            "dashboard.html",
            user=current_user,
            requested_count=requested_count,
            approved_count=approved_count,
            completed_count=completed_count,
            rejected_count=rejected_count,
            cancelled_count=cancelled_count,
            expired_count=expired_count
        )

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("errors/404.html"), 404


    @app.errorhandler(500)
    def internal_server_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500


    @app.cli.command("create-admin")
    def create_admin():

        name = input("Admin name: ")
        email = input("Admin email: ")
        password = input("Admin password: ")
        department = input("Department: ")

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            print("A user with this email already exists.")
            return

        admin = User(
            name=name,
            email=email,
            department=department,
            role="ADMIN"
        )

        admin.set_password(password)

        db.session.add(admin)
        db.session.commit()

        print("Admin account created successfully.")


    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)