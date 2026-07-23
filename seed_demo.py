"""seed_demo.py - ASCII-safe version for Windows console"""
import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from app import create_app, db
from models import User, Questionnaire, Prediction, Recommendation, Report, ModelLog, Admin

app = create_app('development')

with app.app_context():
    db.create_all()

    if not User.query.filter_by(email='demo@healthai.com').first():
        u = User(
            full_name='Alex Johnson', age=34, gender='Male',
            height_cm=175.0, weight_kg=88.0,
            email='demo@healthai.com', is_email_verified=True
        )
        u.password = 'Demo@1234'
        db.session.add(u)
        db.session.commit()

        q = Questionnaire(
            user_id=u.id, age=34, gender='Male',
            height_cm=175.0, weight_kg=88.0, bmi=28.7,
            occupation='Software Engineer', working_hours_per_day=9.0,
            smoking_status='Former', alcohol_intake='Moderate',
            sleep_hours=6.0, screen_time_hours=8.0, stress_level=7,
            diet_type='Non-Vegetarian', meals_per_day=3,
            water_intake_L=1.8, fast_food_per_week=4,
            sugar_intake='High', fruit_veg_servings=2,
            exercise_frequency='1-2x per week', exercise_duration_min=30,
            heart_rate_resting=78,
            blood_pressure_systolic=135, blood_pressure_diastolic=88,
            blood_sugar_fasting=105.0, cholesterol_level=215.0,
            family_diabetes=True, family_heart_disease=True,
            family_hypertension=True,
            depression_symptoms=False, anxiety_symptoms=True,
            meditation_yoga='Sometimes', daily_steps=4500,
            is_complete=True
        )
        db.session.add(q)
        db.session.commit()

        from services.prediction_service import PredictionService
        svc = PredictionService(app)
        pred = svc.run_prediction(q)
        db.session.commit()
        print("DEMO USER CREATED")
        print("Email   : " + u.email)
        print("Password: Demo@1234")
        print("Pred ID : " + str(pred.id))
    else:
        u = User.query.filter_by(email='demo@healthai.com').first()
        pred = u.predictions.order_by(Prediction.created_at.desc()).first()
        print("EXISTING DEMO USER")

    print("\n--- DISEASE RISKS ---")
    for disease, data in pred.disease_risks.items():
        pct = data['probability']
        lvl = data['risk_level']
        bar = '#' * int(pct / 5)
        print(f"  {disease:<20} {pct:>5.1f}%  {lvl}")

    print("\n--- HEALTH SCORES ---")
    for label, val in pred.health_scores.items():
        print(f"  {label:<16} {val:>5.1f}")

    recs = pred.recommendations.all()
    print(f"\n--- RECOMMENDATIONS ({len(recs)}) ---")
    for r in recs:
        print(f"  [{r.category}] {r.title}")

    print("\n--- DATABASE TABLE COUNTS ---")
    print(f"  users           : {User.query.count()}")
    print(f"  admins          : {Admin.query.count()}")
    print(f"  questionnaires  : {Questionnaire.query.count()}")
    print(f"  predictions     : {Prediction.query.count()}")
    print(f"  recommendations : {Recommendation.query.count()}")
    print(f"  reports         : {Report.query.count()}")
    print(f"  model_logs      : {ModelLog.query.count()}")
    print("\nAll systems OK!")
