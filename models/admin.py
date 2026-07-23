"""
models/admin.py - Admin User ORM Model
========================================
Separate admin-specific table for elevated privileges.
Admin accounts are seeded via CLI, not through public registration.
"""

from datetime import datetime
from flask_login import UserMixin
from extensions import db, bcrypt


class Admin(UserMixin, db.Model):
    """
    Admin user with full system access.
    Kept separate from the User table for clean role separation.
    """

    __tablename__ = "admins"

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name  = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(180), unique=True, nullable=False, index=True)
    _password_hash = db.Column("password_hash", db.String(255), nullable=False)

    is_active  = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    # ── Password helpers ───────────────────────────────────────────────────

    @property
    def password(self):
        raise AttributeError("password is write-only.")

    @password.setter
    def password(self, plain_text: str) -> None:
        self._password_hash = bcrypt.generate_password_hash(plain_text).decode("utf-8")

    def verify_password(self, plain_text: str) -> bool:
        return bcrypt.check_password_hash(self._password_hash, plain_text)

    # ── Flask-Login ────────────────────────────────────────────────────────

    def get_id(self) -> str:
        return f"admin-{self.id}"

    @property
    def is_admin(self) -> bool:
        return True

    @property
    def role(self) -> str:
        return "admin"

    def __repr__(self) -> str:
        return f"<Admin id={self.id} email={self.email!r}>"


# ── models/__init__.py convenience re-exports ─────────────────────────────
