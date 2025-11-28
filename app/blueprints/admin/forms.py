from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DecimalField,
    HiddenField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
)

from ...models import AdminUser


class AdminRegisterForm(FlaskForm):
    full_name = StringField(
        "Full name",
        validators=[DataRequired(), Length(min=3, max=120)],
    )
    email = StringField(
        "Work email",
        validators=[DataRequired(), Email(), Length(max=120)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8)],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match"),
        ],
    )
    submit = SubmitField("Create admin account")

    def validate_email(self, field):
        if AdminUser.query.filter_by(email=field.data.lower()).first():
            raise ValueError("This email is already registered as admin.")


class AdminLoginForm(FlaskForm):
    email = StringField(
        "Work email",
        validators=[DataRequired(), Email(), Length(max=120)],
    )
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Continue to dashboard")


class InventoryForm(FlaskForm):
    name = StringField(
        "Item name",
        validators=[DataRequired(), Length(min=2, max=150)],
    )
    category = StringField(
        "Category",
        validators=[DataRequired(), Length(min=2, max=120)],
    )
    quantity = IntegerField(
        "Quantity",
        validators=[DataRequired(), NumberRange(min=0)],
    )
    purchase_date = DateField(
        "Purchase date",
        format="%Y-%m-%d",
        validators=[Optional()],
    )
    price = DecimalField(
        "Unit price",
        places=2,
        rounding=None,
        validators=[DataRequired(), NumberRange(min=0)],
    )
    submit = SubmitField("Save item")


class DeleteItemForm(FlaskForm):
    submit = SubmitField("Delete")


class ApproveRequestForm(FlaskForm):
    request_id = HiddenField(validators=[DataRequired()])
    item_id = SelectField(
        "Assign inventory",
        coerce=int,
        validators=[DataRequired()],
    )
    submit = SubmitField("Approve & assign")


class RejectRequestForm(FlaskForm):
    request_id = HiddenField(validators=[DataRequired()])
    submit = SubmitField("Reject request")


class ManualAssignmentForm(FlaskForm):
    staff_id = SelectField(
        "Select staff",
        coerce=int,
        validators=[DataRequired()],
    )
    item_id = SelectField(
        "Inventory item",
        coerce=int,
        validators=[DataRequired()],
    )
    submit = SubmitField("Assign item")


class CompleteReturnForm(FlaskForm):
    assignment_id = HiddenField(validators=[DataRequired()])
    submit = SubmitField("Confirm return")

