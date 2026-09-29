from flask import Flask, render_template
from flask_login import current_user, login_required

from .config import Config
from .extensions import db, login_manager
from .models import User
from .auth import auth

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

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/dashboard")
    @login_required
    def dashboard():
        return render_template("dashboard.html", user=current_user)

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