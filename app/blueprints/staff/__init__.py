from flask import Blueprint

staff_bp = Blueprint("staff", __name__, url_prefix="/staff")

from . import routes  # noqa: E402,F401

__all__ = ["staff_bp"]

