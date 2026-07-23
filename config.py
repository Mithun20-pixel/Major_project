"""
config.py - Application Configuration Module
=============================================
Defines configuration classes for different environments:
- DevelopmentConfig: Local development with SQLite (zero-setup)
- TestingConfig: Isolated testing environment (in-memory SQLite)
- ProductionConfig: Hardened production settings (MySQL)

All secrets are read from environment variables for security.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class BaseConfig:
    """Base configuration shared across all environments."""

    # ── Flask ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production-secret-key-123!")
    DEBUG = False
    TESTING = False

    # ── Database ───────────────────────────────────────────────────────
    DB_USER     = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "root")
    DB_HOST     = os.environ.get("DB_HOST", "localhost")
    DB_PORT     = os.environ.get("DB_PORT", "3306")
    DB_NAME     = os.environ.get("DB_NAME", "explainable_ai_health")

    # Default: SQLite (overridden per environment below)
    SQLALCHEMY_DATABASE_URI = (
        f"sqlite:///{os.path.join(os.getcwd(), 'database', 'healthai.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # ── Session ────────────────────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # ── CSRF ───────────────────────────────────────────────────────────────
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour

    # ── Mail ───────────────────────────────────────────────────────────────
    MAIL_SERVER   = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT     = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS  = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@healthai.com")

    # ── File Uploads ───────────────────────────────────────────────────────
    UPLOAD_FOLDER   = os.path.join(os.getcwd(), "uploads")
    DATASET_FOLDER  = os.path.join(os.getcwd(), "datasets")
    REPORTS_FOLDER  = os.path.join(os.getcwd(), "reports")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024   # 16 MB max upload
    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}

    # ── ML Models ──────────────────────────────────────────────────────────
    MODELS_FOLDER = os.path.join(os.getcwd(), "ml", "saved_models")

    # ── Pagination ─────────────────────────────────────────────────────────
    PREDICTIONS_PER_PAGE = 10
    USERS_PER_PAGE       = 20

    # ── Token Expiry (Email verification / Password reset) ─────────────────
    EMAIL_TOKEN_EXPIRY         = 3600       # 1 hour
    PASSWORD_RESET_EXPIRY      = 1800       # 30 minutes

    # ── Bcrypt ─────────────────────────────────────────────────────────────
    BCRYPT_LOG_ROUNDS = 12


class DevelopmentConfig(BaseConfig):
    """Development configuration using SQLite — no database install required."""

    DEBUG = True
    SQLALCHEMY_ECHO = False        # set True to log SQL queries
    SESSION_COOKIE_SECURE = False  # allow HTTP in dev
    # SQLite file lives in database/ folder
    SQLALCHEMY_DATABASE_URI = (
        f"sqlite:///{os.path.join(os.getcwd(), 'database', 'healthai.db')}"
    )


class TestingConfig(BaseConfig):
    """Testing configuration using an in-memory SQLite database."""

    TESTING = True
    WTF_CSRF_ENABLED = False       # disable CSRF for test client
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    BCRYPT_LOG_ROUNDS = 4          # speed up tests


class ProductionConfig(BaseConfig):
    """Production configuration with MySQL and security hardened."""

    SESSION_COOKIE_SECURE = True   # HTTPS only
    SESSION_COOKIE_HTTPONLY = True
    PREFERRED_URL_SCHEME = "https"
    # Production uses MySQL
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{BaseConfig.DB_USER}:{BaseConfig.DB_PASSWORD}"
        f"@{BaseConfig.DB_HOST}:{BaseConfig.DB_PORT}/{BaseConfig.DB_NAME}"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    }


# ── Config registry ────────────────────────────────────────────────────────
config_map = {
    "development": DevelopmentConfig,
    "testing":     TestingConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}


def get_config(env: str = None) -> BaseConfig:
    """
    Return the configuration class for the given environment name.

    Args:
        env: One of 'development', 'testing', 'production'.
             Falls back to FLASK_ENV env-var, then 'default'.

    Returns:
        Configuration class (not an instance).
    """
    env = env or os.environ.get("FLASK_ENV", "default")
    return config_map.get(env, DevelopmentConfig)
