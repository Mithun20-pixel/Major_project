"""
routes/predict.py - Prediction Blueprint (4-Step Streamlined Wizard)
===================================================================
Handles: Consolidated 4-step health questionnaire, ML risk prediction trigger, Result display.
"""

from flask import (
    Blueprint, render_template, redirect,
    url_for, flash, request, jsonify, current_app
)
from flask_login import login_required, current_user

from extensions import db
from models.questionnaire  import Questionnaire
from models.prediction     import Prediction
from forms.questionnaire   import (
    PersonalInfoForm,
    LifestyleDietForm,
    MedicalHistoryForm,
    MentalHealthForm
)
from services.prediction_service import PredictionService

predict_bp = Blueprint("predict", __name__, template_folder="../templates/predict")


# ── Step 1: Personal Profile & Vitals ────────────────────────────────────────

@predict_bp.route("/step/1", methods=["GET", "POST"])
@predict_bp.route("/step/1/<int:qid>", methods=["GET", "POST"])
@login_required
def step1(qid: int = None):
    """Questionnaire step 1 – Personal demographics & baseline physical vitals."""
    q = _get_questionnaire_or_abort(qid) if qid else None
    form = PersonalInfoForm(obj=q if (q and request.method == "GET") else None)
    if request.method == "GET" and not q:
        if current_user.is_authenticated:
            if getattr(current_user, "age", None) and not form.age.data:
                form.age.data = current_user.age
            if getattr(current_user, "gender", None) and not form.gender.data:
                form.gender.data = current_user.gender
            if getattr(current_user, "height_cm", None) and not form.height_cm.data:
                form.height_cm.data = current_user.height_cm
            if getattr(current_user, "weight_kg", None) and not form.weight_kg.data:
                form.weight_kg.data = current_user.weight_kg

    if form.validate_on_submit():
        if not q:
            # Create a new questionnaire session
            q = Questionnaire(
                user_id                  = current_user.id,
                age                      = form.age.data,
                gender                   = form.gender.data,
                height_cm                = form.height_cm.data,
                weight_kg                = form.weight_kg.data,
                occupation               = form.occupation.data,
                working_hours_per_day    = form.working_hours_per_day.data,
                blood_pressure_systolic  = form.blood_pressure_systolic.data,
                blood_pressure_diastolic = form.blood_pressure_diastolic.data,
                blood_sugar_fasting      = form.blood_sugar_fasting.data,
                cholesterol_level        = form.cholesterol_level.data,
                heart_rate_resting       = form.heart_rate_resting.data,
            )
            db.session.add(q)
        else:
            q.age                      = form.age.data
            q.gender                   = form.gender.data
            q.height_cm                = form.height_cm.data
            q.weight_kg                = form.weight_kg.data
            q.occupation               = form.occupation.data
            q.working_hours_per_day    = form.working_hours_per_day.data
            q.blood_pressure_systolic  = form.blood_pressure_systolic.data
            q.blood_pressure_diastolic = form.blood_pressure_diastolic.data
            q.blood_sugar_fasting      = form.blood_sugar_fasting.data
            q.cholesterol_level        = form.cholesterol_level.data
            q.heart_rate_resting       = form.heart_rate_resting.data

        db.session.commit()
        return redirect(url_for("predict.step2", qid=q.id))

    return render_template("predict/step1.html", form=form, step=1, total_steps=4, qid=qid)


# ── Step 2: Daily Lifestyle, Nutrition & Activity ────────────────────────────

@predict_bp.route("/step/2/<int:qid>", methods=["GET", "POST"])
@login_required
def step2(qid: int):
    """Questionnaire step 2 – Dietary habits, physical exercise, and sleep routine."""
    q = _get_questionnaire_or_abort(qid)

    # Server-side step enforcement: Ensure Step 1 mandatory vitals & demographics exist
    if (q.age is None or q.gender is None or q.blood_pressure_systolic is None or
            q.blood_pressure_diastolic is None or q.blood_sugar_fasting is None or
            q.cholesterol_level is None or q.heart_rate_resting is None):
        flash("Please complete all mandatory profile & vital fields in Step 1 first.", "warning")
        return redirect(url_for("predict.step1", qid=qid))

    form = LifestyleDietForm(obj=q if request.method == "GET" else None)
    if form.validate_on_submit():
        # Nutrition & Hydration
        q.diet_type          = form.diet_type.data
        q.meals_per_day      = form.meals_per_day.data
        q.water_intake_L     = form.water_intake_L.data
        q.fast_food_per_week = form.fast_food_per_week.data
        q.sugar_intake       = form.sugar_intake.data
        q.fruit_veg_servings = form.fruit_veg_servings.data

        # Activity & Sleep
        q.exercise_frequency    = form.exercise_frequency.data
        q.exercise_type         = form.exercise_type.data
        q.exercise_duration_min = form.exercise_duration_min.data
        q.daily_steps           = form.daily_steps.data
        q.sleep_hours           = form.sleep_hours.data
        q.screen_time_hours     = form.screen_time_hours.data
        q.travel_frequency      = form.travel_frequency.data

        db.session.commit()
        return redirect(url_for("predict.step3", qid=qid))

    return render_template("predict/step2.html", form=form, step=2, total_steps=4, qid=qid)


# ── Step 3: Medical Background & Genetics ────────────────────────────────────

@predict_bp.route("/step/3/<int:qid>", methods=["GET", "POST"])
@login_required
def step3(qid: int):
    """Questionnaire step 3 – Personal medical history & family genetics."""
    q = _get_questionnaire_or_abort(qid)

    # Server-side step enforcement: Ensure Step 2 is completed
    if (q.diet_type is None or q.meals_per_day is None or q.water_intake_L is None or
            q.exercise_frequency is None or q.sleep_hours is None):
        flash("Please complete all mandatory fields in Step 2 first.", "warning")
        return redirect(url_for("predict.step2", qid=qid))

    form = MedicalHistoryForm(obj=q if request.method == "GET" else None)
    if form.validate_on_submit():
        # Personal Medical History
        q.existing_diseases   = form.existing_diseases.data
        q.current_medications = form.current_medications.data
        q.vaccination_status  = form.vaccination_status.data

        # Family Genetics
        q.family_diabetes       = form.family_diabetes.data
        q.family_heart_disease  = form.family_heart_disease.data
        q.family_stroke         = form.family_stroke.data
        q.family_hypertension   = form.family_hypertension.data
        q.family_obesity        = form.family_obesity.data
        q.family_kidney_disease = form.family_kidney_disease.data
        q.family_cancer         = form.family_cancer.data
        q.family_thyroid        = form.family_thyroid.data
        q.family_depression     = form.family_depression.data

        db.session.commit()
        return redirect(url_for("predict.step4", qid=qid))

    return render_template("predict/step3.html", form=form, step=3, total_steps=4, qid=qid)


# ── Step 4: Mental Well-being, Habits & Submission ───────────────────────────

@predict_bp.route("/step/4/<int:qid>", methods=["GET", "POST"])
@login_required
def step4(qid: int):
    """Questionnaire step 4 – Habits, stress, mental well-being and final submission."""
    q = _get_questionnaire_or_abort(qid)

    # Server-side step enforcement
    if q.blood_pressure_systolic is None:
        flash("Please complete Step 1 first.", "warning")
        return redirect(url_for("predict.step1", qid=qid))
    if q.diet_type is None:
        flash("Please complete Step 2 first.", "warning")
        return redirect(url_for("predict.step2", qid=qid))

    is_female = (q.gender == "Female")
    form = MentalHealthForm(obj=q if request.method == "GET" else None)
    if not is_female:
        form.pregnancy_status.data = "N/A"

    if form.validate_on_submit():
        # Habits & Stress
        q.stress_level      = form.stress_level.data
        q.smoking_status    = form.smoking_status.data
        q.cigarettes_per_day = form.cigarettes_per_day.data if form.smoking_status.data == "Current" else None
        q.alcohol_intake    = form.alcohol_intake.data

        # Mental Well-being
        q.depression_symptoms   = form.depression_symptoms.data
        q.anxiety_symptoms      = form.anxiety_symptoms.data
        q.mental_health_support = form.mental_health_support.data
        q.meditation_yoga       = form.meditation_yoga.data
        q.pregnancy_status      = form.pregnancy_status.data if is_female else "N/A"
        q.is_complete           = True

        # Compute BMI and store on questionnaire
        if q.height_cm and q.weight_kg:
            h = q.height_cm / 100
            q.bmi = round(q.weight_kg / (h ** 2), 2)

        db.session.commit()

        # Trigger prediction service
        service = PredictionService(current_app._get_current_object())
        prediction = service.run_prediction(q)
        db.session.commit()

        # Log activity
        from utils.activity_tracker import log_user_activity
        log_user_activity(current_user, "Ran Risk Prediction", f"Completed disease risk prediction (ID #{prediction.id})")

        flash("Analysis complete! Your results are ready.", "success")
        return redirect(url_for("predict.results", prediction_id=prediction.id))

    return render_template("predict/step4.html", form=form, step=4, total_steps=4, qid=qid, is_female=is_female)


# ── Backwards compatibility redirects for steps 5, 6, 7 ────────────────────

@predict_bp.route("/step/5/<int:qid>", methods=["GET", "POST"])
@predict_bp.route("/step/6/<int:qid>", methods=["GET", "POST"])
@predict_bp.route("/step/7/<int:qid>", methods=["GET", "POST"])
@login_required
def legacy_steps(qid: int):
    """Graceful redirect for any legacy links to consolidated Step 4."""
    return redirect(url_for("predict.step4", qid=qid))


# ── Results ────────────────────────────────────────────────────────────────

@predict_bp.route("/results/<int:prediction_id>")
@login_required
def results(prediction_id: int):
    """
    Display the full prediction results:
    - Disease risk cards
    - SHAP / LIME visualisations
    - Health scores
    - Recommendations
    """
    prediction = Prediction.query.filter_by(
        id=prediction_id, user_id=current_user.id
    ).first_or_404()

    recommendations = (
        prediction.recommendations
        .order_by("priority")
        .all()
    )

    return render_template(
        "predict/results.html",
        prediction=prediction,
        disease_risks=prediction.disease_risks,
        health_scores=prediction.health_scores,
        recommendations=recommendations,
        positive_factors=prediction.get_top_positive_factors(),
        negative_factors=prediction.get_top_negative_factors(),
    )


# ── Private helpers ────────────────────────────────────────────────────────

def _get_questionnaire_or_abort(qid: int) -> Questionnaire:
    """
    Fetch the questionnaire by ID and verify ownership.
    Aborts with 403/404 if the questionnaire does not belong to the current user.
    """
    q = Questionnaire.query.filter_by(
        id=qid, user_id=current_user.id
    ).first_or_404()
    return q
