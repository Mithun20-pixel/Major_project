"""
models/activity_log.py - User Activity Log ORM Model
======================================================
Stores real-time activity logs for users (logins, predictions, daily logs, account updates).
Used by administrators to monitor system activity and user actions.
"""

from datetime import datetime
from extensions import db
from sqlalchemy.dialects.mysql import INTEGER as MYSQL_INTEGER


class UserActivityLog(db.Model):
    """
    Logs user activities and system actions for audit and administrative tracking.
    """

    __tablename__ = "user_activity_logs"

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(MYSQL_INTEGER(unsigned=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    action     = db.Column(db.String(120), nullable=False, index=True)
    details    = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(100), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # ── Relationship ───────────────────────────────────────────────────────
    user = db.relationship("User", backref=db.backref("activity_logs", lazy="dynamic", cascade="all, delete-orphan"))

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "user_id":    self.user_id,
            "user_name":  self.user.full_name if self.user else "System/Guest",
            "user_email": self.user.email if self.user else "N/A",
            "action":     self.action,
            "details":    self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<UserActivityLog id={self.id} user_id={self.user_id} action={self.action!r}>"
