"""
routes/auth.py - Authentication Blueprint
==========================================
Handles: Register, Login, Logout, Email Verification, Password Reset, Resend Verification.
All forms are CSRF-protected via Flask-WTF.
"""

import os
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from flask import (
    Blueprint, render_template, redirect,
    url_for, flash, request, current_app
)
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from extensions import db, mail
from models.user import User
from forms.auth import (
    RegistrationForm, LoginForm, ForgotPasswordForm,
    ResetPasswordForm, ResendVerificationForm
)
from utils.email_utils import send_verification_email, send_password_reset_email
from utils.rate_limiter import rate_limit

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


def is_safe_url(target: str) -> bool:
    """
    Ensure a redirect URL target is safe and points to the same host
    to prevent unsafe open redirects to external sites.
    """
    if not target or not target.startswith("/") or target.startswith("//"):
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


# ── Registration ───────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
@rate_limit(max_requests=10, window_seconds=60)
def register():
    """
    Handle new user registration.
    Sends an email verification link after successful registration.
    """
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()

        try:
            # Check for duplicate email
            if User.query.filter_by(email=email).first():
                flash("An account with this email address already exists.", "danger")
                return render_template("auth/register.html", form=form)

            # Create user (password is auto-hashed by the model setter)
            user = User(
                full_name = form.full_name.data.strip(),
                age       = form.age.data,
                gender    = form.gender.data,
                height_cm = form.height_cm.data,
                weight_kg = form.weight_kg.data,
                email     = email,
            )
            user.password = form.password.data   # triggers bcrypt hash
            db.session.add(user)
            db.session.commit()

        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "Registration DB error for email=%s", email
            )
            flash(
                "Registration could not be completed due to a server error. "
                "Please try again in a moment.",
                "danger",
            )
            return render_template("auth/register.html", form=form)

        # In development, auto-verify so users can log in without SMTP setup
        if os.environ.get('FLASK_ENV', 'development') == 'development':
            user.is_email_verified = True
            db.session.commit()
            flash("Account created successfully! You can now log in immediately (dev mode).", "success")
        else:
            try:
                send_verification_email(user)
                flash("Registration successful! Please check your email to verify your account.", "success")
            except Exception as exc:
                current_app.logger.error(f"Failed to send email verification: {exc}")
                user.is_email_verified = True
                db.session.commit()
                flash("Account created! Email delivery failed — logged in directly for demo.", "warning")

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
        flash("Email is already verified. Please log in.", "info")
    else:
        user.is_email_verified = True
        db.session.commit()
        flash("Email verified successfully! You can now log in.", "success")

    return redirect(url_for("auth.login"))


@auth_bp.route("/resend-verification", methods=["GET", "POST"])
@rate_limit(max_requests=5, window_seconds=60)
def resend_verification():
    """
    Safely resend email verification link without revealing if an account exists.
    """
    form = ResendVerificationForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()
        if user and not user.is_email_verified:
            try:
                send_verification_email(user)
            except Exception as exc:
                current_app.logger.error(f"Error resending verification: {exc}")
        flash("If an unverified account exists with that email, a new verification link has been sent.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/resend_verification.html", form=form)


# ── Login ──────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
@rate_limit(max_requests=10, window_seconds=60)
def login():
    """
    Authenticate user with email + password.
    Enforces email verification before allowing access.
    Validates redirect targets to prevent open redirects.
    """
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()

        if not user or not user.verify_password(form.password.data):
            flash("Invalid email address or password.", "danger")
            return render_template("auth/login.html", form=form)

        if not user.is_active or user.is_deleted:
            flash("Your account has been disabled. Please contact support.", "danger")
            return render_template("auth/login.html", form=form)

        if not user.is_email_verified:
            flash("Please verify your email address before logging in.", "warning")
            return render_template("auth/login.html", form=form)

        login_user(user, remember=form.remember_me.data)
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Log activity
        from utils.activity_tracker import log_user_activity
        log_user_activity(user, "User Login", f"Logged in from {request.remote_addr}")

        # Redirect safely (open redirect prevention)
        next_page = request.args.get("next")
        if not next_page or not is_safe_url(next_page):
            next_page = url_for("main.dashboard")

        flash(f"Welcome back, {user.full_name}!", "success")
        return redirect(next_page)

    return render_template("auth/login.html", form=form)


# ── Logout ─────────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    """End the user's session and redirect to login."""
    from utils.activity_tracker import log_user_activity
    log_user_activity(current_user, "Logged Out", "User signed out")

    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


# ── Forgot password ────────────────────────────────────────────────────────

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@rate_limit(max_requests=5, window_seconds=60)
def forgot_password():
    """
    Send a password-reset link to the provided email address.
    Always shows a generic success message to prevent user enumeration attacks.
    Enforces single-use reset links by persisting reset_token on the user model.
    """
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()
        if user:
            s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
            token = s.dumps(user.email, salt="password-reset")

            # Persist token on user model for single-use enforcement
            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(seconds=current_app.config["PASSWORD_RESET_EXPIRY"])
            db.session.commit()

            try:
                send_password_reset_email(user, token=token)
            except Exception as exc:
                current_app.logger.error(f"Error sending password reset email: {exc}")

        flash(
            "If that email address is registered, you will receive a password reset link shortly.",
            "info"
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", form=form)


# ── Reset password ─────────────────────────────────────────────────────────

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@rate_limit(max_requests=5, window_seconds=60)
def reset_password(token: str):
    """
    Allow the user to set a new password using a timed signed token.
    Enforces single-use verification against user.reset_token.
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

    # Enforce single-use token check
    if user.reset_token and user.reset_token != token:
        flash("This password reset link has already been used or invalidated.", "danger")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        user.password = form.password.data
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        flash("Password updated successfully! Please log in with your new password.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form)

