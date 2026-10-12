"""
tests/conftest.py
=================
Shared pytest fixtures for the HealthAI test suite.

The SECRET_KEY / JWT_SECRET_KEY env-vars must be set *before* config.py is
imported (ProductionConfig raises at class-evaluation time if they are absent).
"""

import os

# Set before any app code is imported so ProductionConfig class body doesn't raise.
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-for-production")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-jwt-key-not-for-production")

import pytest
from app import create_app
from extensions import db as _db


@pytest.fixture(scope="session")
def app():
    """Create a testing Flask application (in-memory SQLite, CSRF off)."""
    application = create_app("testing")
    application.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        MAIL_SUPPRESS_SEND=True,   # Flask-Mail: suppress actual sends in tests
        SERVER_NAME="localhost",   # required for url_for(_external=True)
    )
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    """Return a test client for the given app."""
    return app.test_client()


@pytest.fixture()
def db(app):
    """Yield the database, rolling back after each test."""
    with app.app_context():
        yield _db
        _db.session.rollback()
