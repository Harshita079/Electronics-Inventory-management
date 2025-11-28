from flask_wtf import FlaskForm
from wtforms import (
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import Email, EqualTo, Length, DataRequired, NumberRange

from ...models import StaffUser


def _strip_filter(value):
    return value.strip() if isinstance(value, str) else value


class StaffRegisterForm(FlaskForm):
    full_name = StringField(
        "Full name",
        validators=[DataRequired(), Length(min=3, max=120)],
    )
    department = SelectField(
        "Department",
        choices=[
            ("IT", "IT"),
            ("Operations", "Operations"),
            ("Finance", "Finance"),
            ("HR", "HR"),
            ("Other", "Other"),
        ],
        validators=[DataRequired()],
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
    submit = SubmitField("Join staff workspace")

    def validate_email(self, field):
        if StaffUser.query.filter_by(email=field.data.lower()).first():
            raise ValueError("This email is already registered as staff.")


class StaffLoginForm(FlaskForm):
    email = StringField(
        "Work email",
        validators=[DataRequired(), Email(), Length(max=120)],
    )
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Continue")


class StaffRequestItemForm(FlaskForm):
    item_name = StringField(
        "What do you need?",
        validators=[DataRequired(), Length(min=3, max=150)],
        filters=[_strip_filter],
    )
    justification = TextAreaField(
        "Tell admin why you need it",
        validators=[DataRequired(), Length(min=10, max=500)],
        filters=[_strip_filter],
    )
    submit = SubmitField("Submit request")


class FeedbackForm(FlaskForm):
    rating = IntegerField(
        "Overall experience",
        validators=[DataRequired(), NumberRange(min=1, max=5)],
        filters=[_strip_filter],
    )
    question_1 = TextAreaField(
        "Ease of assigning devices",
        validators=[Length(max=255)],
        filters=[_strip_filter],
    )
    question_2 = TextAreaField(
        "Clarity of stock information",
        validators=[Length(max=255)],
        filters=[_strip_filter],
    )
    question_3 = TextAreaField(
        "Request approval speed",
        validators=[Length(max=255)],
        filters=[_strip_filter],
    )
    question_4 = TextAreaField(
        "Return workflow experience",
        validators=[Length(max=255)],
        filters=[_strip_filter],
    )
    question_5 = TextAreaField(
        "Any other feedback?",
        validators=[Length(max=255)],
        filters=[_strip_filter],
    )
    submit = SubmitField("Submit feedback")

