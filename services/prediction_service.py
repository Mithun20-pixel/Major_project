"""
services/prediction_service.py - Prediction Orchestrator (Phase 1 Stub)
=========================================================================
This service stub wires the questionnaire → ML pipeline → Prediction model.
In Phase 1, it generates deterministic placeholder predictions.
The real ML model calls will be integrated in Phase 3.

Phase 3 (Tracker) Note:
    _predict_diseases() and _calculate_health_scores() are intentionally
    kept as regular instance methods but are also aliased as
    predict_diseases() and calculate_health_scores() so that
    TrackerService can call them without needing a full questionnaire.
"""

import random
import json
from datetime import datetime
from flask import Flask

from extensions import db
from models.questionnaire  import Questionnaire
from models.prediction     import Prediction
from models.recommendation import Recommendation
from ml.predictor import MLPredictor
from ml.shap_explainer import ShapExplainer
from ml.lifestyle_analytics import LifestyleAnalytics


class PredictionService:
    """
    Orchestrates the full prediction workflow:
      1. Extract features from Questionnaire.
      2. Call ML models for each disease.
      3. Generate SHAP/LIME explanations.
      4. Calculate health scores.
      5. Persist Prediction to database.
      6. Generate Recommendations.
    """

    DISEASES = [
        "diabetes", "heart_disease", "stroke",
        "hypertension", "obesity", "kidney_disease",
        "fatty_liver", "depression", "sleep_disorder", "thyroid",
    ]

    def __init__(self, app: Flask):
        """
        Args:
            app: The Flask application instance (for config access).
        """
        self.app = app

    def run_prediction(self, questionnaire: Questionnaire) -> Prediction:
        """
        Main entry point. Runs the full prediction pipeline.

        Args:
            questionnaire: A completed Questionnaire ORM instance.

        Returns:
            A persisted Prediction ORM instance.
        """
        features = questionnaire.to_feature_dict()

        # ── Step 1: Get disease probabilities ─────────────────────────────
        probabilities = self._predict_diseases(features)

        # ── Step 2: Calculate health scores ───────────────────────────────
        health_scores = self._calculate_health_scores(features)

        # ── Step 3: Gather SHAP top factors ───────────────────────────────
        positive_factors, negative_factors = self._get_top_factors(features)

        # ── Step 4: Persist Prediction ─────────────────────────────────────
        prediction = Prediction(
            user_id          = questionnaire.user_id,
            questionnaire_id = questionnaire.id,
            # Disease probabilities
            diabetes_prob       = probabilities["diabetes"],
            heart_disease_prob  = probabilities["heart_disease"],
            stroke_prob         = probabilities["stroke"],
            hypertension_prob   = probabilities["hypertension"],
            obesity_prob        = probabilities["obesity"],
            kidney_disease_prob = probabilities["kidney_disease"],
            fatty_liver_prob    = probabilities["fatty_liver"],
            depression_prob     = probabilities["depression"],
            sleep_disorder_prob = probabilities["sleep_disorder"],
            thyroid_prob        = probabilities["thyroid"],
            # Health scores
            overall_health_score = health_scores["Overall"],
            lifestyle_score      = health_scores["Lifestyle"],
            fitness_score        = health_scores["Fitness"],
            diet_score           = health_scores["Diet"],
            mental_health_score  = health_scores["Mental Health"],
            sleep_score          = health_scores["Sleep"],
            hydration_score      = health_scores["Hydration"],
            exercise_score       = health_scores["Exercise"],
            # SHAP factors
            top_positive_factors = json.dumps(positive_factors),
            top_negative_factors = json.dumps(negative_factors),
            # Model metadata
            model_version = "v3.0-XAI",
            model_name    = MLPredictor.predict_diabetes_detailed(features).get("model_type", "basic"),
        )
        db.session.add(prediction)
        db.session.flush()   # get prediction.id before commit

        # ── Step 5: Generate Recommendations ──────────────────────────────
        self._generate_recommendations(prediction, probabilities, features)

        return prediction

    # ── Private helpers ────────────────────────────────────────────────────

    def _predict_diseases(self, features: dict) -> dict:
        """
        Compute disease probabilities using calibrated ML prediction models.

        Args:
            features: Dict of feature name → value from questionnaire.

        Returns:
            Dict mapping disease key → probability (0.0–100.0).
        """
        probabilities = {}
        for disease in self.DISEASES:
            prob = MLPredictor.predict_disease(disease, features)
            probabilities[disease] = prob
        return probabilities

    # ── Public aliases (used by TrackerService) ────────────────────────────

    def predict_diseases(self, features: dict) -> dict:
        """
        Public wrapper around _predict_diseases for external callers
        (e.g. TrackerService) that need disease probabilities without
        running the full prediction pipeline.

        Args:
            features: Feature dict in the same format as Questionnaire.to_feature_dict().

        Returns:
            Dict mapping disease key → probability (0.0–100.0).
        """
        return self._predict_diseases(features)

    def calculate_health_scores(self, features: dict) -> dict:
        """
        Public wrapper around _calculate_health_scores for external callers.

        Args:
            features: Feature dict in the same format as Questionnaire.to_feature_dict().

        Returns:
            Dict mapping score dimension → float (0–100).
        """
        return self._calculate_health_scores(features)

    def _calculate_health_scores(self, features: dict) -> dict:
        """
        Compute multi-dimensional health scores (0–100).

        Args:
            features: Questionnaire feature dict.

        Returns:
            Dict mapping score dimension → float (0–100).
        """
        # Sleep score (7–9 hours is optimal)
        sleep = features.get("sleep_hours") or 6
        sleep_score = max(0, min(100, 100 - abs(sleep - 8) * 12.5))

        # Hydration score (2.5 L is optimal for adults)
        water = features.get("water_intake_L") or 1.5
        hydration_score = max(0, min(100, (water / 3.0) * 100))

        # Exercise score
        ex_map = {
            "Never":           10,
            "1-2x per week":   40,
            "3-4x per week":   75,
            "5+ times per week": 100,
        }
        exercise_score = ex_map.get(features.get("exercise_frequency"), 20)

        # Diet score
        diet_score = 60
        if features.get("fruit_veg_servings"):
            diet_score += min(20, features["fruit_veg_servings"] * 4)
        if features.get("fast_food_per_week"):
            diet_score -= min(30, features["fast_food_per_week"] * 5)
        if features.get("sugar_intake") == "High":
            diet_score -= 15
        diet_score = max(0, min(100, diet_score))

        # Mental health score
        mental_score = 80
        if features.get("depression_symptoms"):  mental_score -= 25
        if features.get("anxiety_symptoms"):     mental_score -= 15
        if (features.get("stress_level") or 5) >= 8: mental_score -= 20
        mental_score = max(0, min(100, mental_score))

        # Lifestyle score
        lifestyle_score = 70
        if features.get("smoking_status") == "Current":
            cigs = features.get("cigarettes_per_day") or 0
            if cigs >= 20:
                lifestyle_score -= 30
            elif cigs >= 10:
                lifestyle_score -= 25
            else:
                lifestyle_score -= 20
        if features.get("alcohol_intake") == "Heavy":   lifestyle_score -= 15
        if (features.get("screen_time_hours") or 0) >= 8: lifestyle_score -= 10
        lifestyle_score = max(0, min(100, lifestyle_score))

        # Fitness score (BMI + exercise + steps)
        bmi = features.get("bmi") or 25
        fitness_score = 70
        if 18.5 <= bmi <= 24.9: fitness_score += 15
        elif bmi >= 30:          fitness_score -= 20
        fitness_score += (exercise_score - 50) * 0.3
        fitness_score = max(0, min(100, fitness_score))

        # Overall = weighted average
        overall = (
            lifestyle_score * 0.20 +
            fitness_score   * 0.20 +
            diet_score      * 0.20 +
            mental_score    * 0.15 +
            sleep_score     * 0.10 +
            hydration_score * 0.05 +
            exercise_score  * 0.10
        )

        return {
            "Overall":      round(overall, 1),
            "Lifestyle":    round(lifestyle_score, 1),
            "Fitness":      round(fitness_score, 1),
            "Diet":         round(diet_score, 1),
            "Mental Health": round(mental_score, 1),
            "Sleep":        round(sleep_score, 1),
            "Hydration":    round(hydration_score, 1),
            "Exercise":     round(exercise_score, 1),
        }

    def _get_top_factors(self, features: dict) -> tuple[list, list]:
        """
        Identify the top positive and negative lifestyle factors using SHAP explanations.

        Returns:
            Tuple of (positive_factors list, negative_factors list).
            Each item is a dict with keys: {feature, value, impact, description}.
        """
        shap_res = ShapExplainer.calculate_shap_values("heart_disease", features)
        positive = []
        negative = []

        for d in shap_res.get("negative_drivers", []):  # negative risk impact = protective factor
            positive.append({
                "feature": d["feature"],
                "value": str(d["val"]),
                "impact": "+high" if d["phi"] < -2.0 else "+medium",
                "description": f"Protective factor (lowers risk by {abs(d['phi'])}%).",
            })

        for d in shap_res.get("positive_drivers", []):  # positive risk impact = risk driver
            negative.append({
                "feature": d["feature"],
                "value": str(d["val"]),
                "impact": "-high" if d["phi"] > 2.0 else "-medium",
                "description": f"Elevates disease risk by +{d['phi']}%.",
            })

        # Fallbacks if SHAP drivers are sparse
        if not positive:
            if features.get("exercise_frequency") in ("3-4x per week", "5+ times per week"):
                positive.append({
                    "feature": "Exercise Frequency",
                    "value": str(features["exercise_frequency"]),
                    "impact": "+high",
                    "description": "Regular physical activity supports overall cardiovascular health.",
                })
            if (features.get("sleep_hours") or 0) >= 7:
                positive.append({
                    "feature": "Sleep Duration",
                    "value": f"{features['sleep_hours']} hrs",
                    "impact": "+medium",
                    "description": "Adequate sleep promotes heart and metabolic health.",
                })

        if not negative:
            if features.get("smoking_status") == "Current":
                negative.append({
                    "feature": "Smoking",
                    "value": "Current Smoker",
                    "impact": "-high",
                    "description": "Smoking elevates vascular and heart risk.",
                })
            if (features.get("stress_level") or 0) >= 7:
                negative.append({
                    "feature": "Stress Level",
                    "value": f"{features['stress_level']}/10",
                    "impact": "-medium",
                    "description": "Elevated stress increases cortisol and blood pressure.",
                })

        return positive[:5], negative[:5]

    def _generate_recommendations(
        self, prediction: Prediction, probabilities: dict, features: dict
    ) -> None:
        """
        Create personalised Recommendation rows based on prediction results.

        Args:
            prediction:    The Prediction ORM instance (already flushed).
            probabilities: Dict of disease → probability.
            features:      Questionnaire feature dict.
        """
        recs = []

        # Exercise recommendation
        if features.get("exercise_frequency") in ("Never", "1-2x per week"):
            recs.append(Recommendation(
                prediction_id  = prediction.id,
                user_id        = prediction.user_id,
                category       = "exercise",
                title          = "Increase Physical Activity",
                description    = (
                    "Aim for at least 150 minutes of moderate aerobic exercise per week. "
                    "Start with brisk walking for 30 minutes, 5 days a week."
                ),
                priority       = 1,
                icon           = "bi-bicycle",
                related_disease= "Heart Disease, Obesity, Diabetes",
            ))

        # Diet recommendation
        if features.get("fast_food_per_week") and features["fast_food_per_week"] >= 4:
            recs.append(Recommendation(
                prediction_id  = prediction.id,
                user_id        = prediction.user_id,
                category       = "diet",
                title          = "Reduce Fast Food Consumption",
                description    = (
                    "Limit fast food to 1 meal per week. Prepare home-cooked meals "
                    "with whole grains, lean proteins, and vegetables."
                ),
                priority       = 2,
                icon           = "bi-egg-fried",
                related_disease= "Obesity, Fatty Liver, Diabetes",
            ))

        # Hydration recommendation
        if (features.get("water_intake_L") or 0) < 2.0:
            recs.append(Recommendation(
                prediction_id  = prediction.id,
                user_id        = prediction.user_id,
                category       = "hydration",
                title          = "Improve Daily Water Intake",
                description    = (
                    "Aim to drink at least 2.5–3 litres of water per day. "
                    "Carry a water bottle and set hourly reminders."
                ),
                priority       = 3,
                icon           = "bi-droplet",
                related_disease= "Kidney Disease, General Health",
            ))

        # Sleep recommendation
        if (features.get("sleep_hours") or 7) < 6:
            recs.append(Recommendation(
                prediction_id  = prediction.id,
                user_id        = prediction.user_id,
                category       = "sleep",
                title          = "Improve Sleep Quality and Duration",
                description    = (
                    "Target 7–9 hours of sleep nightly. Maintain a consistent "
                    "sleep schedule and limit screen time 1 hour before bed."
                ),
                priority       = 2,
                icon           = "bi-moon-stars",
                related_disease= "Sleep Disorder, Depression, Heart Disease",
            ))

        # Smoking cessation
        if features.get("smoking_status") == "Current":
            cigs = features.get("cigarettes_per_day")
            freq_str = f"You recorded smoking {cigs} time(s) a day. " if cigs else ""
            recs.append(Recommendation(
                prediction_id  = prediction.id,
                user_id        = prediction.user_id,
                category       = "smoking_cessation",
                title          = "Quit Smoking – Consult a Doctor",
                description    = (
                    f"{freq_str}Smoking is the single largest modifiable risk factor for cardiovascular "
                    "disease. Consult your doctor for nicotine replacement therapy or medication."
                ),
                priority       = 1,
                icon           = "bi-x-circle",
                related_disease= "Heart Disease, Stroke, Lung Disease",
            ))

        # Medical consultation for high-risk diseases
        high_risk = [d for d, p in probabilities.items() if p >= 67]
        if high_risk:
            disease_names = ", ".join(d.replace("_", " ").title() for d in high_risk)
            recs.append(Recommendation(
                prediction_id  = prediction.id,
                user_id        = prediction.user_id,
                category       = "medical",
                title          = "Schedule a Medical Consultation",
                description    = (
                    f"You show elevated risk for: {disease_names}. "
                    "Please consult a healthcare professional for proper clinical evaluation."
                ),
                priority       = 1,
                icon           = "bi-hospital",
                related_disease= disease_names,
            ))

        # Population Peer Benchmark recommendation (from health_lifestyle_dataset.csv)
        benchmarks = LifestyleAnalytics.get_peer_benchmarks(
            age=int(features.get("age", 35) or 35),
            gender=str(features.get("gender", "Female"))
        )
        if benchmarks and benchmarks.get("sample_size"):
            sleep_gap = round(benchmarks.get("avg_sleep_hours", 7.0) - (features.get("sleep_hours") or 7.0), 1)
            if sleep_gap > 0.5:
                recs.append(Recommendation(
                    prediction_id  = prediction.id,
                    user_id        = prediction.user_id,
                    category       = "lifestyle_benchmark",
                    title          = "Peer Health Benchmark Comparison",
                    description    = (
                        f"Based on 571 real-world survey respondents, individuals in your age group "
                        f"average {benchmarks.get('avg_sleep_hours')} hours of sleep. You log {features.get('sleep_hours')} hours "
                        f"({sleep_gap} hrs less than peers). Increasing sleep can improve metabolic resilience."
                    ),
                    priority       = 3,
                    icon           = "bi-people-fill",
                    related_disease= "General Health, Sleep Disorder",
                ))

        db.session.add_all(recs)
