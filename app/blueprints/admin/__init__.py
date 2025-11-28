from flask import Blueprint

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Import routes so they register with the blueprint when package is imported.
from . import routes  # noqa: E402,F401

__all__ = ["admin_bp"]