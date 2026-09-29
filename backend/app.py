from flask import Flask, render_template
from flask_login import current_user, login_required

from .config import Config
from .extensions import db, login_manager
from .models import User, Resource, Booking
from .auth import auth
from .resources import resources
from .bookings import bookings

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

            return render_template(
                "dashboard.html",
                user=current_user,
                resource_count=resource_count,
                booked_count=booked_count,
                pending_count=pending_count
            )

        requested_count = Booking.query.filter_by(
            user_id=current_user.id
        ).count()

        approved_count = Booking.query.filter_by(
            user_id=current_user.id,
            status="BOOKED"
        ).count()

        rejected_count = Booking.query.filter_by(
            user_id=current_user.id,
            status="REJECTED"
        ).count()

        cancelled_count = Booking.query.filter_by(
            user_id=current_user.id,
            status="CANCELLED"
        ).count()

        return render_template(
            "dashboard.html",
            user=current_user,
            requested_count=requested_count,
            approved_count=approved_count,
            rejected_count=rejected_count,
            cancelled_count=cancelled_count
        )

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