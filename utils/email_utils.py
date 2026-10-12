"""
utils/email_utils.py - Email Sending Utilities
===============================================
Handles sending verification emails and password-reset emails
using Flask-Mail with itsdangerous signed tokens.

Security notes
--------------
* SMTP exceptions are logged with diagnostic info (exception type + sanitised
  message) and then **re-raised** so callers can decide how to respond.
* SMTP passwords, app-passwords, and other secrets are NEVER written to logs.
"""

import smtplib
import socket

from flask import current_app, url_for
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer

from extensions import mail


class EmailDeliveryError(RuntimeError):
    """Raised when an outbound email cannot be delivered.

    Wraps the underlying transport exception so callers get a single,
    predictable error type without needing to know the SMTP internals.
    The original cause is available via ``__cause__``.
    """


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

    Raises:
        EmailDeliveryError: If the message cannot be sent (SMTP error,
            connection failure, etc.).  Credentials are never included in
            the exception message or the log line.
    """
    token = _generate_token(user.email, salt="email-verify")
    verify_url = url_for("auth.verify_email", token=token, _external=True)

    msg = Message(
        subject="Verify Your HealthAI Account",
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
        recipients=[user.email],
        html=_render_verification_email(user.full_name, verify_url),
    )
    _send_message(msg, context=f"verification email to {user.email}")


def send_password_reset_email(user, token: str = None) -> None:
    """
    Send a password-reset link email.

    Args:
        user: User ORM instance with .email and .full_name attributes.
        token: Optional existing token string. Generated if not supplied.

    Raises:
        EmailDeliveryError: If the message cannot be sent.
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
    _send_message(msg, context=f"password-reset email to {user.email}")


# ── Internal helpers ────────────────────────────────────────────────────────

def _send_message(msg: Message, *, context: str) -> None:
    """
    Attempt to send *msg* via Flask-Mail.

    Catches SMTP / socket / generic transport errors, logs a diagnostic
    line that contains ONLY the exception type and a sanitised description
    (never SMTP credentials or stack traces), then re-raises as
    :class:`EmailDeliveryError`.

    Args:
        msg:     The Flask-Mail ``Message`` to send.
        context: A human-readable description used in the log line
                 (e.g. "verification email to user@example.com").

    Raises:
        EmailDeliveryError: Always raised when sending fails.
    """
    try:
        mail.send(msg)
    except smtplib.SMTPAuthenticationError as exc:
        # Authentication failure — log type only; never log credentials.
        current_app.logger.error(
            "Email delivery failed (%s) — SMTP authentication error while sending %s. "
            "Check MAIL_USERNAME / MAIL_PASSWORD configuration.",
            type(exc).__name__,
            context,
        )
        raise EmailDeliveryError(
            "SMTP authentication failed. Contact the site administrator."
        ) from exc
    except smtplib.SMTPException as exc:
        # Other SMTP-layer errors (bad recipients, relay denied, etc.)
        # smtp_code / smtp_error are safe to log; they contain no secrets.
        current_app.logger.error(
            "Email delivery failed (%s) while sending %s. "
            "SMTP code: %s — reason: %s",
            type(exc).__name__,
            context,
            getattr(exc, "smtp_code", "N/A"),
            getattr(exc, "smtp_error", str(exc)),
        )
        raise EmailDeliveryError(
            "SMTP error occurred during email delivery."
        ) from exc
    except (socket.gaierror, socket.timeout, ConnectionError, OSError) as exc:
        # Network-level problems (DNS failure, timeout, refused connection)
        current_app.logger.error(
            "Email delivery failed (%s) — network/connection error while sending %s.",
            type(exc).__name__,
            context,
        )
        raise EmailDeliveryError(
            "Network error prevented email delivery."
        ) from exc
    except Exception as exc:  # noqa: BLE001
        # Catch-all for unexpected failures; log type only to avoid
        # accidentally surfacing sensitive config values from repr().
        current_app.logger.error(
            "Email delivery failed unexpectedly (%s) while sending %s.",
            type(exc).__name__,
            context,
        )
        raise EmailDeliveryError(
            "Unexpected error during email delivery."
        ) from exc


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
