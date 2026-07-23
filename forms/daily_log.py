"""
forms/daily_log.py - Daily Health Log WTForms
===============================================
Defines DailyHealthLogForm used on the /tracker/log route.
All optional fields use validators.Optional() so they don't block submission.
"""

from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    FloatField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    NumberRange,
    Optional,
    ValidationError,
)


# ── Mood choices ───────────────────────────────────────────────────────────
MOOD_CHOICES = [
    ("", "— Select Mood —"),
    ("Happy",    "😊 Happy"),
    ("Neutral",  "😐 Neutral"),
    ("Sad",      "😢 Sad"),
    ("Anxious",  "😰 Anxious"),
    ("Angry",    "😠 Angry"),
    ("Energetic","⚡ Energetic"),
    ("Tired",    "😴 Tired"),
]

# ── Workout type choices ───────────────────────────────────────────────────
WORKOUT_CHOICES = [
    ("None",        "None / Rest Day"),
    ("Walking",     "🚶 Walking"),
    ("Running",     "🏃 Running"),
    ("Cycling",     "🚴 Cycling"),
    ("Swimming",    "🏊 Swimming"),
    ("Gym/Weights", "🏋️ Gym / Weights"),
    ("Yoga",        "🧘 Yoga"),
    ("Sports",      "⚽ Sports"),
    ("HIIT",        "🔥 HIIT"),
    ("Other",       "Other"),
]


class DailyHealthLogForm(FlaskForm):
    """
    Comprehensive daily health log form.

    Sections:
        1. Date
        2. Sleep
        3. Water Intake
        4. Exercise
        5. Food Habits
        6. Habits (smoking / alcohol / tobacco)
        7. Mental Health
        8. Health Vitals
    """

    # ── Section 1: Date ────────────────────────────────────────────────────
    log_date = DateField(
        "Log Date",
        validators=[DataRequired(message="Please select a date.")],
        default=date.today,
        description="One entry per day is allowed.",
    )

    # ── Section 2: Sleep ───────────────────────────────────────────────────
    sleep_hours = FloatField(
        "Sleep Hours",
        validators=[
            DataRequired(message="Sleep hours are required."),
            NumberRange(min=0, max=24, message="Sleep hours must be between 0 and 24."),
        ],
        description="Total hours of sleep last night.",
    )
    sleep_quality = SelectField(
        "Sleep Quality",
        choices=[
            ("1", "1 – Very Poor"),
            ("2", "2 – Poor"),
            ("3", "3 – Average"),
            ("4", "4 – Good"),
            ("5", "5 – Excellent"),
        ],
        coerce=int,
        validators=[DataRequired()],
        description="Rate your sleep quality from 1 (worst) to 5 (best).",
    )

    # ── Section 3: Water Intake ────────────────────────────────────────────
    water_intake = FloatField(
        "Water Intake (Litres)",
        validators=[
            DataRequired(message="Water intake is required."),
            NumberRange(min=0, max=20, message="Water intake must be between 0 and 20 L."),
        ],
        description="Total litres of water consumed today.",
    )

    # ── Section 4: Exercise ────────────────────────────────────────────────
    exercise_minutes = IntegerField(
        "Exercise Duration (minutes)",
        validators=[
            DataRequired(message="Enter 0 if no exercise today."),
            NumberRange(min=0, max=480, message="Exercise duration must be 0–480 minutes."),
        ],
    )
    steps = IntegerField(
        "Steps Walked",
        validators=[
            DataRequired(message="Enter 0 if steps are unknown."),
            NumberRange(min=0, max=100_000, message="Steps must be between 0 and 100,000."),
        ],
    )
    workout_type = SelectField(
        "Workout Type",
        choices=WORKOUT_CHOICES,
        validators=[Optional()],
    )

    # ── Section 5: Food Habits ─────────────────────────────────────────────
    breakfast     = BooleanField("Breakfast Completed")
    lunch         = BooleanField("Lunch Completed")
    dinner        = BooleanField("Dinner Completed")

    fruits = IntegerField(
        "Fruits Consumed (servings)",
        validators=[
            Optional(),
            NumberRange(min=0, max=20, message="Must be between 0 and 20."),
        ],
        default=0,
    )
    vegetables = IntegerField(
        "Vegetables Consumed (servings)",
        validators=[
            Optional(),
            NumberRange(min=0, max=20, message="Must be between 0 and 20."),
        ],
        default=0,
    )
    junk_food     = BooleanField("Had Junk Food Today")
    sugary_drinks = BooleanField("Had Sugary Drinks Today")

    # ── Section 6: Habits ──────────────────────────────────────────────────
    smoking = BooleanField("Smoked Today")
    alcohol = BooleanField("Consumed Alcohol Today")
    tobacco = BooleanField("Used Tobacco Today")

    # ── Section 7: Mental Health ───────────────────────────────────────────
    stress_level = IntegerField(
        "Stress Level (1–10)",
        validators=[
            DataRequired(message="Stress level is required."),
            NumberRange(min=1, max=10, message="Stress level must be between 1 and 10."),
        ],
        description="1 = No stress, 10 = Extremely stressed.",
    )
    mood = SelectField(
        "Mood",
        choices=MOOD_CHOICES,
        validators=[DataRequired(message="Please select your mood.")],
    )
    anxiety_level = IntegerField(
        "Anxiety Level (1–10, optional)",
        validators=[
            Optional(),
            NumberRange(min=1, max=10, message="Anxiety level must be between 1 and 10."),
        ],
        description="Leave blank if not applicable.",
    )

    # ── Section 8: Health Vitals ───────────────────────────────────────────
    weight = FloatField(
        "Current Weight (kg)",
        validators=[
            DataRequired(message="Weight is required."),
            NumberRange(min=20, max=300, message="Weight must be between 20 and 300 kg."),
        ],
    )
    blood_pressure = StringField(
        "Blood Pressure (e.g. 120/80, optional)",
        validators=[Optional()],
        description="Format: systolic/diastolic",
    )
    blood_sugar = FloatField(
        "Blood Sugar – Fasting (mg/dL, optional)",
        validators=[
            Optional(),
            NumberRange(min=40, max=600, message="Blood sugar must be between 40 and 600."),
        ],
    )
    heart_rate = IntegerField(
        "Heart Rate (bpm, optional)",
        validators=[
            Optional(),
            NumberRange(min=30, max=250, message="Heart rate must be between 30 and 250 bpm."),
        ],
    )

    # ── Submit ─────────────────────────────────────────────────────────────
    submit = SubmitField("💾 Save Daily Log")

    # ── Custom validators ──────────────────────────────────────────────────

    def validate_log_date(self, field):
        """Disallow future dates — a log must be for today or a past day."""
        if field.data and field.data > date.today():
            raise ValidationError("You cannot log a future date.")

    def validate_blood_pressure(self, field):
        """Loosely validate the 'systolic/diastolic' format if provided."""
        if field.data:
            parts = field.data.strip().split("/")
            if len(parts) != 2:
                raise ValidationError(
                    "Blood pressure must be in 'systolic/diastolic' format, e.g. 120/80."
                )
            try:
                systolic  = int(parts[0])
                diastolic = int(parts[1])
            except ValueError:
                raise ValidationError("Blood pressure values must be whole numbers.")
            if not (60 <= systolic <= 250):
                raise ValidationError("Systolic pressure should be between 60 and 250.")
            if not (40 <= diastolic <= 150):
                raise ValidationError("Diastolic pressure should be between 40 and 150.")
