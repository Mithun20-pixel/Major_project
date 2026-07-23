"""
forms/profile.py - Profile Update Form
"""

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class ProfileUpdateForm(FlaskForm):
    """Form for updating user profile information."""

    full_name = StringField(
        "Full Name",
        validators=[DataRequired(), Length(min=2, max=120)]
    )
    age = IntegerField(
        "Age",
        validators=[DataRequired(), NumberRange(min=1, max=120)]
    )
    gender = SelectField(
        "Gender",
        choices=[("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
        validators=[DataRequired()]
    )
    height_cm = FloatField(
        "Height (cm)",
        validators=[Optional(), NumberRange(min=50, max=300)]
    )
    weight_kg = FloatField(
        "Weight (kg)",
        validators=[Optional(), NumberRange(min=1, max=500)]
    )
    submit = SubmitField("Update Profile")


# forms/__init__.py
