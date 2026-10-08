"""
forms/questionnaire.py - Streamlined 4-Step Questionnaire WTForms
==================================================================
Four consolidated form classes matching the 4-Pillar health architecture.
All fields include detailed validators for input sanitisation and boundary checking.
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, IntegerField, FloatField,
    SelectField, BooleanField, TextAreaField, SubmitField
)
from wtforms.validators import DataRequired, NumberRange, Optional, Length, ValidationError


# ── Step 1: Personal Profile & Vitals ────────────────────────────────────────

class PersonalInfoForm(FlaskForm):
    """Step 1 – Personal demographics & baseline physical vitals (All Mandatory)."""

    # Demographics
    age = IntegerField(
        "Age (years)",
        validators=[
            DataRequired(message="Please enter your age."),
            NumberRange(min=5, max=100, message="Age must be between 5 and 100 years.")
        ]
    )
    gender = SelectField(
        "Gender",
        choices=[("", "Select Gender"), ("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
        validators=[DataRequired(message="Please select your gender.")]
    )
    height_cm = FloatField(
        "Height (cm)",
        validators=[
            DataRequired(message="Please enter your height in cm."),
            NumberRange(min=50, max=250, message="Height must be between 50 and 250 cm.")
        ]
    )
    weight_kg = FloatField(
        "Weight (kg)",
        validators=[
            DataRequired(message="Please enter your weight in kg."),
            NumberRange(min=10, max=120, message="Weight must be between 10 and 120 kg.")
        ]
    )
    occupation = StringField(
        "Occupation",
        validators=[
            DataRequired(message="Please enter your occupation."),
            Length(max=100, message="Occupation cannot exceed 100 characters.")
        ]
    )
    working_hours_per_day = FloatField(
        "Working Hours per Day",
        validators=[
            DataRequired(message="Please enter your working hours per day."),
            NumberRange(min=0, max=24, message="Working hours must be between 0 and 24 hours.")
        ]
    )

    # Physical Vitals (Mandatory)
    blood_pressure_systolic = IntegerField(
        "Blood Pressure – Systolic (mmHg)",
        validators=[
            DataRequired(message="Please enter your systolic blood pressure.")
        ]
    )
    blood_pressure_diastolic = IntegerField(
        "Blood Pressure – Diastolic (mmHg)",
        validators=[
            DataRequired(message="Please enter your diastolic blood pressure.")
        ]
    )
    blood_sugar_fasting = FloatField(
        "Fasting Blood Sugar (mg/dL)",
        validators=[
            DataRequired(message="Please enter your fasting blood sugar level.")
        ]
    )
    cholesterol_level = FloatField(
        "Total Cholesterol (mg/dL)",
        validators=[
            DataRequired(message="Please enter your total cholesterol level.")
        ]
    )
    heart_rate_resting = IntegerField(
        "Resting Heart Rate (bpm)",
        validators=[
            DataRequired(message="Please enter your resting heart rate.")
        ]
    )

    submit = SubmitField("Next: Lifestyle & Diet →")


# ── Step 2: Daily Lifestyle, Nutrition & Activity ────────────────────────────

class LifestyleDietForm(FlaskForm):
    """Step 2 – Dietary habits, physical exercise, and sleep routine."""

    # Nutrition & Hydration
    diet_type = SelectField(
        "Diet Type",
        choices=[
            ("", "Select Diet Type"), ("Vegetarian", "Vegetarian"),
            ("Non-Vegetarian", "Non-Vegetarian"),
            ("Vegan", "Vegan"), ("Pescatarian", "Pescatarian"),
            ("Keto", "Keto"), ("Mixed", "Mixed")
        ],
        validators=[DataRequired(message="Please select your primary diet type.")]
    )
    meals_per_day = IntegerField(
        "Number of Meals per Day",
        validators=[
            DataRequired(message="Please enter the number of meals per day."),
            NumberRange(min=1, max=10, message="Meals per day must be between 1 and 10.")
        ]
    )
    water_intake_L = FloatField(
        "Daily Water Intake (litres)",
        validators=[
            DataRequired(message="Please enter your daily water intake."),
            NumberRange(min=0, max=20, message="Water intake must be between 0 and 20 litres.")
        ]
    )
    fast_food_per_week = IntegerField(
        "Fast Food Meals per Week",
        validators=[
            DataRequired(message="Please enter fast food meals per week."),
            NumberRange(min=0, max=21, message="Fast food meals per week must be between 0 and 21.")
        ]
    )
    sugar_intake = SelectField(
        "Daily Sugar Intake Level",
        choices=[("", "Select Sugar Intake"), ("Low", "Low"), ("Moderate", "Moderate"), ("High", "High")],
        validators=[DataRequired(message="Please select your daily sugar intake level.")]
    )
    fruit_veg_servings = IntegerField(
        "Fruit & Vegetable Servings per Day",
        validators=[
            DataRequired(message="Please enter fruit and vegetable servings per day."),
            NumberRange(min=0, max=20, message="Servings must be between 0 and 20 per day.")
        ]
    )

    # Physical Activity & Daily Routine
    exercise_frequency = SelectField(
        "Exercise Frequency",
        choices=[
            ("", "Select Exercise Frequency"), ("Never", "Never"),
            ("1-2x per week", "1-2x per week"),
            ("3-4x per week", "3-4x per week"),
            ("5+ times per week", "5+ times per week")
        ],
        validators=[DataRequired(message="Please select your exercise frequency.")]
    )
    exercise_type = StringField(
        "Primary Exercise Type (e.g. Walking, Gym, Yoga)",
        validators=[Optional(), Length(max=100, message="Exercise type cannot exceed 100 characters.")]
    )
    exercise_duration_min = IntegerField(
        "Exercise Duration per Session (minutes)",
        validators=[
            Optional(),
            NumberRange(min=0, max=480, message="Exercise duration must be between 0 and 480 minutes.")
        ]
    )
    daily_steps = IntegerField(
        "Average Daily Steps",
        validators=[
            Optional(),
            NumberRange(min=0, max=100000, message="Daily steps must be between 0 and 100,000.")
        ]
    )
    sleep_hours = FloatField(
        "Average Sleep Hours per Night",
        validators=[
            DataRequired(message="Please enter your average sleep hours."),
            NumberRange(min=0, max=24, message="Sleep hours must be between 0 and 24 hours.")
        ]
    )
    screen_time_hours = FloatField(
        "Daily Screen Time (hours)",
        validators=[
            Optional(),
            NumberRange(min=0, max=24, message="Screen time must be between 0 and 24 hours.")
        ]
    )
    travel_frequency = SelectField(
        "Travel Frequency",
        choices=[
            ("", "Select Travel Frequency"), ("Rarely", "Rarely"),
            ("Weekly", "Weekly"), ("Daily", "Daily")
        ],
        validators=[Optional()]
    )

    submit = SubmitField("Next: Medical & Family →")


# ── Step 3: Medical Background & Genetics ────────────────────────────────────

class MedicalHistoryForm(FlaskForm):
    """Step 3 – Personal clinical history and family hereditary risks."""

    # Personal Medical History
    existing_diseases = TextAreaField(
        "Existing Diseases (comma-separated, or 'None')",
        validators=[Optional(), Length(max=500, message="Diseases description cannot exceed 500 characters.")]
    )
    current_medications = TextAreaField(
        "Current Medications (comma-separated, or 'None')",
        validators=[Optional(), Length(max=500, message="Medications description cannot exceed 500 characters.")]
    )
    vaccination_status = SelectField(
        "Vaccination Status",
        choices=[
            ("", "Select Vaccination Status"), ("Up to date", "Up to date"),
            ("Partially vaccinated", "Partially vaccinated"),
            ("Not vaccinated", "Not vaccinated"),
            ("Unknown", "Unknown")
        ],
        validators=[Optional()]
    )

    # Family Genetics / History
    family_diabetes       = BooleanField("Diabetes in family")
    family_heart_disease  = BooleanField("Heart disease in family")
    family_stroke         = BooleanField("Stroke in family")
    family_hypertension   = BooleanField("Hypertension in family")
    family_obesity        = BooleanField("Obesity in family")
    family_kidney_disease = BooleanField("Kidney disease in family")
    family_cancer         = BooleanField("Cancer in family")
    family_thyroid        = BooleanField("Thyroid disease in family")
    family_depression     = BooleanField("Depression / mental illness in family")

    submit = SubmitField("Next: Mind & Wellness →")


# ── Step 4: Mental Well-being, Habits & Submission ───────────────────────────

class MentalHealthForm(FlaskForm):
    """Step 4 – Habits, stress, mental well-being and final submission."""

    # Habits & Stressors
    stress_level = IntegerField(
        "Stress Level (1 = Low, 10 = High)",
        validators=[
            DataRequired(message="Please rate your stress level from 1 to 10."),
            NumberRange(min=1, max=10, message="Stress level must be between 1 and 10.")
        ]
    )
    smoking_status = SelectField(
        "Smoking Status",
        choices=[
            ("", "Select Smoking Status"), ("Never", "Never"),
            ("Former", "Former Smoker"), ("Current", "Current Smoker")
        ],
        validators=[DataRequired(message="Please select your smoking status.")]
    )
    cigarettes_per_day = IntegerField(
        "Times Smoked per Day",
        validators=[
            Optional(),
            NumberRange(min=1, max=100, message="Please enter a valid number of times smoked per day (1–100).")
        ]
    )

    def validate_smoking_status(self, field):
        if field.data == "Current":
            cigs = self.cigarettes_per_day.data
            if cigs is None or cigs < 1:
                msg = "As a current smoker, please enter the number of times you smoke in a day."
                self.cigarettes_per_day.errors = list(self.cigarettes_per_day.errors) + [msg]
                raise ValidationError(msg)

    alcohol_intake = SelectField(
        "Alcohol Intake",
        choices=[
            ("", "Select Alcohol Intake"), ("None", "None"),
            ("Occasional", "Occasional (1-2/week)"),
            ("Moderate", "Moderate (3-5/week)"),
            ("Heavy", "Heavy (Daily)")
        ],
        validators=[DataRequired(message="Please select your alcohol intake level.")]
    )

    # Mental Well-being
    depression_symptoms   = BooleanField("I experience frequent low mood / depression symptoms")
    anxiety_symptoms      = BooleanField("I experience frequent anxiety or panic attacks")
    mental_health_support = BooleanField("I am currently receiving mental health support")
    meditation_yoga = SelectField(
        "Meditation / Yoga Practice",
        choices=[
            ("", "Select Practice Frequency"), ("Never", "Never"),
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

    submit = SubmitField("Analyze My Health 🚀")


# Backward-compatibility aliases if imported elsewhere
LifestyleForm = LifestyleDietForm
FoodHabitsForm = LifestyleDietForm
ExerciseForm = LifestyleDietForm
FamilyHistoryForm = MedicalHistoryForm
