"""
routes/api_mobile.py - Mobile API Blueprint
=============================================
Dedicated JSON REST API for the Android APK.
Secured with JWT (Flask-JWT-Extended).
Exempted from Flask-WTF CSRF.
"""

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)
from extensions import db, jwt
from models.user import User
from models.prediction import Prediction

api_mobile_bp = Blueprint("api_mobile", __name__)


# ── JWT Error Handlers ─────────────────────────────────────────────────────

@jwt.unauthorized_loader
def unauthorized_callback(callback):
    return jsonify({
        "success": False,
        "error": {
            "code": "MISSING_AUTHORIZATION",
            "message": "Missing Authorization header."
        }
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({
        "success": False,
        "error": {
            "code": "INVALID_TOKEN",
            "message": "Invalid or malformed Bearer token."
        }
    }), 401

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({
        "success": False,
        "error": {
            "code": "TOKEN_EXPIRED",
            "message": "Your session has expired. Please log in again."
        }
    }), 401


# ── Endpoints ─────────────────────────────────────────────────────────────

@api_mobile_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for the mobile app to verify connectivity."""
    return jsonify({
        "status": "ok",
        "service": "mobile-api",
        "version": "1.0"
    })


@api_mobile_bp.route("/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json() or {}

    required_fields = ["full_name", "email", "password", "age", "gender"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": f"Missing required fields: {', '.join(missing)}"
            }
        }), 400

    email = data.get("email").lower().strip()

    if User.query.filter_by(email=email).first():
        return jsonify({
            "success": False,
            "error": {
                "code": "DUPLICATE_ACCOUNT",
                "message": "An account with this email address already exists."
            }
        }), 409

    user = User(
        full_name=data.get("full_name").strip(),
        age=data.get("age"),
        gender=data.get("gender"),
        height_cm=data.get("height_cm"),
        weight_kg=data.get("weight_kg"),
        email=email,
        is_email_verified=True # Auto-verify for mobile demo
    )
    user.password = data.get("password")

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Registration successful",
        "user": user.to_dict()
    }), 201


@api_mobile_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user and return a JWT access token."""
    data = request.get_json() or {}
    email = data.get("email", "").lower().strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Email and password are required."
            }
        }), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.verify_password(password):
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid email address or password."
            }
        }), 401

    if not user.is_active or user.is_deleted:
        return jsonify({
            "success": False,
            "error": {
                "code": "ACCOUNT_DISABLED",
                "message": "Your account has been disabled."
            }
        }), 403

    # Create the token using user.id as identity
    access_token = create_access_token(identity=str(user.id))

    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "success": True,
        "access_token": access_token,
        "token_type": "Bearer",
        "user": user.to_dict()
    }), 200


@api_mobile_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Return the currently authenticated user's profile."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.is_deleted:
        return jsonify({
            "success": False,
            "error": {
                "code": "USER_NOT_FOUND",
                "message": "User account no longer exists."
            }
        }), 401

    return jsonify({
        "success": True,
        "user": user.to_dict()
    }), 200

@api_mobile_bp.route("/predict", methods=["POST"])
@jwt_required()
def predict():
    """Run full disease risk prediction pipeline from mobile JSON payload."""
    import time
    start_time = time.time()

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "error": {"code": "USER_NOT_FOUND", "message": "User not found"}}), 401

    data = request.get_json() or {}

    # ── 1. Validation ──
    # Based exactly on the Questionnaire ORM schema
    try:
        age = int(data.get("age", 0))
        if not (18 <= age <= 120):
            raise ValueError("Age must be between 18 and 120")

        gender = str(data.get("gender", "")).strip().title()
        if gender not in ("Male", "Female", "Other"):
            raise ValueError("Gender must be Male, Female, or Other")

        height_cm = float(data.get("height_cm", 0))
        weight_kg = float(data.get("weight_kg", 0))
        if height_cm <= 0 or weight_kg <= 0:
            raise ValueError("Height and weight must be positive")

        bmi = round(weight_kg / ((height_cm / 100) ** 2), 2)
    except (ValueError, TypeError) as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid questionnaire data",
                "details": str(e)
            }
        }), 400

    # ── 2. Create Questionnaire ──
    from models.questionnaire import Questionnaire
    q = Questionnaire(
        user_id=user.id,
        age=age,
        gender=gender,
        height_cm=height_cm,
        weight_kg=weight_kg,
        bmi=bmi,
        occupation=data.get("occupation"),
        working_hours_per_day=data.get("working_hours_per_day") or 8.0,
        smoking_status=data.get("smoking_status") or "Never",
        cigarettes_per_day=data.get("cigarettes_per_day") or 0,
        alcohol_intake=data.get("alcohol_intake") or "None",
        sleep_hours=data.get("sleep_hours") or 7.0,
        screen_time_hours=data.get("screen_time_hours") or 4.0,
        stress_level=data.get("stress_level") or 5,
        travel_frequency=data.get("travel_frequency") or "Rarely",
        diet_type=data.get("diet_type") or "Mixed",
        meals_per_day=data.get("meals_per_day") or 3,
        water_intake_L=data.get("water_intake_L") or 2.0,
        fast_food_per_week=data.get("fast_food_per_week") or 1,
        sugar_intake=data.get("sugar_intake") or "Moderate",
        fruit_veg_servings=data.get("fruit_veg_servings") or 3,
        exercise_frequency=data.get("exercise_frequency") or "1-2x per week",
        exercise_type=data.get("exercise_type") or "Walking",
        exercise_duration_min=data.get("exercise_duration_min") or 20,
        heart_rate_resting=data.get("heart_rate_resting") or 72,
        existing_diseases=data.get("existing_diseases") or "",
        current_medications=data.get("current_medications") or "",
        blood_pressure_systolic=data.get("blood_pressure_systolic") or 120,
        blood_pressure_diastolic=data.get("blood_pressure_diastolic") or 80,
        blood_sugar_fasting=data.get("blood_sugar_fasting") or 95.0,
        cholesterol_level=data.get("cholesterol_level") or 190.0,
        vaccination_status=data.get("vaccination_status") or "",
        family_diabetes=bool(data.get("family_diabetes")),
        family_heart_disease=bool(data.get("family_heart_disease")),
        family_stroke=bool(data.get("family_stroke")),
        family_hypertension=bool(data.get("family_hypertension")),
        family_obesity=bool(data.get("family_obesity")),
        family_kidney_disease=bool(data.get("family_kidney_disease")),
        family_cancer=bool(data.get("family_cancer")),
        family_thyroid=bool(data.get("family_thyroid")),
        family_depression=bool(data.get("family_depression")),
        depression_symptoms=bool(data.get("depression_symptoms")),
        anxiety_symptoms=bool(data.get("anxiety_symptoms")),
        mental_health_support=bool(data.get("mental_health_support")),
        meditation_yoga=data.get("meditation_yoga") or "Never",
        pregnancy_status=data.get("pregnancy_status") or "N/A",
        daily_steps=data.get("daily_steps") or 5000,
        is_complete=True
    )
    db.session.add(q)
    db.session.commit()

    # ── 3. Run Prediction Service (reuses web flow) ──
    from flask import current_app
    from services.prediction_service import PredictionService

    pred_start = time.time()
    service = PredictionService(current_app._get_current_object())
    prediction = service.run_prediction(q)
    db.session.commit()
    pred_end = time.time()

    # ── 4. Generate Additional Explanations (LIME) ──
    from ml.lime_explainer import LimeExplainer

    expl_start = time.time()
    features = q.to_feature_dict()
    try:
        lime_res = LimeExplainer.explain_instance(features)
    except Exception as e:
        current_app.logger.error(f"LIME Error: {e}")
        lime_res = {"error": "LIME generation failed"}
    expl_end = time.time()

    # ── 5. Assemble JSON Response ──
    total_time = time.time() - start_time

    return jsonify({
        "success": True,
        "prediction_id": prediction.id,
        "results": {
            "health_scores": prediction.health_scores,
            "risks": prediction.disease_risks
        },
        "explanations": {
            "shap": {
                "positive_factors": prediction.get_top_positive_factors(),
                "negative_factors": prediction.get_top_negative_factors()
            },
            "lime": lime_res
        },
        "model_info": {
            "name": prediction.model_name,
            "version": prediction.model_version
        },
        "performance_ms": {
            "prediction": round((pred_end - pred_start) * 1000, 1),
            "explanation": round((expl_end - expl_start) * 1000, 1),
            "total": round(total_time * 1000, 1)
        }
    }), 200


# ── Phase 4: History, Dashboard, Tracker & Reports ──────────────────────────

@api_mobile_bp.route("/history", methods=["GET"])
@jwt_required()
def mobile_history():
    user_id = get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    paginated = Prediction.query.filter_by(user_id=user_id).order_by(Prediction.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    predictions_data = []
    for p in paginated.items:
        predictions_data.append({
            "id": p.id,
            "created_at": p.created_at.isoformat(),
            "health_score": p.overall_health_score,
            "summary": {
                "top_risks": [k for k, v in p.disease_risks.items() if v.get("risk_level") in ["High", "Medium"]][:3]
            }
        })

    return jsonify({
        "success": True,
        "page": paginated.page,
        "per_page": paginated.per_page,
        "total": paginated.total,
        "predictions": predictions_data
    })


@api_mobile_bp.route("/history/<int:prediction_id>", methods=["GET"])
@jwt_required()
def mobile_history_detail(prediction_id):
    user_id = get_jwt_identity()
    pred = Prediction.query.filter_by(id=prediction_id, user_id=user_id).first()
    if not pred:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Prediction not found"}}), 404

    return jsonify({
        "success": True,
        "results": {
            "health_score": pred.health_scores,
            "risks": pred.disease_risks
        },
        "explanations": {
            "shap": {
                "positive_factors": pred.get_top_positive_factors(),
                "negative_factors": pred.get_top_negative_factors()
            }
        },
        "model_info": {
            "name": pred.model_name,
            "version": pred.model_version
        }
    })


@api_mobile_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def mobile_dashboard():
    user_id = get_jwt_identity()
    recent_predictions = Prediction.query.filter_by(user_id=user_id).order_by(Prediction.created_at.desc()).limit(5).all()
    latest = recent_predictions[0] if recent_predictions else None

    if not latest:
        return jsonify({"success": True, "summary": None, "trends": None, "recent_predictions": []})

    trend_data = [{"date": p.created_at.strftime("%Y-%m-%d"), "health_score": p.overall_health_score} for p in reversed(recent_predictions)]

    return jsonify({
        "success": True,
        "summary": {
            "latest_health_score": latest.overall_health_score,
            "latest_prediction_date": latest.created_at.isoformat(),
            "risk_summary": {k: v for k, v in latest.disease_risks.items() if v.get("risk_level") in ["High", "Medium"]}
        },
        "trends": trend_data,
        "recent_predictions": [{"id": p.id, "date": p.created_at.isoformat(), "score": p.overall_health_score} for p in recent_predictions]
    })


@api_mobile_bp.route("/health-score", methods=["GET"])
@jwt_required()
def mobile_health_score():
    user_id = get_jwt_identity()
    pred = Prediction.query.filter_by(user_id=user_id).order_by(Prediction.created_at.desc()).first()
    if not pred:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "No predictions found"}}), 404
    return jsonify({"success": True, "data": pred.health_scores})


@api_mobile_bp.route("/disease-risks", methods=["GET"])
@jwt_required()
def mobile_disease_risks():
    user_id = get_jwt_identity()
    pred = Prediction.query.filter_by(user_id=user_id).order_by(Prediction.created_at.desc()).first()
    if not pred:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "No predictions found"}}), 404
    return jsonify({"success": True, "data": pred.disease_risks})


@api_mobile_bp.route("/history/trend", methods=["GET"])
@jwt_required()
def mobile_history_trend():
    user_id = get_jwt_identity()
    n = min(request.args.get("n", 7, type=int), 50)
    predictions = Prediction.query.filter_by(user_id=user_id).order_by(Prediction.created_at.desc()).limit(n).all()

    data = [{"date": p.created_at.strftime("%Y-%m-%d"), "health_score": p.overall_health_score} for p in reversed(predictions)]
    return jsonify({"success": True, "points": data})


@api_mobile_bp.route("/tracker/log", methods=["POST"])
@jwt_required()
def mobile_tracker_log_post():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    from models.daily_health_log import DailyHealthLog
    from datetime import date

    try:
        target_date_str = data.get("log_date", date.today().isoformat())
        target_date = date.fromisoformat(target_date_str)

        existing = DailyHealthLog.query.filter_by(user_id=user_id, log_date=target_date).first()
        if existing:
            return jsonify({"success": False, "error": {"code": "DUPLICATE", "message": "Log already exists for this date"}}), 400

        log = DailyHealthLog(
            user_id=user_id,
            log_date=target_date,
            sleep_hours=float(data.get("sleep_hours") or 7.0),
            sleep_quality=int(data.get("sleep_quality") or 3),
            water_intake=float(data.get("water_intake") or 2.0),
            exercise_minutes=int(data.get("exercise_minutes") or 0),
            steps=int(data.get("steps") or 5000),
            workout_type=data.get("workout_type"),
            breakfast=bool(data.get("breakfast")),
            lunch=bool(data.get("lunch")),
            dinner=bool(data.get("dinner")),
            fruits=int(data.get("fruits") or 0),
            vegetables=int(data.get("vegetables") or 0),
            junk_food=bool(data.get("junk_food")),
            sugary_drinks=bool(data.get("sugary_drinks")),
            smoking=bool(data.get("smoking")),
            alcohol=bool(data.get("alcohol")),
            tobacco=bool(data.get("tobacco")),
            stress_level=int(data.get("stress_level") or 5),
            mood=int(data.get("mood") or 3),
            anxiety_level=data.get("anxiety_level"),
            weight=float(data.get("weight") or 70.0),
            blood_pressure=data.get("blood_pressure"),
            blood_sugar=data.get("blood_sugar"),
            heart_rate=data.get("heart_rate")
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({"success": True, "log": log.to_dict()})

    except Exception as e:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}}), 400


@api_mobile_bp.route("/tracker/logs", methods=["GET"])
@jwt_required()
def mobile_tracker_logs():
    user_id = get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 30)
    days = min(request.args.get("days", 30, type=int), 90)

    from datetime import date, timedelta
    cutoff = date.today() - timedelta(days=days)

    from models.daily_health_log import DailyHealthLog
    paginated = DailyHealthLog.query.filter(
        DailyHealthLog.user_id == user_id,
        DailyHealthLog.log_date >= cutoff
    ).order_by(DailyHealthLog.log_date.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "success": True,
        "data": [log.to_dict() for log in paginated.items],
        "total": paginated.total,
        "page": paginated.page,
        "pages": paginated.pages
    })


@api_mobile_bp.route("/tracker/stats", methods=["GET"])
@jwt_required()
def mobile_tracker_stats():
    user_id = get_jwt_identity()
    from services.tracker_service import TrackerService
    service = TrackerService(current_app._get_current_object())
    return jsonify({
        "success": True,
        "weekly": service.get_weekly_stats(user_id),
        "monthly": service.get_monthly_stats(user_id)
    })


@api_mobile_bp.route("/reports/<int:prediction_id>/pdf", methods=["GET"])
@jwt_required()
def mobile_report_pdf(prediction_id):
    user_id = get_jwt_identity()
    pred = Prediction.query.filter_by(id=prediction_id, user_id=user_id).first()
    if not pred:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Prediction not found"}}), 404

    from models.user import User
    user = User.query.get(user_id)

    import io
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=22, textColor=colors.HexColor("#6C63FF"), spaceAfter=6)
    heading2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=14, textColor=colors.HexColor("#4ecdc4"), spaceBefore=14, spaceAfter=6)
    normal = styles["Normal"]

    story = []
    story.append(Paragraph("🩺 HealthAI – Prediction Report", title_style))
    story.append(Paragraph(f"<b>User:</b> {user.full_name} &nbsp;|&nbsp; <b>Email:</b> {user.email} &nbsp;|&nbsp; <b>Date:</b> {pred.created_at.strftime('%B %d, %Y')}", normal))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#6C63FF")))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("Disease Risks", heading2))
    risk_data = [["Disease", "Probability", "Risk Level"]]
    for disease, info in pred.disease_risks.items():
        risk_data.append([disease.replace("_", " ").title(), f"{info.get('probability', 0):.1f}%", info.get("risk_level", "-")])

    if len(risk_data) > 1:
        tbl = Table(risk_data, colWidths=[6*cm, 4*cm, 4*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4ecdc4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0ffff")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ]))
        story.append(tbl)

    doc.build(story)
    pdf_bytes = buf.getvalue()

    from flask import send_file
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"prediction_report_{prediction_id}.pdf"
    )
