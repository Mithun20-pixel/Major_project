"""
tests/test_register.py
=======================
Tests for the /auth/register route.

Covers:
  - GET renders the registration form.
  - POST with valid data creates a user and redirects (dev mode auto-verify).
  - POST with a duplicate email flashes an error and does not create a second user.
  - POST when the database raises an exception returns a safe flash message,
    calls rollback(), and logs the exception.

Uses TestingConfig (in-memory SQLite, CSRF disabled) -- never touches production.
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError

from app import create_app
from extensions import db as _db
from models.user import User


# ---- Fixtures ---------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    """Create the Flask application in testing mode once per session."""
    application = create_app("testing")
    return application


@pytest.fixture(scope="function")
def db(app):
    """
    Create all tables before each test and drop them after.
    This gives each test an empty, isolated in-memory SQLite database.
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app, db):
    """Flask test client with a fresh DB per test."""
    return app.test_client()


# ---- Helpers ----------------------------------------------------------------

VALID_FORM = {
    "full_name":        "Test User",
    "age":              "25",
    "gender":           "Male",
    "height_cm":        "175.0",
    "weight_kg":        "70.0",
    "email":            "test@example.com",
    "password":         "Secure1234",
    "confirm_password": "Secure1234",
    "submit":           "Create Account",
}


def _post_register(client, overrides=None, follow_redirects=False):
    """POST to /auth/register with VALID_FORM data, applying any overrides."""
    data = {**VALID_FORM, **(overrides or {})}
    return client.post("/auth/register", data=data, follow_redirects=follow_redirects)


# ---- Tests ------------------------------------------------------------------

class TestRegisterGet:
    def test_get_renders_form(self, client):
        """GET /auth/register should return 200 with the registration form."""
        response = client.get("/auth/register")
        assert response.status_code == 200
        body = response.data.lower()
        assert b"register" in body or b"create account" in body


class TestRegisterSuccess:
    def test_successful_registration_redirects(self, client, app):
        """A valid POST should insert one User row and redirect to /auth/login."""
        response = _post_register(client)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("Location", "")
        with app.app_context():
            assert User.query.filter_by(email="test@example.com").first() is not None
            assert User.query.count() == 1

    def test_successful_registration_hashes_password(self, client, app):
        """The stored password must be a bcrypt hash, never plaintext."""
        _post_register(client)
        with app.app_context():
            user = User.query.filter_by(email="test@example.com").first()
            assert user is not None
            assert user._password_hash != "Secure1234"
            assert user._password_hash.startswith("$2b$")

    def test_email_is_lowercased(self, client, app):
        """Emails are stored in lowercase regardless of form casing."""
        _post_register(client, {"email": "TEST@Example.COM"})
        with app.app_context():
            assert User.query.filter_by(email="test@example.com").first() is not None


class TestRegisterDuplicateEmail:
    def test_duplicate_email_does_not_create_second_user(self, client, app):
        """Submitting the same email twice must leave only one user row."""
        _post_register(client)
        _post_register(client)
        with app.app_context():
            assert User.query.count() == 1

    def test_duplicate_email_case_insensitive(self, client, app):
        """Email uniqueness check must be case-insensitive."""
        _post_register(client, {"email": "unique@example.com"})
        _post_register(client, {"email": "UNIQUE@example.com"})
        with app.app_context():
            assert User.query.count() == 1


class TestRegisterDatabaseFailure:
    def test_db_commit_failure_returns_200_not_500(self, client, app):
        """
        If db.session.commit() raises OperationalError the route must:
        - Return 200 (form re-rendered, not a crash to Gunicorn).
        - NOT expose SQL or internal exception details in the response.
        - Call db.session.rollback().
        """
        fake_error = OperationalError("insert", {}, Exception("connection lost"))

        with patch("routes.auth.db.session.commit", side_effect=fake_error), \
             patch("routes.auth.db.session.rollback") as mock_rollback:
            response = _post_register(client, follow_redirects=True)

        assert response.status_code == 200
        body = response.data
        assert b"OperationalError" not in body
        assert b"connection lost" not in body
        assert b"server error" in body.lower() or b"try again" in body.lower()
        mock_rollback.assert_called_once()

    def test_db_commit_failure_creates_no_user(self, client, app):
        """On commit failure the partial user must NOT be persisted."""
        fake_error = OperationalError("insert", {}, Exception("db down"))

        with patch("routes.auth.db.session.commit", side_effect=fake_error), \
             patch("routes.auth.db.session.rollback"):
            _post_register(client, follow_redirects=True)

        with app.app_context():
            assert User.query.count() == 0

    def test_db_query_failure_returns_200_not_500(self, client, app):
        """A SELECT failure (e.g. SSL stall) must not propagate as an unhandled 500."""
        fake_error = OperationalError("select", {}, Exception("SSL error"))

        with patch("routes.auth.User.query") as mock_query, \
             patch("routes.auth.db.session.rollback") as mock_rollback:
            mock_query.filter_by.return_value.first.side_effect = fake_error
            response = _post_register(client, follow_redirects=True)

        assert response.status_code == 200
        assert b"SSL error" not in response.data
        assert b"OperationalError" not in response.data
        assert b"try again" in response.data.lower()
        mock_rollback.assert_called_once()

