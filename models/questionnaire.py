"""
models/questionnaire.py - Health Questionnaire ORM Model
=========================================================
Stores every response from the health questionnaire.
Each User can have multiple Questionnaire records (one per prediction session).
"""

from datetime import datetime
from extensions import db


class Questionnaire(db.Model):
    """
    Persists the full lifestyle and medical questionnaire answers.

    All numeric fields use nullable=True so partial saves are allowed.
    Final submission sets `is_complete = True`.
    """

    __tablename__ = "questionnaires"

    # ── Primary key ────────────────────────────────────────────────────────
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                           nullable=False, index=True)

    # ── Section 1: Personal Information ───────────────────────────────────
    age          = db.Column(db.Integer, nullable=True)
    gender       = db.Column(db.String(20), nullable=True)
    height_cm    = db.Column(db.Float,   nullable=True)
    weight_kg    = db.Column(db.Float,   nullable=True)
    bmi          = db.Column(db.Float,   nullable=True)
    occupation   = db.Column(db.String(100), nullable=True)
    working_hours_per_day = db.Column(db.Float, nullable=True)

    # ── Section 2: Lifestyle ───────────────────────────────────────────────
    smoking_status   = db.Column(db.String(50),  nullable=True)  # Never/Former/Current
    cigarettes_per_day = db.Column(db.Integer,   nullable=True)  # times/cigarettes smoked per day
    alcohol_intake   = db.Column(db.String(50),  nullable=True)  # None/Occasional/Moderate/Heavy
    sleep_hours      = db.Column(db.Float,        nullable=True)
    screen_time_hours= db.Column(db.Float,        nullable=True)
    stress_level     = db.Column(db.Integer,      nullable=True)  # 1-10 scale
    travel_frequency = db.Column(db.String(50),   nullable=True)  # Rarely/Weekly/Daily

    # ── Section 3: Food Habits ────────────────────────────────────────────
    diet_type        = db.Column(db.String(50),  nullable=True)   # Veg/Non-Veg/Vegan/etc.
    meals_per_day    = db.Column(db.Integer,     nullable=True)
    water_intake_L   = db.Column(db.Float,       nullable=True)
    fast_food_per_week = db.Column(db.Integer,   nullable=True)
    sugar_intake     = db.Column(db.String(50),  nullable=True)   # Low/Moderate/High
    fruit_veg_servings = db.Column(db.Integer,   nullable=True)   # per day

    # ── Section 4: Exercise ───────────────────────────────────────────────
    exercise_frequency    = db.Column(db.String(50), nullable=True)  # Never/1-2x/3-4x/5+
    exercise_type         = db.Column(db.String(100),nullable=True)
    exercise_duration_min = db.Column(db.Integer,    nullable=True)  # minutes per session
    heart_rate_resting    = db.Column(db.Integer,    nullable=True)  # bpm

    # ── Section 5: Medical History ────────────────────────────────────────
    existing_diseases    = db.Column(db.Text, nullable=True)  # comma-separated
    current_medications  = db.Column(db.Text, nullable=True)
    blood_pressure_systolic  = db.Column(db.Integer, nullable=True)
    blood_pressure_diastolic = db.Column(db.Integer, nullable=True)
    blood_sugar_fasting  = db.Column(db.Float,   nullable=True)
    cholesterol_level    = db.Column(db.Float,   nullable=True)
    vaccination_status   = db.Column(db.String(100), nullable=True)

    # ── Section 6: Family History ─────────────────────────────────────────
    family_diabetes       = db.Column(db.Boolean, default=False)
    family_heart_disease  = db.Column(db.Boolean, default=False)
    family_stroke         = db.Column(db.Boolean, default=False)
    family_hypertension   = db.Column(db.Boolean, default=False)
    family_obesity        = db.Column(db.Boolean, default=False)
    family_kidney_disease = db.Column(db.Boolean, default=False)
    family_cancer         = db.Column(db.Boolean, default=False)
    family_thyroid        = db.Column(db.Boolean, default=False)
    family_depression     = db.Column(db.Boolean, default=False)

    # ── Section 7: Mental Health ──────────────────────────────────────────
    depression_symptoms  = db.Column(db.Boolean, default=False)
    anxiety_symptoms     = db.Column(db.Boolean, default=False)
    mental_health_support = db.Column(db.Boolean, default=False)
    meditation_yoga      = db.Column(db.String(50), nullable=True)  # Never/Sometimes/Regular

    # ── Section 8: Other ──────────────────────────────────────────────────
    pregnancy_status  = db.Column(db.String(50), nullable=True)  # N/A / Yes / Post
    daily_steps       = db.Column(db.Integer,    nullable=True)

    # ── Submission state ──────────────────────────────────────────────────
    is_complete = db.Column(db.Boolean, default=False, nullable=False)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                            onupdate=datetime.utcnow, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────
    user        = db.relationship("User", back_populates="questionnaires")
    predictions = db.relationship(
        "Prediction", back_populates="questionnaire",
        lazy="dynamic", cascade="all, delete-orphan"
    )

    # ── Helpers ───────────────────────────────────────────────────────────

    def to_feature_dict(self) -> dict:
        """
        Return only the ML feature columns as a flat dictionary.
        Used as input for the prediction pipeline.
        """
        return {
            "age":                    self.age,
            "gender":                 self.gender,
            "bmi":                    self.bmi,
            "occupation":             self.occupation,
            "working_hours_per_day":  self.working_hours_per_day,
            "smoking_status":         self.smoking_status,
            "cigarettes_per_day":     self.cigarettes_per_day,
            "alcohol_intake":         self.alcohol_intake,
            "sleep_hours":            self.sleep_hours,
            "screen_time_hours":      self.screen_time_hours,
            "stress_level":           self.stress_level,
            "diet_type":              self.diet_type,
            "meals_per_day":          self.meals_per_day,
            "water_intake_L":         self.water_intake_L,
            "fast_food_per_week":     self.fast_food_per_week,
            "sugar_intake":           self.sugar_intake,
            "fruit_veg_servings":     self.fruit_veg_servings,
            "exercise_frequency":     self.exercise_frequency,
            "exercise_duration_min":  self.exercise_duration_min,
            "heart_rate_resting":     self.heart_rate_resting,
            "blood_pressure_systolic":   self.blood_pressure_systolic,
            "blood_pressure_diastolic":  self.blood_pressure_diastolic,
            "blood_sugar_fasting":    self.blood_sugar_fasting,
            "cholesterol_level":      self.cholesterol_level,
            "family_diabetes":        int(self.family_diabetes or 0),
            "family_heart_disease":   int(self.family_heart_disease or 0),
            "family_stroke":          int(self.family_stroke or 0),
            "family_hypertension":    int(self.family_hypertension or 0),
            "family_obesity":         int(self.family_obesity or 0),
            "family_kidney_disease":  int(self.family_kidney_disease or 0),
            "family_thyroid":         int(self.family_thyroid or 0),
            "family_depression":      int(self.family_depression or 0),
            "depression_symptoms":    int(self.depression_symptoms or 0),
            "anxiety_symptoms":       int(self.anxiety_symptoms or 0),
            "meditation_yoga":        self.meditation_yoga,
            "daily_steps":            self.daily_steps,
        }

    def __repr__(self) -> str:
        return f"<Questionnaire id={self.id} user_id={self.user_id} complete={self.is_complete}>"
