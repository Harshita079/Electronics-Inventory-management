from functools import wraps

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from ...extensions import db
from ...models import Feedback, ItemAssignment, ItemRequest, StaffUser
from . import staff_bp
from .forms import FeedbackForm, StaffLoginForm, StaffRegisterForm, StaffRequestItemForm


def staff_only(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or getattr(current_user, "user_role", "") != "staff":
            flash("Please log in as staff to continue.", "warning")
            return redirect(url_for("staff.login"))
        return view(*args, **kwargs)

    return wrapped


@staff_bp.route("/")
@login_required
@staff_only
def dashboard():
    assignments = (
        ItemAssignment.query.filter_by(staff_id=current_user.id)
        .order_by(ItemAssignment.created_at.desc())
        .all()
    )
    outstanding_requests = (
        ItemRequest.query.filter_by(staff_id=current_user.id)
        .order_by(ItemRequest.created_at.desc())
        .all()
    )
    form = StaffRequestItemForm()
    feedback_form = FeedbackForm()
    return render_template(
        "staff/dashboard.html",
        assignments=assignments,
        form=form,
        requests=outstanding_requests,
        feedback_form=feedback_form,
    )


@staff_bp.route("/requests", methods=["POST"])
@login_required
@staff_only
def submit_request():
    form = StaffRequestItemForm()
    if form.validate_on_submit():
        request_record = ItemRequest(
            staff_id=current_user.id,
            item_name=form.item_name.data.strip(),
            justification=form.justification.data.strip(),
        )
        db.session.add(request_record)
        db.session.commit()
        current_app.logger.info(
            "Staff request submitted",
            extra={"staff_id": current_user.id, "item_name": form.item_name.data},
        )
        flash("Request submitted. Admin will review shortly.", "success")
    else:
        current_app.logger.warning(
            "Staff request failed validation",
            extra={"staff_id": current_user.id, "errors": form.errors},
        )
        flash("Please fix the errors and try again.", "danger")

    return redirect(url_for("staff.dashboard"))


@staff_bp.route("/feedback", methods=["POST"])
@login_required
@staff_only
def submit_feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        feedback = Feedback(
            staff_id=current_user.id,
            rating=form.rating.data,
            question_1=form.question_1.data.strip(),
            question_2=form.question_2.data.strip(),
            question_3=form.question_3.data.strip(),
            question_4=form.question_4.data.strip(),
            question_5=form.question_5.data.strip(),
        )
        db.session.add(feedback)
        db.session.commit()
        current_app.logger.info(
            "Feedback submitted", extra={"staff_id": current_user.id, "rating": form.rating.data}
        )
        flash("Thank you for your feedback!", "success")
        return redirect(url_for("staff.thank_you"))
    current_app.logger.warning(
        "Feedback submission failed",
        extra={"staff_id": current_user.id, "errors": form.errors},
    )
    flash("Please complete all fields before submitting feedback.", "danger")
    return redirect(url_for("staff.dashboard"))


@staff_bp.route("/feedback/thanks")
@login_required
@staff_only
def thank_you():
    return render_template("staff/thank_you.html")


@staff_bp.route("/assignments/<int:assignment_id>/return", methods=["POST"])
@login_required
@staff_only
def request_return(assignment_id: int):
    assignment = ItemAssignment.query.filter_by(
        id=assignment_id, staff_id=current_user.id
    ).first_or_404()

    if assignment.status not in {"assigned", "return_requested"}:
        flash("This item cannot be returned right now.", "warning")
        return redirect(url_for("staff.dashboard"))

    if assignment.status == "return_requested":
        flash("Return already requested. Hang tight!", "info")
        return redirect(url_for("staff.dashboard"))

    assignment.status = "return_requested"
    db.session.commit()
    current_app.logger.info(
        "Return requested", extra={"assignment_id": assignment.id, "staff_id": current_user.id}
    )
    flash("Return request sent.", "info")
    return redirect(url_for("staff.dashboard"))


@staff_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated and getattr(current_user, "user_role", "") == "staff":
        return redirect(url_for("staff.dashboard"))

    form = StaffRegisterForm()
    if form.validate_on_submit():
        staff = StaffUser(
            full_name=form.full_name.data.strip(),
            department=form.department.data,
            email=form.email.data.lower(),
            password_hash=generate_password_hash(form.password.data),
        )
        db.session.add(staff)
        db.session.commit()
        login_user(staff)
        flash("Welcome to your workspace!", "success")
        return redirect(url_for("staff.dashboard"))

    return render_template("staff/register.html", form=form)


@staff_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated and getattr(current_user, "user_role", "") == "staff":
        return redirect(url_for("staff.dashboard"))

    form = StaffLoginForm()
    if form.validate_on_submit():
        staff = StaffUser.query.filter_by(email=form.email.data.lower()).first()
        if not staff or not check_password_hash(staff.password_hash, form.password.data):
            flash("Invalid credentials. Try again.", "danger")
        else:
            login_user(staff)
            flash("Signed in successfully.", "success")
            return redirect(url_for("staff.dashboard"))

    return render_template("staff/login.html", form=form)


@staff_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Signed out.", "info")
    return redirect(url_for("public.role_selection"))

