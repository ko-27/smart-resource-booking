from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)
from flask_login import login_required, current_user

from .extensions import db
from .models import Booking, Resource


bookings = Blueprint(
    "bookings",
    __name__,
    url_prefix="/bookings"
)


@bookings.route("/")
@login_required
def list_bookings():

    status_filter = request.args.get(
        "status",
        ""
    ).strip()

    if current_user.role == "ADMIN":

        query = Booking.query

    else:

        query = Booking.query.filter_by(
            user_id=current_user.id
        )

    if status_filter:

        query = query.filter(
            Booking.status == status_filter
        )

    booking_list = query.order_by(
        Booking.booking_date.desc(),
        Booking.start_time.desc()
    ).all()

    return render_template(
        "bookings/list.html",
        bookings=booking_list,
        status_filter=status_filter
    )


@bookings.route(
    "/create/<int:resource_id>",
    methods=["GET", "POST"]
)
@login_required
def create_booking(resource_id):

    if current_user.role == "ADMIN":

        flash(
            "Administrators cannot create booking requests.",
            "error"
        )

        return redirect(
            url_for("resources.list_resources")
        )

    resource = db.session.get(
        Resource,
        resource_id
    )

    if resource is None:

        flash(
            "Resource not found.",
            "error"
        )

        return redirect(
            url_for("resources.list_resources")
        )

    if resource.status != "AVAILABLE":

        flash(
            "This resource is currently unavailable.",
            "error"
        )

        return redirect(
            url_for("resources.list_resources")
        )

    if request.method == "POST":

        booking_date_text = request.form.get(
            "booking_date",
            ""
        ).strip()

        start_time_text = request.form.get(
            "start_time",
            ""
        ).strip()

        end_time_text = request.form.get(
            "end_time",
            ""
        ).strip()

        purpose = request.form.get(
            "purpose",
            ""
        ).strip()

        if not booking_date_text or not start_time_text or not end_time_text:
            flash(
                "Date, start time and end time are required.",
                "error"
            )

            return redirect(
                url_for(
                    "bookings.create_booking",
                    resource_id=resource.id
                )
            )

        if not purpose:

            flash(
                "Booking purpose is required.",
                "error"
            )

            return redirect(
                url_for(
                    "bookings.create_booking",
                    resource_id=resource.id
                )
            )

        try:

            booking_date = datetime.strptime(
                booking_date_text,
                "%Y-%m-%d"
            ).date()

            start_time = datetime.strptime(
                start_time_text,
                "%H:%M"
            ).time()

            end_time = datetime.strptime(
                end_time_text,
                "%H:%M"
            ).time()

        except ValueError:

            flash(
                "Invalid date or time format.",
                "error"
            )

            return redirect(
                url_for(
                    "bookings.create_booking",
                    resource_id=resource.id
                )
            )

        if start_time >= end_time:

            flash(
                "End time must be later than start time.",
                "error"
            )

            return redirect(
                url_for(
                    "bookings.create_booking",
                    resource_id=resource.id
                )
            )

        existing_booking = Booking.query.filter(
              Booking.resource_id == resource.id,
              Booking.booking_date == booking_date,
              Booking.status.in_(["PENDING", "BOOKED"]),
              Booking.start_time < end_time,
              Booking.end_time > start_time
         ).first()

        if existing_booking:

            flash(
                 "The resource is already requested or booked for the selected time slot.",
                 "error"
            )

            return redirect(
                url_for(
                     "resources.list_resources"
                )
            )

        booking = Booking(
            user_id=current_user.id,
            resource_id=resource.id,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            purpose=purpose,
            status="PENDING"
        )

        db.session.add(booking)
        db.session.commit()

        flash(
           "Booking request submitted successfully. Waiting for administrator approval.",
            "success"
        )

        return redirect(
            url_for("bookings.list_bookings")
        )

    return render_template(
        "bookings/create.html",
        resource=resource
    )


@bookings.route(
    "/cancel/<int:booking_id>"
)
@login_required
def cancel_booking(booking_id):

    booking = db.session.get(
        Booking,
        booking_id
    )

    if booking is None:

        flash(
            "Booking not found.",
            "error"
        )

        return redirect(
            url_for("bookings.list_bookings")
        )

    if (
        current_user.role != "ADMIN"
        and booking.user_id != current_user.id
    ):

        flash(
            "You are not authorized to cancel this booking.",
            "error"
        )

        return redirect(
            url_for("bookings.list_bookings")
        )

    if booking.status == "CANCELLED":

        flash(
            "Booking is already cancelled.",
            "error"
        )

        return redirect(
            url_for("bookings.list_bookings")
        )

    booking.status = "CANCELLED"

    db.session.commit()

    flash(
        "Booking cancelled successfully.",
        "success"
    )

    return redirect(
        url_for("bookings.list_bookings")
    )
@bookings.route(
    "/approve/<int:booking_id>"
)
@login_required
def approve_booking(booking_id):

    if current_user.role != "ADMIN":

        flash(
            "Administrator access required.",
            "error"
        )

        return redirect(
            url_for("bookings.list_bookings")
        )

    booking = db.session.get(
        Booking,
        booking_id
    )

    if booking is None:

        flash(
            "Booking not found.",
            "error"
        )

        return redirect(
            url_for("bookings.list_bookings")
        )

    if booking.status != "PENDING":

        flash(
            "Only pending bookings can be approved.",
            "error"
        )

        return redirect(
            url_for("bookings.list_bookings")
        )

    conflicting_booking = Booking.query.filter(
        Booking.id != booking.id,
        Booking.resource_id == booking.resource_id,
        Booking.booking_date == booking.booking_date,
        Booking.status == "BOOKED",
        Booking.start_time < booking.end_time,
        Booking.end_time > booking.start_time
    ).first()

    if conflicting_booking:

        flash(
            "Cannot approve this booking because the resource is already booked for the selected time slot.",
            "error"
        )

        return redirect(
            url_for("bookings.list_bookings")
        )

    booking.status = "BOOKED"

    db.session.commit()

    flash(
        "Booking approved successfully.",
        "success"
    )

    return redirect(
        url_for("bookings.list_bookings")
    )

@bookings.route(
    "/reject/<int:booking_id>"
)
@login_required
def reject_booking(booking_id):

    if current_user.role != "ADMIN":

        flash(
            "Administrator access required.",
            "error"
        )

        return redirect(
            url_for("bookings.list_bookings")
        )

    booking = db.session.get(
        Booking,
        booking_id
    )

    if booking is None:

        flash(
            "Booking not found.",
            "error"
        )

        return redirect(
            url_for("bookings.list_bookings")
        )

    if booking.status != "PENDING":

        flash(
            "Only pending bookings can be rejected.",
            "error"
        )

        return redirect(
            url_for("bookings.list_bookings")
        )

    booking.status = "REJECTED"

    db.session.commit()

    flash(
        "Booking rejected successfully.",
        "success"
    )

    return redirect(
        url_for("bookings.list_bookings")
    )