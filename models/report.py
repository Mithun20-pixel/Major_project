"""
models/report.py - PDF Report ORM Model
=========================================
Tracks generated PDF health reports linked to a Prediction.
"""

from datetime import datetime
from extensions import db


class Report(db.Model):
    """
    Represents a generated PDF report for a prediction session.

    file_path is stored relative to REPORTS_FOLDER.
    """

    __tablename__ = "reports"

    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id       = db.Column(db.Integer,
                               db.ForeignKey("users.id",       ondelete="CASCADE"),
                               nullable=False, index=True)
    prediction_id = db.Column(db.Integer,
                               db.ForeignKey("predictions.id", ondelete="CASCADE"),
                               nullable=False, index=True)

    file_name  = db.Column(db.String(255), nullable=False)
    file_path  = db.Column(db.String(512), nullable=False)
    file_size  = db.Column(db.Integer,     nullable=True)   # bytes

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────
    user       = db.relationship("User",       back_populates="reports")
    prediction = db.relationship("Prediction", back_populates="reports")

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "prediction_id": self.prediction_id,
            "file_name":     self.file_name,
            "file_size":     self.file_size,
            "created_at":    self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Report id={self.id} file={self.file_name!r}>"


# ── models/model_log.py ───────────────────────────────────────────────────
