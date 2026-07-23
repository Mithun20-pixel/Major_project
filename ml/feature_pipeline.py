"""
ml/feature_pipeline.py - Feature Extraction & Preprocessing Pipeline
=====================================================================
Transforms questionnaire and daily log data into standardized numerical
feature vectors for ML models, SHAP explainers, and LIME explainers.
"""

from typing import Dict, Any, List, Tuple
import math

# Baseline population expectations E[f(x)] for baseline SHAP calculations
BASE_POPULATION_EXPECTATIONS = {
    "age": 42.0,
    "bmi": 24.5,
    "sleep_hours": 7.2,
    "water_intake_L": 2.2,
    "exercise_duration_min": 25.0,
    "daily_steps": 6500.0,
    "stress_level": 4.5,
    "fruit_veg_servings": 4.0,
    "fast_food_per_week": 2.0,
    "smoking_active": 0.0,
    "alcohol_heavy": 0.0,
    "family_history_score": 0.5,
    "blood_pressure_systolic": 120.0,
    "blood_sugar_fasting": 95.0,
}

FEATURE_NAMES = list(BASE_POPULATION_EXPECTATIONS.keys())


class FeaturePipeline:
    """
    Standardizes raw lifestyle dicts (from Questionnaire or DailyHealthLog)
    into clean numerical feature vectors suitable for ML & XAI explainers.
    """

    @staticmethod
    def extract_features(raw_dict: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract numerical features from raw dictionary.

        Args:
            raw_dict: Raw input dict from questionnaire or merged log features.

        Returns:
            Dict mapping standardized feature name -> float value.
        """
        features = {}

        # 1. Age
        features["age"] = float(raw_dict.get("age", 35))

        # 2. BMI
        bmi = raw_dict.get("bmi")
        if bmi is None and raw_dict.get("weight_kg") and raw_dict.get("height_cm"):
            h_m = float(raw_dict["height_cm"]) / 100.0
            if h_m > 0:
                bmi = float(raw_dict["weight_kg"]) / (h_m ** 2)
        features["bmi"] = float(bmi if bmi else (raw_dict.get("weight", 24.5) or 24.5))

        # 3. Sleep
        features["sleep_hours"] = float(raw_dict.get("sleep_hours", 7.0))

        # 4. Water
        features["water_intake_L"] = float(
            raw_dict.get("water_intake_L", raw_dict.get("water_intake", 2.0))
        )

        # 5. Exercise
        ex_min = raw_dict.get("exercise_duration_min", raw_dict.get("exercise_minutes"))
        if ex_min is None:
            freq = raw_dict.get("exercise_frequency", "Never")
            freq_map = {
                "Never": 0.0,
                "1-2x per week": 15.0,
                "3-4x per week": 40.0,
                "5+ times per week": 60.0,
            }
            ex_min = freq_map.get(freq, 20.0)
        features["exercise_duration_min"] = float(ex_min)

        # 6. Steps
        features["daily_steps"] = float(raw_dict.get("daily_steps", raw_dict.get("steps", 5000)))

        # 7. Stress Level
        features["stress_level"] = float(raw_dict.get("stress_level", 5))

        # 8. Fruits & Vegetables
        fv = raw_dict.get("fruit_veg_servings")
        if fv is None:
            fv = (raw_dict.get("fruits", 0) or 0) + (raw_dict.get("vegetables", 0) or 0)
        features["fruit_veg_servings"] = float(fv)

        # 9. Fast / Junk Food
        ff = raw_dict.get("fast_food_per_week")
        if ff is None:
            ff = 7.0 if raw_dict.get("junk_food") else 1.0
        features["fast_food_per_week"] = float(ff)

        # 10. Smoking status
        smk = raw_dict.get("smoking_status")
        if smk is None:
            smk_val = 1.0 if raw_dict.get("smoking") else 0.0
        else:
            smk_val = 1.0 if smk == "Current" else 0.0
        features["smoking_active"] = float(smk_val)

        # 11. Alcohol
        alc = raw_dict.get("alcohol_intake")
        if alc is None:
            alc_val = 1.0 if raw_dict.get("alcohol") else 0.0
        else:
            alc_val = 1.0 if alc in ("Heavy", "Moderate") else 0.0
        features["alcohol_heavy"] = float(alc_val)

        # 12. Family History Score
        fam_score = 0.0
        for key in ["family_diabetes", "family_heart_disease", "family_stroke", "family_hypertension"]:
            if raw_dict.get(key):
                fam_score += 0.5
        features["family_history_score"] = float(fam_score)

        # 13. Blood Pressure
        bp_sys = raw_dict.get("blood_pressure_systolic")
        if bp_sys is None and raw_dict.get("blood_pressure"):
            try:
                bp_sys = float(raw_dict["blood_pressure"].split("/")[0])
            except Exception:
                bp_sys = 120.0
        features["blood_pressure_systolic"] = float(bp_sys if bp_sys else 120.0)

        # 14. Blood Sugar Fasting
        features["blood_sugar_fasting"] = float(
            raw_dict.get("blood_sugar_fasting", raw_dict.get("blood_sugar", 95.0)) or 95.0
        )

        return features
