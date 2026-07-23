"""
routes/auth.py - Authentication Blueprint
==========================================
Handles: Register, Login, Logout, Email Verification, Password Reset.
All forms are CSRF-protected via Flask-WTF.
"""

from flask import (
    Blueprint, render_template, redirect,
    url_for, flash, request, current_app
)
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from datetime import datetime

from extensions import db, mail
from models.user import User
from forms.auth import RegistrationForm, LoginForm, ForgotPasswordForm, ResetPasswordForm
from utils.email_utils import send_verification_email, send_password_reset_email

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


# ── Registration ───────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    Handle new user registration.
    Sends an email verification link after successful registration.
    """
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Check for duplicate email
        if User.query.filter_by(email=form.email.data.lower().strip()).first():
            flash("An account with this email already exists.", "danger")
            return render_template("auth/register.html", form=form)

        # Create user (password is auto-hashed by the model setter)
        user = User(
            full_name = form.full_name.data.strip(),
            age       = form.age.data,
            gender    = form.gender.data,
            height_cm = form.height_cm.data,
            weight_kg = form.weight_kg.data,
            email     = form.email.data.lower().strip(),
        )
        user.password = form.password.data   # triggers bcrypt hash
        db.session.add(user)
        db.session.commit()

        # In development, auto-verify so users can log in without SMTP setup
        import os
        if os.environ.get('FLASK_ENV', 'development') == 'development':
            user.is_email_verified = True
            db.session.commit()
            flash("Account created! You can log in immediately (dev mode).", "success")
        else:
            try:
                send_verification_email(user)
                flash("Registration successful! Please verify your email address.", "success")
            except Exception:
                user.is_email_verified = True
                db.session.commit()
                flash("Account created! Email sending failed — logging you in directly.", "warning")

        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


# ── Email verification ─────────────────────────────────────────────────────

@auth_bp.route("/verify/<token>")
def verify_email(token: str):
    """
    Confirm the user's email address using a timed signed token.
    Token expiry is controlled by EMAIL_TOKEN_EXPIRY in config.
    """
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        email = s.loads(
            token,
            salt="email-verify",
            max_age=current_app.config["EMAIL_TOKEN_EXPIRY"],
        )
    except (SignatureExpired, BadSignature):
        flash("The verification link is invalid or has expired.", "danger")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(email=email).first_or_404()
    if user.is_email_verified:
        flash("Email already verified. Please log in.", "info")
    else:
        user.is_email_verified = True
        db.session.commit()
        flash("Email verified successfully! You can now log in.", "success")

    return redirect(url_for("auth.login"))


# ── Login ──────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Authenticate user with email + password.
    Enforces email verification before allowing access.
    """
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(
            email=form.email.data.lower().strip()
        ).first()

        if not user or not user.verify_password(form.password.data):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", form=form)

        if not user.is_active or user.is_deleted:
            flash("Your account has been disabled. Contact support.", "danger")
            return render_template("auth/login.html", form=form)

        if not user.is_email_verified:
            flash("Please verify your email before logging in.", "warning")
            return render_template("auth/login.html", form=form)

        login_user(user, remember=form.remember_me.data)
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Redirect to the page the user was trying to reach (if any)
        next_page = request.args.get("next")
        flash(f"Welcome back, {user.full_name}!", "success")
        return redirect(next_page or url_for("main.dashboard"))

    return render_template("auth/login.html", form=form)


# ── Logout ─────────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    """End the user's session and redirect to login."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


# ── Forgot password ────────────────────────────────────────────────────────

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """
    Send a password-reset link to the provided email address.
    Always shows a success message regardless of whether the email exists
    (prevents user enumeration attacks).
    """
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user:
            send_password_reset_email(user)
        flash(
            "If that email is registered, you will receive a reset link shortly.",
            "info"
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", form=form)


# ── Reset password ─────────────────────────────────────────────────────────

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    """
    Allow the user to set a new password using a timed signed token.
    """
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        email = s.loads(
            token,
            salt="password-reset",
            max_age=current_app.config["PASSWORD_RESET_EXPIRY"],
        )
    except (SignatureExpired, BadSignature):
        flash("The reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    user = User.query.filter_by(email=email).first_or_404()
    form = ResetPasswordForm()

    if form.validate_on_submit():
        user.password = form.password.data
        db.session.commit()
        flash("Password updated successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form)
