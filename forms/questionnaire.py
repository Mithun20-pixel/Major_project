"""
forms/questionnaire.py - Multi-Step Questionnaire WTForms
===========================================================
Seven form classes, one per wizard step.
All fields include detailed validators for input sanitisation.
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, IntegerField, FloatField,
    SelectField, BooleanField, TextAreaField, SubmitField
)
from wtforms.validators import DataRequired, NumberRange, Optional, Length


# ── Step 1: Personal Information ───────────────────────────────────────────

class PersonalInfoForm(FlaskForm):
    """Step 1 – Personal & occupation details."""

    age = IntegerField(
        "Age (years)",
        validators=[
            DataRequired(),
            NumberRange(min=1, max=120, message="Age must be 1–120.")
        ]
    )
    gender = SelectField(
        "Gender",
        choices=[("", "Select"), ("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
        validators=[DataRequired()]
    )
    height_cm = FloatField(
        "Height (cm)",
        validators=[Optional(), NumberRange(min=50, max=300)]
    )
    weight_kg = FloatField(
        "Weight (kg)",
        validators=[Optional(), NumberRange(min=1, max=500)]
    )
    occupation = StringField(
        "Occupation",
        validators=[Optional(), Length(max=100)]
    )
    working_hours_per_day = FloatField(
        "Working Hours per Day",
        validators=[Optional(), NumberRange(min=0, max=24)]
    )
    submit = SubmitField("Next →")


# ── Step 2: Lifestyle ──────────────────────────────────────────────────────

class LifestyleForm(FlaskForm):
    """Step 2 – Lifestyle habits."""

    smoking_status = SelectField(
        "Smoking Status",
        choices=[
            ("", "Select"), ("Never", "Never"),
            ("Former", "Former Smoker"), ("Current", "Current Smoker")
        ],
        validators=[DataRequired()]
    )
    alcohol_intake = SelectField(
        "Alcohol Intake",
        choices=[
            ("", "Select"), ("None", "None"),
            ("Occasional", "Occasional (1-2/week)"),
            ("Moderate", "Moderate (3-5/week)"),
            ("Heavy", "Heavy (Daily)")
        ],
        validators=[DataRequired()]
    )
    sleep_hours = FloatField(
        "Average Sleep Hours per Night",
        validators=[DataRequired(), NumberRange(min=0, max=24)]
    )
    screen_time_hours = FloatField(
        "Daily Screen Time (hours)",
        validators=[Optional(), NumberRange(min=0, max=24)]
    )
    stress_level = IntegerField(
        "Stress Level (1 = Low, 10 = High)",
        validators=[DataRequired(), NumberRange(min=1, max=10)]
    )
    travel_frequency = SelectField(
        "Travel Frequency",
        choices=[
            ("", "Select"), ("Rarely", "Rarely"),
            ("Weekly", "Weekly"), ("Daily", "Daily")
        ],
        validators=[Optional()]
    )
    submit = SubmitField("Next →")


# ── Step 3: Food Habits ────────────────────────────────────────────────────

class FoodHabitsForm(FlaskForm):
    """Step 3 – Dietary habits."""

    diet_type = SelectField(
        "Diet Type",
        choices=[
            ("", "Select"), ("Vegetarian", "Vegetarian"),
            ("Non-Vegetarian", "Non-Vegetarian"),
            ("Vegan", "Vegan"), ("Pescatarian", "Pescatarian"),
            ("Keto", "Keto"), ("Mixed", "Mixed")
        ],
        validators=[DataRequired()]
    )
    meals_per_day = IntegerField(
        "Number of Meals per Day",
        validators=[DataRequired(), NumberRange(min=1, max=10)]
    )
    water_intake_L = FloatField(
        "Daily Water Intake (litres)",
        validators=[DataRequired(), NumberRange(min=0, max=20)]
    )
    fast_food_per_week = IntegerField(
        "Fast Food Meals per Week",
        validators=[DataRequired(), NumberRange(min=0, max=21)]
    )
    sugar_intake = SelectField(
        "Daily Sugar Intake Level",
        choices=[("", "Select"), ("Low", "Low"), ("Moderate", "Moderate"), ("High", "High")],
        validators=[DataRequired()]
    )
    fruit_veg_servings = IntegerField(
        "Fruit & Vegetable Servings per Day",
        validators=[DataRequired(), NumberRange(min=0, max=20)]
    )
    submit = SubmitField("Next →")


# ── Step 4: Medical History ────────────────────────────────────────────────

class MedicalHistoryForm(FlaskForm):
    """Step 4 – Medical history and current vitals."""

    existing_diseases = TextAreaField(
        "Existing Diseases (comma-separated, or 'None')",
        validators=[Optional(), Length(max=500)]
    )
    current_medications = TextAreaField(
        "Current Medications (comma-separated, or 'None')",
        validators=[Optional(), Length(max=500)]
    )
    blood_pressure_systolic = IntegerField(
        "Blood Pressure – Systolic (mmHg)",
        validators=[Optional(), NumberRange(min=60, max=300)]
    )
    blood_pressure_diastolic = IntegerField(
        "Blood Pressure – Diastolic (mmHg)",
        validators=[Optional(), NumberRange(min=40, max=200)]
    )
    blood_sugar_fasting = FloatField(
        "Fasting Blood Sugar (mg/dL)",
        validators=[Optional(), NumberRange(min=50, max=600)]
    )
    cholesterol_level = FloatField(
        "Total Cholesterol (mg/dL)",
        validators=[Optional(), NumberRange(min=50, max=600)]
    )
    vaccination_status = SelectField(
        "Vaccination Status",
        choices=[
            ("", "Select"), ("Up to date", "Up to date"),
            ("Partially vaccinated", "Partially vaccinated"),
            ("Not vaccinated", "Not vaccinated"),
            ("Unknown", "Unknown")
        ],
        validators=[Optional()]
    )
    submit = SubmitField("Next →")


# ── Step 5: Family History ─────────────────────────────────────────────────

class FamilyHistoryForm(FlaskForm):
    """Step 5 – Family disease history (yes/no checkboxes)."""

    family_diabetes       = BooleanField("Diabetes in family")
    family_heart_disease  = BooleanField("Heart disease in family")
    family_stroke         = BooleanField("Stroke in family")
    family_hypertension   = BooleanField("Hypertension in family")
    family_obesity        = BooleanField("Obesity in family")
    family_kidney_disease = BooleanField("Kidney disease in family")
    family_cancer         = BooleanField("Cancer in family")
    family_thyroid        = BooleanField("Thyroid disease in family")
    family_depression     = BooleanField("Depression / mental illness in family")
    submit = SubmitField("Next →")


# ── Step 6: Exercise ───────────────────────────────────────────────────────

class ExerciseForm(FlaskForm):
    """Step 6 – Physical activity and fitness."""

    exercise_frequency = SelectField(
        "Exercise Frequency",
        choices=[
            ("", "Select"), ("Never", "Never"),
            ("1-2x per week", "1-2x per week"),
            ("3-4x per week", "3-4x per week"),
            ("5+ times per week", "5+ times per week")
        ],
        validators=[DataRequired()]
    )
    exercise_type = StringField(
        "Primary Exercise Type (e.g. Walking, Gym, Yoga)",
        validators=[Optional(), Length(max=100)]
    )
    exercise_duration_min = IntegerField(
        "Exercise Duration per Session (minutes)",
        validators=[Optional(), NumberRange(min=0, max=480)]
    )
    heart_rate_resting = IntegerField(
        "Resting Heart Rate (bpm)",
        validators=[Optional(), NumberRange(min=30, max=200)]
    )
    daily_steps = IntegerField(
        "Average Daily Steps",
        validators=[Optional(), NumberRange(min=0, max=100000)]
    )
    submit = SubmitField("Next →")


# ── Step 7: Mental Health ──────────────────────────────────────────────────

class MentalHealthForm(FlaskForm):
    """Step 7 – Mental health status and final questions."""

    depression_symptoms   = BooleanField("I experience frequent low mood / depression symptoms")
    anxiety_symptoms      = BooleanField("I experience frequent anxiety or panic attacks")
    mental_health_support = BooleanField("I am currently receiving mental health support")
    meditation_yoga = SelectField(
        "Meditation / Yoga Practice",
        choices=[
            ("", "Select"), ("Never", "Never"),
            ("Sometimes", "Sometimes"),
            ("Regular", "Regular (3+ times/week)")
        ],
        validators=[Optional()]
    )
    pregnancy_status = SelectField(
        "Pregnancy Status",
        choices=[
            ("N/A", "Not applicable"),
            ("Yes", "Currently pregnant"),
            ("Post", "Postpartum (within 1 year)")
        ],
        validators=[Optional()]
    )
    submit = SubmitField("Submit & Get My Results 🚀")
