from datetime import datetime
from functools import wraps

from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, or_
from werkzeug.security import check_password_hash, generate_password_hash

from ...extensions import db
from ...models import AdminUser, Feedback, InventoryItem, ItemAssignment, ItemRequest, StaffUser
from . import admin_bp
from .forms import (
    AdminLoginForm,
    AdminRegisterForm,
    ApproveRequestForm,
    CompleteReturnForm,
    DeleteItemForm,
    InventoryForm,
    ManualAssignmentForm,
    RejectRequestForm,
)


def admin_only(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or getattr(current_user, "user_role", "") != "admin":
            flash("Please log in as admin to continue.", "warning")
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)

    return wrapped


@admin_bp.route("/")
@login_required
@admin_only
def dashboard():
    latest_items = (
        InventoryItem.query.order_by(InventoryItem.created_at.desc()).limit(3).all()
    )
    inventory_count = InventoryItem.query.count()
    inventory_quantity = (
        db.session.query(func.coalesce(func.sum(InventoryItem.quantity_available), 0)).scalar()
    )
    pending_requests = ItemRequest.query.filter_by(status="pending").count()
    pending_returns = ItemAssignment.query.filter_by(status="return_requested").count()
    return render_template(
        "admin/dashboard.html",
        latest_items=latest_items,
        inventory_count=inventory_count,
        inventory_quantity=inventory_quantity,
        pending_requests=pending_requests,
        pending_returns=pending_returns,
    )


@admin_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated and getattr(current_user, "user_role", "") == "admin":
        return redirect(url_for("admin.dashboard"))

    form = AdminRegisterForm()
    if form.validate_on_submit():
        admin = AdminUser(
            full_name=form.full_name.data.strip(),
            email=form.email.data.lower(),
            password_hash=generate_password_hash(form.password.data),
        )
        db.session.add(admin)
        db.session.commit()
        login_user(admin)
        flash("Admin workspace ready. Welcome!", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/register.html", form=form)


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated and getattr(current_user, "user_role", "") == "admin":
        return redirect(url_for("admin.dashboard"))

    form = AdminLoginForm()
    if form.validate_on_submit():
        admin = AdminUser.query.filter_by(email=form.email.data.lower()).first()
        if not admin or not check_password_hash(admin.password_hash, form.password.data):
            flash("Invalid credentials. Try again.", "danger")
        else:
            login_user(admin)
            flash("Signed in successfully.", "success")
            return redirect(url_for("admin.dashboard"))

    return render_template("admin/login.html", form=form)


@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Signed out.", "info")
    return redirect(url_for("public.role_selection"))


@admin_bp.route("/requests")
@login_required
@admin_only
def requests_queue():
    pending_requests = (
        ItemRequest.query.filter_by(status="pending")
        .order_by(ItemRequest.created_at.asc())
        .all()
    )
    request_history = (
        ItemRequest.query.filter(ItemRequest.status != "pending")
        .order_by(ItemRequest.updated_at.desc())
        .limit(10)
        .all()
    )
    returns_queue = (
        ItemAssignment.query.filter_by(status="return_requested")
        .order_by(ItemAssignment.updated_at.desc())
        .all()
    )

    item_choices = _available_item_choices()
    approve_forms = {}
    reject_forms = {}
    for req in pending_requests:
        approve_form = ApproveRequestForm(prefix=f"approve-{req.id}")
        approve_form.item_id.choices = item_choices
        approve_form.request_id.data = req.id
        approve_forms[req.id] = approve_form

        reject_form = RejectRequestForm(prefix=f"reject-{req.id}")
        reject_form.request_id.data = req.id
        reject_forms[req.id] = reject_form

    return_forms = {}
    for assignment in returns_queue:
        return_form = CompleteReturnForm(prefix=f"return-{assignment.id}")
        return_form.assignment_id.data = assignment.id
        return_forms[assignment.id] = return_form

    manual_form = ManualAssignmentForm()
    manual_form.item_id.choices = item_choices
    manual_form.staff_id.choices = _staff_choices()

    return render_template(
        "admin/requests.html",
        pending_requests=pending_requests,
        request_history=request_history,
        returns_queue=returns_queue,
        approve_forms=approve_forms,
        reject_forms=reject_forms,
        return_forms=return_forms,
        manual_form=manual_form,
        has_inventory=bool(item_choices),
    )


@admin_bp.route("/requests/<int:request_id>/approve", methods=["POST"])
@login_required
@admin_only
def approve_request(request_id: int):
    form = ApproveRequestForm(prefix=f"approve-{request_id}")
    form.item_id.choices = _available_item_choices()
    if not form.validate_on_submit() or int(form.request_id.data) != request_id:
        current_app.logger.warning(
            "Approve request failed validation",
            extra={"request_id": request_id, "errors": form.errors},
        )
        flash("Could not process request approval. Please recheck the form.", "danger")
        return redirect(url_for("admin.requests_queue"))

    request_record = ItemRequest.query.get_or_404(request_id)
    if request_record.status != "pending":
        flash("This request has already been processed.", "info")
        return redirect(url_for("admin.requests_queue"))

    item = InventoryItem.query.get_or_404(form.item_id.data)
    if item.quantity_available <= 0:
        flash("Item is no longer available.", "warning")
        return redirect(url_for("admin.requests_queue"))

    assignment = ItemAssignment(
        item_id=item.id,
        staff_id=request_record.staff_id,
        allocation_date=datetime.utcnow(),
        status="assigned",
    )
    item.quantity_available -= 1
    request_record.status = "approved"
    db.session.add(assignment)
    db.session.commit()
    current_app.logger.info(
        "Request approved",
        extra={"request_id": request_id, "item_id": item.id, "staff_id": request_record.staff_id},
    )
    flash("Request approved and item assigned.", "success")
    return redirect(url_for("admin.requests_queue"))


@admin_bp.route("/requests/<int:request_id>/reject", methods=["POST"])
@login_required
@admin_only
def reject_request(request_id: int):
    form = RejectRequestForm(prefix=f"reject-{request_id}")
    if not form.validate_on_submit() or int(form.request_id.data) != request_id:
        current_app.logger.warning(
            "Reject request failed validation",
            extra={"request_id": request_id, "errors": form.errors},
        )
        flash("Could not reject the request. Please retry.", "danger")
        return redirect(url_for("admin.requests_queue"))

    request_record = ItemRequest.query.get_or_404(request_id)
    if request_record.status != "pending":
        flash("This request has already been processed.", "info")
        return redirect(url_for("admin.requests_queue"))

    request_record.status = "rejected"
    db.session.commit()
    current_app.logger.info(
        "Request rejected", extra={"request_id": request_id, "staff_id": request_record.staff_id}
    )
    flash("Request rejected.", "info")
    return redirect(url_for("admin.requests_queue"))


@admin_bp.route("/assignments/manual", methods=["POST"])
@login_required
@admin_only
def manual_assignment():
    form = ManualAssignmentForm()
    form.item_id.choices = _available_item_choices()
    form.staff_id.choices = _staff_choices()
    if not form.validate_on_submit():
        current_app.logger.warning(
            "Manual assignment failed validation", extra={"errors": form.errors}
        )
        flash("Could not create manual assignment. Check the selections.", "danger")
        return redirect(url_for("admin.requests_queue"))

    item = InventoryItem.query.get_or_404(form.item_id.data)
    staff = StaffUser.query.get_or_404(form.staff_id.data)
    if item.quantity_available <= 0:
        flash("Item is no longer available.", "warning")
        return redirect(url_for("admin.requests_queue"))

    assignment = ItemAssignment(
        item_id=item.id,
        staff_id=staff.id,
        allocation_date=datetime.utcnow(),
        status="assigned",
    )
    item.quantity_available -= 1
    db.session.add(assignment)
    db.session.commit()
    current_app.logger.info(
        "Manual assignment created",
        extra={"item_id": item.id, "staff_id": staff.id},
    )
    flash(f"{item.name} assigned to {staff.full_name}.", "success")
    return redirect(url_for("admin.requests_queue"))


@admin_bp.route("/assignments/<int:assignment_id>/complete-return", methods=["POST"])
@login_required
@admin_only
def complete_return(assignment_id: int):
    form = CompleteReturnForm(prefix=f"return-{assignment_id}")
    if not form.validate_on_submit() or int(form.assignment_id.data) != assignment_id:
        current_app.logger.warning(
            "Return completion failed validation",
            extra={"assignment_id": assignment_id, "errors": form.errors},
        )
        flash("Could not process return. Please retry.", "danger")
        return redirect(url_for("admin.requests_queue"))

    assignment = ItemAssignment.query.get_or_404(assignment_id)
    if assignment.status != "return_requested":
        flash("This assignment is not pending return.", "info")
        return redirect(url_for("admin.requests_queue"))

    assignment.status = "returned"
    assignment.return_date = datetime.utcnow()
    if assignment.item:
        assignment.item.quantity_available += 1
    db.session.commit()
    current_app.logger.info(
        "Return completed",
        extra={"assignment_id": assignment_id, "item_id": assignment.item_id},
    )
    flash("Return completed and inventory updated.", "success")
    return redirect(url_for("admin.requests_queue"))


@admin_bp.route("/reports")
@login_required
@admin_only
def reports():
    avg_rating = db.session.query(func.avg(Feedback.rating)).scalar()
    total_feedback = Feedback.query.count()
    recent_feedback = (
        Feedback.query.order_by(Feedback.created_at.desc()).limit(10).all()
    )
    low_stock = (
        InventoryItem.query.filter(InventoryItem.quantity_available <= 3)
        .order_by(InventoryItem.quantity_available.asc())
        .all()
    )
    active_assignments = ItemAssignment.query.filter_by(status="assigned").count()
    return render_template(
        "admin/reports.html",
        avg_rating=avg_rating,
        total_feedback=total_feedback,
        recent_feedback=recent_feedback,
        low_stock=low_stock,
        active_assignments=active_assignments,
    )


@admin_bp.route("/inventory")
@login_required
@admin_only
def inventory():
    search_query = request.args.get("q", "").strip()
    items_query = InventoryItem.query
    if search_query:
        pattern = f"%{search_query}%"
        items_query = items_query.filter(
            or_(
                InventoryItem.name.ilike(pattern),
                InventoryItem.category.ilike(pattern),
            )
        )

    items = items_query.order_by(InventoryItem.created_at.desc()).all()
    stats = {
        "total_items": InventoryItem.query.count(),
        "total_quantity": (
            db.session.query(
                func.coalesce(func.sum(InventoryItem.quantity_available), 0)
            ).scalar()
            or 0
        ),
        "average_price": db.session.query(func.avg(InventoryItem.price)).scalar(),
    }
    delete_form = DeleteItemForm()
    return render_template(
        "admin/inventory_list.html",
        items=items,
        search_query=search_query,
        stats=stats,
        delete_form=delete_form,
    )


@admin_bp.route("/inventory/new", methods=["GET", "POST"])
@login_required
@admin_only
def inventory_create():
    form = InventoryForm()
    if form.validate_on_submit():
        item = InventoryItem(
            name=form.name.data.strip(),
            category=form.category.data.strip(),
            quantity_available=form.quantity.data,
            purchase_date=form.purchase_date.data,
            price=form.price.data,
        )
        db.session.add(item)
        db.session.commit()
        flash("Inventory item added.", "success")
        return redirect(url_for("admin.inventory"))

    return render_template(
        "admin/inventory_form.html",
        form=form,
        mode="create",
    )


@admin_bp.route("/inventory/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
@admin_only
def inventory_edit(item_id: int):
    item = InventoryItem.query.get_or_404(item_id)
    form = InventoryForm(obj=item)
    if form.validate_on_submit():
        item.name = form.name.data.strip()
        item.category = form.category.data.strip()
        item.quantity_available = form.quantity.data
        item.purchase_date = form.purchase_date.data
        item.price = form.price.data
        db.session.commit()
        flash("Inventory item updated.", "success")
        return redirect(url_for("admin.inventory"))

    return render_template(
        "admin/inventory_form.html",
        form=form,
        mode="edit",
        item=item,
    )


@admin_bp.route("/inventory/<int:item_id>/delete", methods=["POST"])
@login_required
@admin_only
def inventory_delete(item_id: int):
    form = DeleteItemForm()
    if not form.validate_on_submit():
        abort(400)
    item = InventoryItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Inventory item removed.", "info")
    return redirect(url_for("admin.inventory"))


def _available_item_choices():
    items = (
        InventoryItem.query.filter(InventoryItem.quantity_available > 0)
        .order_by(InventoryItem.name.asc())
        .all()
    )
    return [
        (item.id, f"{item.name} · {item.quantity_available} available")
        for item in items
    ]


def _staff_choices():
    staff_members = StaffUser.query.order_by(StaffUser.full_name.asc()).all()
    return [(member.id, member.full_name) for member in staff_members]

