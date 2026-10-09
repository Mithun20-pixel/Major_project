"""
models/prediction.py - Disease Prediction ORM Model
=====================================================
Stores the ML prediction results for all 10 diseases per questionnaire.
Includes risk probabilities, risk levels, health scores, and XAI explanation paths.
"""

import json
from datetime import datetime
from extensions import db
from sqlalchemy.dialects.mysql import INTEGER as MYSQL_INTEGER


# ── Risk-level thresholds ──────────────────────────────────────────────────
RISK_LOW    = 33.0   # 0–33  → Low
RISK_MEDIUM = 66.0   # 34–66 → Medium
                     # 67–100 → High


def _classify_risk(probability: float) -> str:
    """Map a probability (0-100) to a risk-level string."""
    if probability is None:
        return "Unknown"
    if probability <= RISK_LOW:
        return "Low"
    if probability <= RISK_MEDIUM:
        return "Medium"
    return "High"


class Prediction(db.Model):
    """
    One row per prediction session (linked to a Questionnaire).

    Disease probability columns (0.0–100.0):
        diabetes_prob, heart_disease_prob, stroke_prob, hypertension_prob,
        obesity_prob, kidney_disease_prob, fatty_liver_prob,
        depression_prob, sleep_disorder_prob, thyroid_prob

    XAI artifact paths (relative to REPORTS_FOLDER):
        shap_summary_path, shap_force_path, shap_waterfall_path,
        lime_explanation_path
    """

    __tablename__ = "predictions"

    # ── Primary key ────────────────────────────────────────────────────────
    id               = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id          = db.Column(MYSQL_INTEGER(unsigned=True),
                                  db.ForeignKey("users.id", ondelete="CASCADE"),
                                  nullable=False, index=True)
    questionnaire_id = db.Column(MYSQL_INTEGER(unsigned=True),
                                  db.ForeignKey("questionnaires.id", ondelete="CASCADE"),
                                  nullable=False, index=True)

    # ── Disease probabilities (%) ──────────────────────────────────────────
    diabetes_prob       = db.Column(db.Float, nullable=True)
    heart_disease_prob  = db.Column(db.Float, nullable=True)
    stroke_prob         = db.Column(db.Float, nullable=True)
    hypertension_prob   = db.Column(db.Float, nullable=True)
    obesity_prob        = db.Column(db.Float, nullable=True)
    kidney_disease_prob = db.Column(db.Float, nullable=True)
    fatty_liver_prob    = db.Column(db.Float, nullable=True)
    depression_prob     = db.Column(db.Float, nullable=True)
    sleep_disorder_prob = db.Column(db.Float, nullable=True)
    thyroid_prob        = db.Column(db.Float, nullable=True)

    # ── Health scores (0–100) ──────────────────────────────────────────────
    overall_health_score  = db.Column(db.Float, nullable=True)
    lifestyle_score       = db.Column(db.Float, nullable=True)
    fitness_score         = db.Column(db.Float, nullable=True)
    diet_score            = db.Column(db.Float, nullable=True)
    mental_health_score   = db.Column(db.Float, nullable=True)
    sleep_score           = db.Column(db.Float, nullable=True)
    hydration_score       = db.Column(db.Float, nullable=True)
    exercise_score        = db.Column(db.Float, nullable=True)

    # ── XAI artefact paths ─────────────────────────────────────────────────
    shap_summary_path    = db.Column(db.String(512), nullable=True)
    shap_force_path      = db.Column(db.String(512), nullable=True)
    shap_waterfall_path  = db.Column(db.String(512), nullable=True)
    lime_explanation_path = db.Column(db.String(512), nullable=True)

    # ── Top features (JSON array of {feature, value, impact} dicts) ────────
    top_positive_factors = db.Column(db.Text, nullable=True)  # JSON
    top_negative_factors = db.Column(db.Text, nullable=True)  # JSON

    # ── Model metadata ─────────────────────────────────────────────────────
    model_version = db.Column(db.String(50), nullable=True)
    model_name    = db.Column(db.String(100), nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────
    user          = db.relationship("User",          back_populates="predictions")
    questionnaire = db.relationship("Questionnaire", back_populates="predictions")
    recommendations = db.relationship(
        "Recommendation", back_populates="prediction",
        lazy="dynamic", cascade="all, delete-orphan"
    )
    reports = db.relationship(
        "Report", back_populates="prediction",
        lazy="dynamic", cascade="all, delete-orphan"
    )

    # ── Computed properties ────────────────────────────────────────────────

    @property
    def disease_risks(self) -> dict:
        """
        Return a dictionary mapping disease name → {probability, risk_level}.
        Convenient for template rendering and API responses.
        """
        fields = {
            "Diabetes":       self.diabetes_prob,
            "Heart Disease":  self.heart_disease_prob,
            "Stroke":         self.stroke_prob,
            "Hypertension":   self.hypertension_prob,
            "Obesity":        self.obesity_prob,
            "Kidney Disease": self.kidney_disease_prob,
            "Fatty Liver":    self.fatty_liver_prob,
            "Depression":     self.depression_prob,
            "Sleep Disorder": self.sleep_disorder_prob,
            "Thyroid Disease": self.thyroid_prob,
        }
        return {
            disease: {
                "probability": prob,
                "risk_level":  _classify_risk(prob),
            }
            for disease, prob in fields.items()
        }

    @property
    def diabetes_model_type(self) -> str:
        """Return the backend diabetes model tier ('basic', 'enhanced', or 'clinical')."""
        if self.model_name in ("basic", "enhanced", "clinical"):
            return self.model_name
        return "basic"

    @property
    def health_scores(self) -> dict:
        """Return all health-score fields as a dict."""
        return {
            "Overall":      self.overall_health_score,
            "Lifestyle":    self.lifestyle_score,
            "Fitness":      self.fitness_score,
            "Diet":         self.diet_score,
            "Mental Health": self.mental_health_score,
            "Sleep":        self.sleep_score,
            "Hydration":    self.hydration_score,
            "Exercise":     self.exercise_score,
        }

    def get_top_positive_factors(self) -> list:
        """Deserialise the positive SHAP factors from JSON."""
        if self.top_positive_factors:
            return json.loads(self.top_positive_factors)
        return []

    def get_top_negative_factors(self) -> list:
        """Deserialise the negative SHAP factors from JSON."""
        if self.top_negative_factors:
            return json.loads(self.top_negative_factors)
        return []

    def to_dict(self) -> dict:
        """Return a JSON-safe summary for the API."""
        return {
            "id":               self.id,
            "user_id":          self.user_id,
            "questionnaire_id": self.questionnaire_id,
            "disease_risks":    self.disease_risks,
            "health_scores":    self.health_scores,
            "model_version":    self.model_version,
            "model_name":       self.model_name,
            "created_at":       self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Prediction id={self.id} user_id={self.user_id}>"
