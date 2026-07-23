"""
models/daily_health_log.py - Daily Health Log ORM Model
=========================================================
Stores one health log entry per user per day.
Covers: sleep, hydration, exercise, food, habits, mental health, and vitals.

Relationships:
    user → User (many-to-one)
    User.daily_health_logs → DailyHealthLog (one-to-many, back-populated)
"""

from datetime import datetime, date
from extensions import db


class DailyHealthLog(db.Model):
    """
    Represents a single day's lifestyle data submitted by the user.

    Unique constraint on (user_id, log_date) ensures only one entry per day.
    All optional vitals (blood_pressure, blood_sugar, heart_rate, anxiety_level)
    are nullable so they never block submission.
    """

    __tablename__ = "daily_health_logs"

    # ── Unique constraint: one log per user per day ────────────────────────
    __table_args__ = (
        db.UniqueConstraint("user_id", "log_date", name="uq_user_log_date"),
    )

    # ── Primary key ────────────────────────────────────────────────────────
    log_id  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Date of the log (should equal the day submitted) ──────────────────
    log_date = db.Column(db.Date, nullable=False, index=True)

    # ── Sleep ──────────────────────────────────────────────────────────────
    sleep_hours   = db.Column(db.Float,   nullable=False)   # 0–24
    sleep_quality = db.Column(db.Integer, nullable=False)   # 1–5

    # ── Water intake ───────────────────────────────────────────────────────
    water_intake = db.Column(db.Float, nullable=False)      # Litres

    # ── Exercise ───────────────────────────────────────────────────────────
    exercise_minutes = db.Column(db.Integer, nullable=False)  # 0–480
    steps            = db.Column(db.Integer, nullable=False)  # 0–100 000
    workout_type     = db.Column(db.String(100), nullable=True)  # Walking/Running/etc.

    # ── Meal completion (boolean per meal) ─────────────────────────────────
    breakfast = db.Column(db.Boolean, default=False, nullable=False)
    lunch     = db.Column(db.Boolean, default=False, nullable=False)
    dinner    = db.Column(db.Boolean, default=False, nullable=False)

    # ── Food quality ───────────────────────────────────────────────────────
    fruits      = db.Column(db.Integer, nullable=False, default=0)  # servings
    vegetables  = db.Column(db.Integer, nullable=False, default=0)  # servings
    junk_food   = db.Column(db.Boolean, default=False, nullable=False)
    sugary_drinks = db.Column(db.Boolean, default=False, nullable=False)

    # ── Habits ─────────────────────────────────────────────────────────────
    smoking = db.Column(db.Boolean, default=False, nullable=False)
    alcohol = db.Column(db.Boolean, default=False, nullable=False)
    tobacco = db.Column(db.Boolean, default=False, nullable=False)

    # ── Mental health ──────────────────────────────────────────────────────
    stress_level  = db.Column(db.Integer, nullable=False)   # 1–10
    mood          = db.Column(db.String(50), nullable=False) # Happy/Neutral/Sad/Anxious/Angry
    anxiety_level = db.Column(db.Integer, nullable=True)    # 1–10, optional

    # ── Health vitals ──────────────────────────────────────────────────────
    weight         = db.Column(db.Float,   nullable=False)          # kg
    blood_pressure = db.Column(db.String(20), nullable=True)        # "120/80"
    blood_sugar    = db.Column(db.Float,   nullable=True)           # mg/dL
    heart_rate     = db.Column(db.Integer, nullable=True)           # bpm

    # ── Timestamps ─────────────────────────────────────────────────────────
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # ── Relationships ──────────────────────────────────────────────────────
    user = db.relationship("User", back_populates="daily_health_logs")

    # ── Computed helpers ───────────────────────────────────────────────────

    @property
    def meals_completed(self) -> int:
        """Return the number of main meals completed (0–3)."""
        return sum([self.breakfast, self.lunch, self.dinner])

    @property
    def healthy_habits_score(self) -> float:
        """
        Quick 0–100 composite score for a single day.

        Dimensions: sleep, water, exercise, diet, stress, bad habits.
        Used for the health-score trend chart.
        """
        score = 0.0

        # Sleep: optimal = 7–9 hrs (max 20 pts)
        score += max(0, 20 - abs(self.sleep_hours - 8) * 4)

        # Water: optimal ≥ 2.5 L (max 15 pts)
        score += min(15, (self.water_intake / 3.0) * 15)

        # Exercise: 30 min = good, 60+ = great (max 20 pts)
        score += min(20, (self.exercise_minutes / 60) * 20)

        # Diet: fruits + veg servings (max 15 pts)
        score += min(15, ((self.fruits + self.vegetables) / 10) * 15)

        # Meals: 3 complete meals (max 10 pts)
        score += (self.meals_completed / 3) * 10

        # Stress: low stress → high score (max 10 pts)
        score += max(0, 10 - self.stress_level)

        # Bad habits penalty (each −5)
        if self.smoking:
            score -= 5
        if self.alcohol:
            score -= 5
        if self.junk_food:
            score -= 5
        if self.sugary_drinks:
            score -= 3

        return round(max(0.0, min(100.0, score)), 1)

    def to_dict(self) -> dict:
        """Return a JSON-safe dictionary representation."""
        return {
            "log_id":           self.log_id,
            "user_id":          self.user_id,
            "log_date":         self.log_date.isoformat() if self.log_date else None,
            "sleep_hours":      self.sleep_hours,
            "sleep_quality":    self.sleep_quality,
            "water_intake":     self.water_intake,
            "exercise_minutes": self.exercise_minutes,
            "steps":            self.steps,
            "workout_type":     self.workout_type,
            "breakfast":        self.breakfast,
            "lunch":            self.lunch,
            "dinner":           self.dinner,
            "fruits":           self.fruits,
            "vegetables":       self.vegetables,
            "junk_food":        self.junk_food,
            "sugary_drinks":    self.sugary_drinks,
            "smoking":          self.smoking,
            "alcohol":          self.alcohol,
            "tobacco":          self.tobacco,
            "stress_level":     self.stress_level,
            "mood":             self.mood,
            "anxiety_level":    self.anxiety_level,
            "weight":           self.weight,
            "blood_pressure":   self.blood_pressure,
            "blood_sugar":      self.blood_sugar,
            "heart_rate":       self.heart_rate,
            "daily_score":      self.healthy_habits_score,
            "created_at":       self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return (
            f"<DailyHealthLog log_id={self.log_id} "
            f"user_id={self.user_id} date={self.log_date}>"
        )
