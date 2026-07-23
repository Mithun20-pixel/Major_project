"""
models/model_log.py - ML Model Training Log ORM Model
=======================================================
Tracks each model training run: algorithm, metrics, version, file path.
Used by the Admin module to display model performance history.
"""

import json
from datetime import datetime
from extensions import db


class ModelLog(db.Model):
    """
    Records training metadata for each disease-model training run.
    One row per (disease, algorithm, training_run).
    """

    __tablename__ = "model_logs"

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ── Model identity ─────────────────────────────────────────────────────
    disease    = db.Column(db.String(100), nullable=False, index=True)
    algorithm  = db.Column(db.String(100), nullable=False)
    version    = db.Column(db.String(50),  nullable=False)
    is_active  = db.Column(db.Boolean, default=False, nullable=False)
    model_path = db.Column(db.String(512), nullable=True)

    # ── Performance metrics ────────────────────────────────────────────────
    accuracy   = db.Column(db.Float, nullable=True)
    precision  = db.Column(db.Float, nullable=True)
    recall     = db.Column(db.Float, nullable=True)
    f1_score   = db.Column(db.Float, nullable=True)
    roc_auc    = db.Column(db.Float, nullable=True)

    # ── Extra metrics as JSON (confusion matrix, feature importances, etc.) ─
    extra_metrics = db.Column(db.Text, nullable=True)

    # ── Training metadata ─────────────────────────────────────────────────
    training_samples  = db.Column(db.Integer, nullable=True)
    training_duration = db.Column(db.Float,   nullable=True)  # seconds
    trained_by        = db.Column(db.String(100), nullable=True)  # admin email

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # ── Helpers ───────────────────────────────────────────────────────────

    def get_extra_metrics(self) -> dict:
        """Deserialise extra metrics from JSON storage."""
        if self.extra_metrics:
            return json.loads(self.extra_metrics)
        return {}

    def set_extra_metrics(self, metrics: dict) -> None:
        """Serialise and store extra metrics as JSON."""
        self.extra_metrics = json.dumps(metrics)

    def to_dict(self) -> dict:
        return {
            "id":                self.id,
            "disease":           self.disease,
            "algorithm":         self.algorithm,
            "version":           self.version,
            "is_active":         self.is_active,
            "accuracy":          self.accuracy,
            "precision":         self.precision,
            "recall":            self.recall,
            "f1_score":          self.f1_score,
            "roc_auc":           self.roc_auc,
            "training_samples":  self.training_samples,
            "training_duration": self.training_duration,
            "created_at":        self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return (
            f"<ModelLog id={self.id} disease={self.disease!r} "
            f"algo={self.algorithm!r} v={self.version!r} active={self.is_active}>"
        )


# ── models/admin.py ───────────────────────────────────────────────────────
