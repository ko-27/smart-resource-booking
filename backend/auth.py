import secrets
from datetime import datetime, timezone, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user

from .extensions import db
from .models import User

auth = Blueprint("auth", __name__)


@auth.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        department = request.form.get("department", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not department or not password:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("auth.register"))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("An account with this email already exists.", "error")
            return redirect(url_for("auth.register"))

        phone_digits = "".join(filter(str.isdigit, phone)) if phone else None
        if phone_digits and len(phone_digits) > 10:
            phone_digits = phone_digits[-10:]

        user = User(
            name=name,
            email=email,
            department=department,
            phone=phone_digits if phone_digits else None,
            role="USER"
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    active_tab = request.args.get("tab", "email")

    # Clean up expired OTP if any
    otp_phone = session.get("login_phone")
    otp_expiry = session.get("login_otp_expiry")
    has_active_otp = False
    if otp_phone and otp_expiry:
        if datetime.now(timezone.utc).timestamp() <= otp_expiry:
            has_active_otp = True
        else:
            session.pop("login_otp", None)
            session.pop("login_phone", None)
            session.pop("login_otp_expiry", None)
            session.pop("login_user_id", None)
            otp_phone = None

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):

            login_user(user)

            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")

    return render_template(
        "login.html",
        active_tab=active_tab,
        has_active_otp=has_active_otp,
        otp_phone=otp_phone
    )


@auth.route("/login/phone/request-otp", methods=["POST"])
def request_otp():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    raw_phone = request.form.get("phone", "").strip()
    phone_digits = "".join(filter(str.isdigit, raw_phone))

    if len(phone_digits) > 10:
        phone_digits = phone_digits[-10:]

    if not phone_digits or len(phone_digits) < 10:
        flash("Please enter a valid 10-digit phone number.", "error")
        return redirect(url_for("auth.login", tab="phone"))

    user = User.query.filter(User.phone.like(f"%{phone_digits}%")).first()

    if not user:
        flash(f"No account found with phone number {phone_digits}. Please register or login with email.", "error")
        return redirect(url_for("auth.login", tab="phone"))

    # Generate 6-digit numeric OTP
    otp = f"{secrets.randbelow(900000) + 100000}"
    expiry = (datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()

    session["login_otp"] = otp
    session["login_phone"] = phone_digits
    session["login_otp_expiry"] = expiry
    session["login_user_id"] = user.id

    flash(f"Verification code sent for {phone_digits}: {otp} (Valid for 5 minutes).", "info")
    return redirect(url_for("auth.login", tab="phone"))


@auth.route("/login/phone/verify-otp", methods=["POST"])
def verify_otp():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    entered_otp = request.form.get("otp", "").strip()
    stored_otp = session.get("login_otp")
    stored_expiry = session.get("login_otp_expiry")
    user_id = session.get("login_user_id")

    if not stored_otp or not stored_expiry or not user_id:
        flash("No active OTP request found. Please request an OTP first.", "error")
        return redirect(url_for("auth.login", tab="phone"))

    if datetime.now(timezone.utc).timestamp() > stored_expiry:
        session.pop("login_otp", None)
        session.pop("login_phone", None)
        session.pop("login_otp_expiry", None)
        session.pop("login_user_id", None)
        flash("The OTP has expired. Please request a new code.", "error")
        return redirect(url_for("auth.login", tab="phone"))

    if entered_otp != stored_otp:
        flash("Invalid OTP entered. Please try again.", "error")
        return redirect(url_for("auth.login", tab="phone"))

    user = db.session.get(User, user_id)
    if not user:
        flash("Account not found.", "error")
        return redirect(url_for("auth.login"))

    # Clear OTP from session
    session.pop("login_otp", None)
    session.pop("login_phone", None)
    session.pop("login_otp_expiry", None)
    session.pop("login_user_id", None)

    login_user(user)
    flash(f"Welcome back, {user.name}! Signed in successfully via phone verification.", "success")
    return redirect(url_for("dashboard"))


@auth.route("/login/phone/clear", methods=["GET"])
def clear_otp():
    session.pop("login_otp", None)
    session.pop("login_phone", None)
    session.pop("login_otp_expiry", None)
    session.pop("login_user_id", None)
    return redirect(url_for("auth.login", tab="phone"))


@auth.route("/profile/edit", methods=["POST"])
@login_required
def edit_profile():

    name = request.form.get("name", "").strip()
    department = request.form.get("department", "").strip()
    raw_phone = request.form.get("phone", "").strip()

    if not name or not department:
        flash("Name and department cannot be empty.", "error")
        return redirect(request.referrer or url_for("dashboard"))

    phone_digits = "".join(filter(str.isdigit, raw_phone)) if raw_phone else None
    if phone_digits:
        if len(phone_digits) > 10:
            phone_digits = phone_digits[-10:]
        if len(phone_digits) < 10:
            flash("Phone number must be a 10-digit number.", "error")
            return redirect(request.referrer or url_for("dashboard"))

        existing = User.query.filter(User.phone == phone_digits, User.id != current_user.id).first()
        if existing:
            flash("This phone number is already registered to another account.", "error")
            return redirect(request.referrer or url_for("dashboard"))

        current_user.phone = phone_digits
    else:
        current_user.phone = None

    current_user.name = name
    current_user.department = department

    db.session.commit()
    flash("Profile contact details updated successfully.", "success")
    return redirect(request.referrer or url_for("dashboard"))


@auth.route("/logout")
@login_required
def logout():

    logout_user()

    flash("You have been logged out.", "success")

    return redirect(url_for("auth.login"))