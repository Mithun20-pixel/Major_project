"""
models/recommendation.py - Personalised Health Recommendation ORM Model
=========================================================================
Stores AI-generated recommendations linked to a specific Prediction.
"""

from datetime import datetime
from extensions import db


# ── Category constants ─────────────────────────────────────────────────────
CATEGORY_EXERCISE    = "exercise"
CATEGORY_DIET        = "diet"
CATEGORY_HYDRATION   = "hydration"
CATEGORY_SLEEP       = "sleep"
CATEGORY_MEDICAL     = "medical"
CATEGORY_STRESS      = "stress"
CATEGORY_SMOKING     = "smoking_cessation"
CATEGORY_ALCOHOL     = "alcohol_reduction"
CATEGORY_MENTAL      = "mental_health"
CATEGORY_LIFESTYLE   = "lifestyle"


class Recommendation(db.Model):
    """
    One recommendation row per personalised suggestion.
    A prediction typically produces multiple recommendation rows.
    """

    __tablename__ = "recommendations"

    # ── Primary key ────────────────────────────────────────────────────────
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prediction_id = db.Column(db.Integer,
                               db.ForeignKey("predictions.id", ondelete="CASCADE"),
                               nullable=False, index=True)
    user_id       = db.Column(db.Integer,
                               db.ForeignKey("users.id", ondelete="CASCADE"),
                               nullable=False, index=True)

    # ── Content ────────────────────────────────────────────────────────────
    category    = db.Column(db.String(60),  nullable=False)   # see constants above
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text,        nullable=False)
    priority    = db.Column(db.Integer,     default=5)         # 1 (highest) – 10
    icon        = db.Column(db.String(60),  nullable=True)     # e.g. Bootstrap icon class

    # ── Related disease (optional) ─────────────────────────────────────────
    related_disease = db.Column(db.String(100), nullable=True)

    # ── Completion tracking ────────────────────────────────────────────────
    is_completed    = db.Column(db.Boolean, default=False)
    completed_at    = db.Column(db.DateTime, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────
    prediction = db.relationship("Prediction", back_populates="recommendations")

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "prediction_id":    self.prediction_id,
            "category":         self.category,
            "title":            self.title,
            "description":      self.description,
            "priority":         self.priority,
            "icon":             self.icon,
            "related_disease":  self.related_disease,
            "is_completed":     self.is_completed,
        }

    def __repr__(self) -> str:
        return f"<Recommendation id={self.id} category={self.category!r}>"


# ── models/report.py ─────────────────────────────────────────────────────
