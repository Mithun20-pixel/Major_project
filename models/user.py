"""
models/user.py - User ORM Model
================================
Represents an application user.
Implements Flask-Login UserMixin for session management.
"""

from datetime import datetime
from flask_login import UserMixin
from extensions import db, bcrypt


class User(UserMixin, db.Model):
    """
    Core user table.

    Relationships:
        questionnaires  → Questionnaire (one-to-many)
        predictions     → Prediction    (one-to-many)
        reports         → Report        (one-to-many)
        recommendations → Recommendation (one-to-many, via Prediction)
    """

    __tablename__ = "users"

    # ── Primary key ────────────────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ── Personal information ───────────────────────────────────────────────
    full_name  = db.Column(db.String(120), nullable=False)
    age        = db.Column(db.Integer,     nullable=False)
    gender     = db.Column(db.String(20),  nullable=False)       # Male / Female / Other
    height_cm  = db.Column(db.Float,       nullable=True)
    weight_kg  = db.Column(db.Float,       nullable=True)

    # ── Account credentials ────────────────────────────────────────────────
    email             = db.Column(db.String(180), unique=True, nullable=False, index=True)
    _password_hash    = db.Column("password_hash", db.String(255), nullable=False)
    is_email_verified = db.Column(db.Boolean, default=False, nullable=False)

    # ── Role ───────────────────────────────────────────────────────────────
    role = db.Column(db.String(20), default="user", nullable=False)
    # Possible values: 'user', 'admin'

    # ── Account status ─────────────────────────────────────────────────────
    is_active   = db.Column(db.Boolean, default=True,  nullable=False)
    is_deleted  = db.Column(db.Boolean, default=False, nullable=False)  # soft-delete

    # ── Profile photo ──────────────────────────────────────────────────────
    profile_photo = db.Column(db.String(255), nullable=True)

    # ── Timestamps ─────────────────────────────────────────────────────────
    created_at   = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow,
                              onupdate=datetime.utcnow, nullable=False)
    last_login   = db.Column(db.DateTime, nullable=True)

    # ── Token fields (email verification / password reset) ─────────────────
    verification_token    = db.Column(db.String(255), nullable=True)
    reset_token           = db.Column(db.String(255), nullable=True)
    reset_token_expiry    = db.Column(db.DateTime,    nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────
    questionnaires  = db.relationship(
        "Questionnaire", back_populates="user",
        lazy="dynamic", cascade="all, delete-orphan"
    )
    predictions = db.relationship(
        "Prediction", back_populates="user",
        lazy="dynamic", cascade="all, delete-orphan"
    )
    reports = db.relationship(
        "Report", back_populates="user",
        lazy="dynamic", cascade="all, delete-orphan"
    )
    daily_health_logs = db.relationship(
        "DailyHealthLog", back_populates="user",
        lazy="dynamic", cascade="all, delete-orphan",
        order_by="desc(DailyHealthLog.log_date)",
    )

    # ── Password helpers ───────────────────────────────────────────────────

    @property
    def password(self):
        """Prevent reading the plain-text password."""
        raise AttributeError("password is write-only.")

    @password.setter
    def password(self, plain_text: str) -> None:
        """Hash and store the password using bcrypt."""
        self._password_hash = bcrypt.generate_password_hash(plain_text).decode("utf-8")

    def verify_password(self, plain_text: str) -> bool:
        """Return True if the supplied password matches the stored hash."""
        return bcrypt.check_password_hash(self._password_hash, plain_text)

    # ── Computed properties ────────────────────────────────────────────────

    @property
    def bmi(self) -> float | None:
        """Calculate Body Mass Index from height and weight."""
        if self.height_cm and self.weight_kg and self.height_cm > 0:
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m ** 2), 2)
        return None

    @property
    def bmi_category(self) -> str:
        """Return BMI category string."""
        bmi = self.bmi
        if bmi is None:
            return "Unknown"
        if bmi < 18.5:
            return "Underweight"
        if bmi < 25.0:
            return "Normal"
        if bmi < 30.0:
            return "Overweight"
        return "Obese"

    @property
    def is_admin(self) -> bool:
        """Convenience check for admin role."""
        return self.role == "admin"

    # ── Flask-Login required ───────────────────────────────────────────────

    def get_id(self) -> str:
        """Return the user ID as a unicode string (required by Flask-Login)."""
        return str(self.id)

    # ── Serialisation ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Return a JSON-safe representation (excludes sensitive fields)."""
        return {
            "id":               self.id,
            "full_name":        self.full_name,
            "age":              self.age,
            "gender":           self.gender,
            "height_cm":        self.height_cm,
            "weight_kg":        self.weight_kg,
            "bmi":              self.bmi,
            "bmi_category":     self.bmi_category,
            "email":            self.email,
            "is_email_verified": self.is_email_verified,
            "role":             self.role,
            "is_active":        self.is_active,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
            "last_login":       self.last_login.isoformat() if self.last_login else None,
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role!r}>"
