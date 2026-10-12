"""
tests/test_email_verification.py
==================================
Focused security and reliability tests for email verification in HealthAI.

Covers:
    1. Successful email sending via send_verification_email / send_password_reset_email
    2. SMTP failures raise EmailDeliveryError (not swallowed silently)
    3. Registration in production mode — email failure NEVER auto-verifies account
    4. Registration in development mode — account auto-verified regardless
    5. Resend-verification flow — email failure leaves account unchanged
    6. User-facing flash messages never expose SMTP credentials / stack traces
"""

import os
import smtplib
import socket
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure env vars are set before any app-level import (ProductionConfig guard)
# ---------------------------------------------------------------------------
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-for-production")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-jwt-key-not-for-production")

from utils.email_utils import (
    EmailDeliveryError,
    _generate_token,
    _send_message,
    send_verification_email,
    send_password_reset_email,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _make_user(email="test@example.com", full_name="Test User", is_email_verified=False):
    """Return a lightweight mock that satisfies the email_utils interface."""
    user = MagicMock()
    user.email = email
    user.full_name = full_name
    user.is_email_verified = is_email_verified
    return user


SENSITIVE_STRINGS = [
    # Nothing from env or typical SMTP config should appear in raised exceptions
    "MAIL_PASSWORD",
    "MAIL_USERNAME",
    "smtp.gmail.com",
    "password",
    "secret",
    "credential",
]


# ===========================================================================
# 1. Unit tests for _send_message / email_utils
# ===========================================================================

class TestSendMessageSuccess:
    """_send_message does NOT raise when mail.send succeeds."""

    def test_success_does_not_raise(self, app):
        with app.app_context():
            mock_msg = MagicMock()
            with patch("utils.email_utils.mail") as mock_mail:
                mock_mail.send.return_value = None
                # Should complete without raising
                _send_message(mock_msg, context="test verification email")
                mock_mail.send.assert_called_once_with(mock_msg)


class TestSendMessageSmtpAuthError:
    """SMTPAuthenticationError is wrapped as EmailDeliveryError."""

    def test_smtp_auth_raises_delivery_error(self, app):
        with app.app_context():
            mock_msg = MagicMock()
            smtp_exc = smtplib.SMTPAuthenticationError(535, b"5.7.8 Bad credentials")
            with patch("utils.email_utils.mail") as mock_mail:
                mock_mail.send.side_effect = smtp_exc
                with pytest.raises(EmailDeliveryError) as exc_info:
                    _send_message(mock_msg, context="verification email to x@y.com")
            # The raised message must NOT expose credentials
            msg = str(exc_info.value)
            for secret in SENSITIVE_STRINGS:
                assert secret.lower() not in msg.lower(), (
                    f"Sensitive term {secret!r} found in EmailDeliveryError message"
                )

    def test_smtp_auth_original_cause_preserved(self, app):
        with app.app_context():
            mock_msg = MagicMock()
            smtp_exc = smtplib.SMTPAuthenticationError(535, b"Bad credentials")
            with patch("utils.email_utils.mail") as mock_mail:
                mock_mail.send.side_effect = smtp_exc
                with pytest.raises(EmailDeliveryError) as exc_info:
                    _send_message(mock_msg, context="ctx")
            assert exc_info.value.__cause__ is smtp_exc


class TestSendMessageSmtpGenericError:
    """Generic SMTPException is wrapped as EmailDeliveryError."""

    def test_smtp_exception_raises_delivery_error(self, app):
        with app.app_context():
            mock_msg = MagicMock()
            smtp_exc = smtplib.SMTPConnectError(421, b"Service unavailable")
            with patch("utils.email_utils.mail") as mock_mail:
                mock_mail.send.side_effect = smtp_exc
                with pytest.raises(EmailDeliveryError):
                    _send_message(mock_msg, context="ctx")


class TestSendMessageNetworkError:
    """Network-level errors are wrapped as EmailDeliveryError."""

    @pytest.mark.parametrize("network_exc", [
        socket.gaierror("Name resolution failed"),
        socket.timeout("Timed out"),
        ConnectionRefusedError("Connection refused"),
        OSError("Network unreachable"),
    ])
    def test_network_errors_raise_delivery_error(self, app, network_exc):
        with app.app_context():
            mock_msg = MagicMock()
            with patch("utils.email_utils.mail") as mock_mail:
                mock_mail.send.side_effect = network_exc
                with pytest.raises(EmailDeliveryError):
                    _send_message(mock_msg, context="ctx")


class TestSendMessageUnexpectedError:
    """Unexpected exceptions are wrapped as EmailDeliveryError."""

    def test_unexpected_error_raises_delivery_error(self, app):
        with app.app_context():
            mock_msg = MagicMock()
            with patch("utils.email_utils.mail") as mock_mail:
                mock_mail.send.side_effect = RuntimeError("totally unexpected")
                with pytest.raises(EmailDeliveryError):
                    _send_message(mock_msg, context="ctx")


class TestSendVerificationEmail:
    """send_verification_email propagates EmailDeliveryError on failure."""

    def test_success(self, app):
        with app.app_context():
            user = _make_user()
            with patch("utils.email_utils.mail") as mock_mail:
                mock_mail.send.return_value = None
                send_verification_email(user)   # must not raise
                assert mock_mail.send.called

    def test_smtp_failure_raises(self, app):
        with app.app_context():
            user = _make_user()
            with patch("utils.email_utils.mail") as mock_mail:
                mock_mail.send.side_effect = smtplib.SMTPException("relay denied")
                with pytest.raises(EmailDeliveryError):
                    send_verification_email(user)


class TestSendPasswordResetEmail:
    """send_password_reset_email propagates EmailDeliveryError on failure."""

    def test_success(self, app):
        with app.app_context():
            user = _make_user()
            with patch("utils.email_utils.mail") as mock_mail:
                mock_mail.send.return_value = None
                send_password_reset_email(user)  # must not raise
                assert mock_mail.send.called

    def test_smtp_failure_raises(self, app):
        with app.app_context():
            user = _make_user()
            with patch("utils.email_utils.mail") as mock_mail:
                mock_mail.send.side_effect = smtplib.SMTPException("relay denied")
                with pytest.raises(EmailDeliveryError):
                    send_password_reset_email(user)


# ===========================================================================
# 2. Integration tests via the auth blueprint (test client)
# ===========================================================================

REGISTER_PAYLOAD = dict(
    full_name="Jane Doe",
    age="28",
    gender="Female",
    height_cm="165",
    weight_kg="60",
    email="jane@example.com",
    password="StrongPass1!",
    confirm_password="StrongPass1!",
)


class TestRegistrationProductionEmailFailure:
    """
    CRITICAL: In production mode, a failed verification email must NEVER
    result in the account being automatically verified.
    """

    def test_email_failure_does_not_auto_verify_account(self, app, db):
        """
        Post to /auth/register with FLASK_ENV=production and a broken SMTP
        server.  The user record must exist in the DB but is_email_verified
        must remain False.
        """
        from models.user import User

        payload = REGISTER_PAYLOAD.copy()
        payload["email"] = "prod_fail@example.com"

        with app.test_client() as client:
            with patch.dict(os.environ, {"FLASK_ENV": "production"}):
                with patch("routes.auth.send_verification_email") as mock_send:
                    mock_send.side_effect = EmailDeliveryError("SMTP auth failed")
                    resp = client.post(
                        "/auth/register",
                        data=payload,
                        follow_redirects=True,
                    )

        with app.app_context():
            user = User.query.filter_by(email="prod_fail@example.com").first()

        assert user is not None, "Account should have been created in DB"
        assert user.is_email_verified is False, (
            "SECURITY: is_email_verified must remain False when email sending fails "
            "in production — account must NOT be auto-verified."
        )
        # Cleanup
        with app.app_context():
            db.session.delete(User.query.filter_by(email="prod_fail@example.com").first())
            db.session.commit()

    def test_email_failure_flash_message_hides_smtp_details(self, app, db):
        """
        The user-facing flash on email failure must not expose SMTP credentials
        or server configuration details.

        Note: Generic words like 'password' legitimately appear in the register
        form HTML (e.g. <input type="password">).  We check for SMTP-specific
        compound strings that would only appear if credentials were leaked.
        """
        payload = REGISTER_PAYLOAD.copy()
        payload["email"] = "prod_flash@example.com"

        # These compound strings would only appear in the page if SMTP config
        # were accidentally surfaced — they won't appear in normal form HTML.
        smtp_specific = [
            "mail_password",
            "mail_username",
            "smtp.gmail.com",
            "smtp auth",
            "smtpauthenticationerror",
            "smtpexception",
            "mail_server",
            "emaildeliveryerror",
        ]

        with app.test_client() as client:
            with patch.dict(os.environ, {"FLASK_ENV": "production"}):
                with patch("routes.auth.send_verification_email") as mock_send:
                    mock_send.side_effect = EmailDeliveryError("SMTP auth failed")
                    resp = client.post(
                        "/auth/register",
                        data=payload,
                        follow_redirects=True,
                    )

        body = resp.data.decode("utf-8", errors="replace").lower()
        for term in smtp_specific:
            assert term.lower() not in body, (
                f"SMTP-specific term {term!r} leaked into HTTP response"
            )

        # Verify the friendly user-facing message IS shown
        assert "verification email" in body or "could not send" in body or "resend" in body, (
            "Expected a user-friendly email-delivery-failure message in the response"
        )

        # Cleanup
        with app.app_context():
            from models.user import User
            u = User.query.filter_by(email="prod_flash@example.com").first()
            if u:
                db.session.delete(u)
                db.session.commit()


    def test_email_success_account_unverified_until_link_clicked(self, app, db):
        """
        In production mode with a working SMTP, the account is created but
        is_email_verified stays False until the link is clicked.
        """
        from models.user import User

        payload = REGISTER_PAYLOAD.copy()
        payload["email"] = "prod_ok@example.com"

        with app.test_client() as client:
            with patch.dict(os.environ, {"FLASK_ENV": "production"}):
                with patch("routes.auth.send_verification_email") as mock_send:
                    mock_send.return_value = None   # email "sent" successfully
                    client.post("/auth/register", data=payload, follow_redirects=True)

        with app.app_context():
            user = User.query.filter_by(email="prod_ok@example.com").first()

        assert user is not None
        assert user.is_email_verified is False, (
            "Account should remain unverified until the user clicks the email link."
        )
        # Cleanup
        with app.app_context():
            db.session.delete(User.query.filter_by(email="prod_ok@example.com").first())
            db.session.commit()


class TestRegistrationDevelopmentMode:
    """Development mode should auto-verify so local workflows are unaffected."""

    def test_dev_mode_auto_verifies(self, app, db):
        from models.user import User

        payload = REGISTER_PAYLOAD.copy()
        payload["email"] = "dev_auto@example.com"

        with app.test_client() as client:
            with patch.dict(os.environ, {"FLASK_ENV": "development"}):
                client.post("/auth/register", data=payload, follow_redirects=True)

        with app.app_context():
            user = User.query.filter_by(email="dev_auto@example.com").first()

        assert user is not None
        assert user.is_email_verified is True, (
            "In development mode, account should be auto-verified for easy login."
        )
        # Cleanup
        with app.app_context():
            db.session.delete(User.query.filter_by(email="dev_auto@example.com").first())
            db.session.commit()


class TestResendVerificationEmailFailure:
    """Resend-verification: SMTP failure must leave the account unchanged."""

    def _create_unverified_user(self, app, db, email):
        from models.user import User
        with app.app_context():
            user = User(
                full_name="Resend Test",
                email=email,
                age=25,
                gender="Male",
                height_cm=170.0,
                weight_kg=70.0,
                is_email_verified=False,
            )
            user.password = "StrongPass1!"
            db.session.add(user)
            db.session.commit()

    def test_resend_failure_does_not_verify_account(self, app, db):
        from models.user import User

        email = "resend_fail@example.com"
        self._create_unverified_user(app, db, email)

        with app.test_client() as client:
            with patch("routes.auth.send_verification_email") as mock_send:
                mock_send.side_effect = EmailDeliveryError("network error")
                client.post(
                    "/auth/resend-verification",
                    data={"email": email},
                    follow_redirects=True,
                )

        with app.app_context():
            user = User.query.filter_by(email=email).first()

        assert user is not None
        assert user.is_email_verified is False, (
            "Resend failure must NOT set is_email_verified to True."
        )

        # Cleanup
        with app.app_context():
            u = User.query.filter_by(email=email).first()
            if u:
                db.session.delete(u)
                db.session.commit()

    def test_resend_shows_generic_message_regardless_of_outcome(self, app, db):
        """
        The resend endpoint always shows the same message to prevent
        account-enumeration attacks.
        """
        email = "resend_generic@example.com"
        self._create_unverified_user(app, db, email)

        with app.test_client() as client:
            with patch("routes.auth.send_verification_email") as mock_send:
                mock_send.side_effect = EmailDeliveryError("network error")
                resp = client.post(
                    "/auth/resend-verification",
                    data={"email": email},
                    follow_redirects=True,
                )

        body = resp.data.decode("utf-8", errors="replace")
        # The generic "if an unverified account exists" message should be present
        assert "unverified account" in body.lower() or "verification link" in body.lower(), (
            "Expected a generic verification message in the response body"
        )

        # Cleanup
        with app.app_context():
            from models.user import User
            u = User.query.filter_by(email=email).first()
            if u:
                db.session.delete(u)
                db.session.commit()
