"""
forms/auth.py - Authentication WTForms
========================================
All forms are CSRF-protected by Flask-WTF (enabled globally in config).
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField,
    IntegerField, FloatField, SelectField, SubmitField
)
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo,
    NumberRange, Optional, Regexp
)


class RegistrationForm(FlaskForm):
    """User registration form with mandatory and optional health metrics."""

    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Full name is required."),
            Length(min=2, max=120, message="Name must be between 2 and 120 characters."),
        ]
    )
    age = IntegerField(
        "Age",
        validators=[
            DataRequired(message="Age is required."),
            NumberRange(min=1, max=120, message="Please enter a valid age between 1 and 120."),
        ]
    )
    gender = SelectField(
        "Gender",
        choices=[("", "Select Gender"), ("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
        validators=[DataRequired(message="Please select a gender.")]
    )
    height_cm = FloatField(
        "Height (cm)",
        validators=[
            Optional(),
            NumberRange(min=50, max=300, message="Height must be between 50 and 300 cm."),
        ]
    )
    weight_kg = FloatField(
        "Weight (kg)",
        validators=[
            Optional(),
            NumberRange(min=1, max=500, message="Weight must be between 1 and 500 kg."),
        ]
    )
    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Email address is required."),
            Email(message="Please enter a valid email address."),
            Length(max=180, message="Email must not exceed 180 characters."),
        ]
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required."),
            Length(min=8, max=128, message="Password must be at least 8 characters long."),
            Regexp(
                r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)",
                message="Password must contain at least 1 uppercase letter, 1 lowercase letter, and 1 digit.",
            ),
        ]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo("password", message="Password confirmation does not match password."),
        ]
    )
    submit = SubmitField("Create Account")


class LoginForm(FlaskForm):
    """User login form."""

    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Email address is required."),
            Email(message="Please enter a valid email address."),
        ]
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required.")]
    )
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class ForgotPasswordForm(FlaskForm):
    """Forgot password – request a reset link."""

    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Email address is required."),
            Email(message="Please enter a valid email address."),
        ]
    )
    submit = SubmitField("Send Reset Link")


class ResetPasswordForm(FlaskForm):
    """Reset password using the emailed token."""

    password = PasswordField(
        "New Password",
        validators=[
            DataRequired(message="New password is required."),
            Length(min=8, max=128, message="Password must be at least 8 characters long."),
            Regexp(
                r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)",
                message="Password must contain at least 1 uppercase letter, 1 lowercase letter, and 1 digit.",
            ),
        ]
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(message="Please confirm your new password."),
            EqualTo("password", message="Password confirmation does not match password."),
        ]
    )
    submit = SubmitField("Update Password")


class ResendVerificationForm(FlaskForm):
    """Resend email verification link."""

    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Email address is required."),
            Email(message="Please enter a valid email address."),
        ]
    )
    submit = SubmitField("Resend Verification Link")

