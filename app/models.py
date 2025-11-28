from datetime import datetime

from flask_login import UserMixin

from .extensions import db, login_manager


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AdminUser(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "admin_users"
    user_role = "admin"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def get_id(self):
        return f"admin:{self.id}"

    def __repr__(self) -> str:
        return f"<AdminUser {self.email}>"


class StaffUser(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "staff_users"
    user_role = "staff"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    assignments = db.relationship("ItemAssignment", back_populates="staff_user")
    requests = db.relationship("ItemRequest", back_populates="staff_user")

    def get_id(self):
        return f"staff:{self.id}"

    def __repr__(self) -> str:
        return f"<StaffUser {self.email}>"


class InventoryItem(TimestampMixin, db.Model):
    __tablename__ = "inventory_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(120), nullable=False)
    quantity_available = db.Column(db.Integer, nullable=False, default=0)
    purchase_date = db.Column(db.Date)
    price = db.Column(db.Numeric(10, 2))

    assignments = db.relationship("ItemAssignment", back_populates="item")

    def __repr__(self) -> str:
        return f"<InventoryItem {self.name}>"


class ItemAssignment(TimestampMixin, db.Model):
    __tablename__ = "item_assignments"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory_items.id"), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey("staff_users.id"), nullable=False)
    allocation_date = db.Column(db.Date, default=datetime.utcnow)
    return_date = db.Column(db.Date)
    status = db.Column(db.String(50), default="assigned")

    item = db.relationship("InventoryItem", back_populates="assignments")
    staff_user = db.relationship("StaffUser", back_populates="assignments")


class ItemRequest(TimestampMixin, db.Model):
    __tablename__ = "item_requests"

    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey("staff_users.id"), nullable=False)
    item_name = db.Column(db.String(150), nullable=False)
    justification = db.Column(db.Text)
    status = db.Column(db.String(50), default="pending")

    staff_user = db.relationship("StaffUser", back_populates="requests")


class Feedback(TimestampMixin, db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey("staff_users.id"))
    rating = db.Column(db.Integer, nullable=False)
    question_1 = db.Column(db.String(255))
    question_2 = db.Column(db.String(255))
    question_3 = db.Column(db.String(255))
    question_4 = db.Column(db.String(255))
    question_5 = db.Column(db.String(255))

    staff_user = db.relationship("StaffUser")


@login_manager.user_loader
def load_user(user_id: str):
    if not user_id or ":" not in user_id:
        return None
    role, raw_id = user_id.split(":", 1)
    if not raw_id.isdigit():
        return None
    model_map = {
        "admin": AdminUser,
        "staff": StaffUser,
    }
    model = model_map.get(role)
    if not model:
        return None
    return model.query.get(int(raw_id))
