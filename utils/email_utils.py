"""
utils/email_utils.py - Email Sending Utilities
===============================================
Handles sending verification emails and password-reset emails
using Flask-Mail with itsdangerous signed tokens.
"""

from flask import current_app, url_for
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer

from extensions import mail


def _generate_token(email: str, salt: str) -> str:
    """
    Generate a URL-safe signed token for the given email.

    Args:
        email: User's email address to encode.
        salt:  Namespace salt to prevent token reuse across different actions.

    Returns:
        A signed, URL-safe token string.
    """
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.dumps(email, salt=salt)


def send_verification_email(user) -> None:
    """
    Send an account email-verification message.

    Args:
        user: User ORM instance with .email and .full_name attributes.
    """
    token = _generate_token(user.email, salt="email-verify")
    verify_url = url_for("auth.verify_email", token=token, _external=True)

    msg = Message(
        subject="Verify Your HealthAI Account",
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
        recipients=[user.email],
        html=_render_verification_email(user.full_name, verify_url),
    )
    try:
        mail.send(msg)
    except Exception as exc:
        current_app.logger.error(
            f"Failed to send verification email to {user.email}: {exc}"
        )


def send_password_reset_email(user, token: str = None) -> None:
    """
    Send a password-reset link email.

    Args:
        user: User ORM instance with .email and .full_name attributes.
        token: Optional existing token string. Generated if not supplied.
    """
    if not token:
        token = _generate_token(user.email, salt="password-reset")
    reset_url = url_for("auth.reset_password", token=token, _external=True)

    msg = Message(
        subject="Reset Your HealthAI Password",
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
        recipients=[user.email],
        html=_render_reset_email(user.full_name, reset_url),
    )
    try:
        mail.send(msg)
    except Exception as exc:
        current_app.logger.error(
            f"Failed to send reset email to {user.email}: {exc}"
        )



# ── Email HTML templates ────────────────────────────────────────────────────

def _render_verification_email(name: str, url: str) -> str:
    """Return HTML body for the email verification message."""
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;
                background:#0f172a;color:#e2e8f0;border-radius:12px;padding:32px;">
      <h1 style="color:#6ee7b7;">🩺 HealthAI</h1>
      <h2>Verify Your Email Address</h2>
      <p>Hi <strong>{name}</strong>,</p>
      <p>Thank you for registering. Click the button below to verify your account.</p>
      <a href="{url}"
         style="display:inline-block;padding:12px 24px;background:#10b981;
                color:#fff;border-radius:8px;text-decoration:none;font-weight:bold;margin:16px 0;">
        Verify My Email
      </a>
      <p style="font-size:12px;color:#94a3b8;">
        This link expires in 1 hour. If you did not register, ignore this email.
      </p>
    </div>
    """


def _render_reset_email(name: str, url: str) -> str:
    """Return HTML body for the password-reset message."""
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;
                background:#0f172a;color:#e2e8f0;border-radius:12px;padding:32px;">
      <h1 style="color:#6ee7b7;">🩺 HealthAI</h1>
      <h2>Password Reset Request</h2>
      <p>Hi <strong>{name}</strong>,</p>
      <p>We received a request to reset your password. Click below to proceed.</p>
      <a href="{url}"
         style="display:inline-block;padding:12px 24px;background:#f59e0b;
                color:#fff;border-radius:8px;text-decoration:none;font-weight:bold;margin:16px 0;">
        Reset My Password
      </a>
      <p style="font-size:12px;color:#94a3b8;">
        This link expires in 30 minutes. If you did not request a reset, ignore this email.
      </p>
    </div>
    """
