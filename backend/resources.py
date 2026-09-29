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
from .models import Resource


resources = Blueprint(
    "resources",
    __name__,
    url_prefix="/resources"
)


@resources.route("/")
@login_required
def list_resources():

    search = request.args.get("search", "").strip()
    resource_type = request.args.get("resource_type", "").strip()
    status = request.args.get("status", "").strip()

    query = Resource.query

    if search:
        query = query.filter(
            db.or_(
                Resource.name.ilike(f"%{search}%"),
                Resource.location.ilike(f"%{search}%"),
                Resource.description.ilike(f"%{search}%")
            )
        )

    if resource_type:
        query = query.filter(
            Resource.resource_type == resource_type
        )

    if status:
        query = query.filter(
            Resource.status == status
        )

    resource_list = query.order_by(
        Resource.created_at.desc()
    ).all()

    return render_template(
        "resources/list.html",
        resources=resource_list,
        search=search,
        resource_type=resource_type,
        status=status
    )


@resources.route("/add", methods=["GET", "POST"])
@login_required
def add_resource():

    if current_user.role != "ADMIN":

        flash(
            "Administrator access required.",
            "error"
        )

        return redirect(
            url_for("resources.list_resources")
        )

    if request.method == "POST":

        name = request.form.get(
            "name", ""
        ).strip()

        resource_type = request.form.get(
            "resource_type", ""
        ).strip()

        description = request.form.get(
            "description", ""
        ).strip()

        location = request.form.get(
            "location", ""
        ).strip()

        capacity = request.form.get(
            "capacity", ""
        ).strip()

        if not name or not resource_type or not location:

            flash(
                "Name, resource type and location are required.",
                "error"
            )

            return redirect(
                url_for("resources.add_resource")
            )

        try:

            capacity = int(capacity)

            if capacity <= 0:
                raise ValueError

        except ValueError:

            flash(
                "Capacity must be a positive number.",
                "error"
            )

            return redirect(
                url_for("resources.add_resource")
            )

        resource = Resource(
            name=name,
            resource_type=resource_type,
            description=description,
            location=location,
            capacity=capacity,
            status="AVAILABLE",
            created_by=current_user.id
        )

        db.session.add(resource)
        db.session.commit()

        flash(
            "Resource added successfully.",
            "success"
        )

        return redirect(
            url_for("resources.list_resources")
        )

    return render_template(
        "resources/add.html"
    )


@resources.route(
    "/edit/<int:resource_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_resource(resource_id):

    if current_user.role != "ADMIN":

        flash(
            "Administrator access required.",
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

    if request.method == "POST":

        name = request.form.get(
            "name", ""
        ).strip()

        resource_type = request.form.get(
            "resource_type", ""
        ).strip()

        description = request.form.get(
            "description", ""
        ).strip()

        location = request.form.get(
            "location", ""
        ).strip()

        capacity = request.form.get(
            "capacity", ""
        ).strip()

        status = request.form.get(
            "status", ""
        ).strip()

        if not name or not resource_type or not location:

            flash(
                "Name, resource type and location are required.",
                "error"
            )

            return redirect(
                url_for(
                    "resources.edit_resource",
                    resource_id=resource.id
                )
            )

        try:

            capacity = int(capacity)

            if capacity <= 0:
                raise ValueError

        except ValueError:

            flash(
                "Capacity must be a positive number.",
                "error"
            )

            return redirect(
                url_for(
                    "resources.edit_resource",
                    resource_id=resource.id
                )
            )

        allowed_statuses = {
            "AVAILABLE",
            "UNAVAILABLE",
            "MAINTENANCE"
        }

        if status not in allowed_statuses:

            flash(
                "Invalid resource status.",
                "error"
            )

            return redirect(
                url_for(
                    "resources.edit_resource",
                    resource_id=resource.id
                )
            )

        resource.name = name
        resource.resource_type = resource_type
        resource.description = description
        resource.location = location
        resource.capacity = capacity
        resource.status = status

        db.session.commit()

        flash(
            "Resource updated successfully.",
            "success"
        )

        return redirect(
            url_for("resources.list_resources")
        )

    return render_template(
        "resources/edit.html",
        resource=resource
    )


@resources.route(
    "/deactivate/<int:resource_id>"
)
@login_required
def deactivate_resource(resource_id):

    if current_user.role != "ADMIN":

        flash(
            "Administrator access required.",
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

    resource.status = "UNAVAILABLE"

    db.session.commit()

    flash(
        "Resource marked as unavailable.",
        "success"
    )

    return redirect(
        url_for("resources.list_resources")
    )