from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def landing():
    return render_template("landing.html")


@public_bp.route("/roles")
def role_selection():
    return render_template("role_select.html")


@public_bp.route("/start")
def enter_workspace():
    if current_user.is_authenticated:
        role = getattr(current_user, "user_role", "")
        if role == "admin":
            return redirect(url_for("admin.dashboard"))
        if role == "staff":
            return redirect(url_for("staff.dashboard"))
    return redirect(url_for("public.role_selection"))

