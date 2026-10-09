"""
ml/predictor.py - ML Prediction & XAI Inference Engine
======================================================
Unified ML predictor that runs disease risk inference using trained, calibrated
machine learning models (Random Forest / CalibratedClassifierCV), computes SHAP
values, and generates LIME explanations.
"""

import os
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd

from ml.feature_pipeline import FeaturePipeline, FEATURE_NAMES
from ml.shap_explainer import ShapExplainer
from ml.lime_explainer import LimeExplainer

SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")

_MODEL_CACHE = {}
_SCALER_CACHE = None


def _get_scaler():
    global _SCALER_CACHE
    if _SCALER_CACHE is None:
        scaler_path = os.path.join(SAVED_MODELS_DIR, "scaler.joblib")
        if os.path.exists(scaler_path):
            try:
                import joblib
                _SCALER_CACHE = joblib.load(scaler_path)
            except Exception as e:
                print(f"[MLPredictor] Warning loading scaler: {e}")
    return _SCALER_CACHE


def _get_model(disease: str):
    global _MODEL_CACHE
    if disease not in _MODEL_CACHE:
        model_path = os.path.join(SAVED_MODELS_DIR, f"{disease}_model.joblib")
        if os.path.exists(model_path):
            try:
                import joblib
                _MODEL_CACHE[disease] = joblib.load(model_path)
            except Exception as e:
                print(f"[MLPredictor] Warning loading model for {disease}: {e}")
                _MODEL_CACHE[disease] = None
        else:
            _MODEL_CACHE[disease] = None
    return _MODEL_CACHE[disease]


def _is_valid_numeric(val: Any, min_val: float, max_val: float) -> bool:
    """Validate whether a value is numeric, non-empty, and within acceptable physiological range."""
    if val is None:
        return False
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str or val_str.lower() in ("none", "null", "nan", ""):
            return False
        try:
            num = float(val_str)
        except ValueError:
            return False
    elif isinstance(val, (int, float)):
        if np.isnan(val):
            return False
        num = float(val)
    else:
        return False
    return min_val <= num <= max_val


def _validate_gender(val: Any) -> Tuple[bool, str]:
    """
    Validate and normalize gender input.
    Returns (is_valid: bool, normalized_gender: str).
    Accepted valid values: 'Male', 'Female', 'Other' (or 'm', 'f').
    Rejects invalid/unknown strings instead of silently defaulting.
    """
    if val is None:
        return False, ""
    val_str = str(val).strip().lower()
    if val_str in ("male", "m", "1"):
        return True, "Male"
    if val_str in ("female", "f", "0"):
        return True, "Female"
    if val_str in ("other", "o"):
        return True, "Other"
    return False, ""


def _extract_personal_hypertension(raw_features: Dict[str, Any], bp_val: Optional[float] = None) -> str:
    """
    Extract user's PERSONAL hypertension status ('Yes' / 'No').
    CRITICAL RULE: family_hypertension = True MUST NOT produce personal Hypertension = 'Yes'.
    
    Personal Hypertension is positive ONLY if:
    1. Measured blood_pressure_systolic >= 140 mmHg.
    2. 'existing_diseases' explicitly contains 'hypertension' or 'high blood pressure'.
    3. 'current_medications' explicitly mentions anti-hypertensive medication keywords.

    SEMANTIC DEFINITION:
    Hypertension = 'No' means 'No reported or detected evidence of personal hypertension
    from the available questionnaire data' and NOT 'A medically confirmed absence of hypertension'.
    """
    # 1. Check measured systolic BP
    if bp_val is not None and bp_val >= 140.0:
        return "Yes"

    sys_bp_raw = raw_features.get("blood_pressure_systolic")
    if _is_valid_numeric(sys_bp_raw, 60.0, 250.0):
        if float(sys_bp_raw) >= 140.0:
            return "Yes"

    # 2. Check existing diseases text
    diseases_text = str(raw_features.get("existing_diseases") or "").lower()
    if any(k in diseases_text for k in ["hypertension", "high blood pressure", "high bp"]):
        return "Yes"

    # 3. Check current medications text
    meds_text = str(raw_features.get("current_medications") or "").lower()
    htn_med_keywords = ["amlodipine", "lisinopril", "losartan", "atenolol", "metoprolol", "bp med", "hypertension"]
    if any(k in meds_text for k in htn_med_keywords):
        return "Yes"

    # CRITICAL: Do NOT use family_hypertension as a substitute for personal hypertension!
    return "No"


_DIABETES_MODELS = {}

def _get_diabetes_pipeline(model_key: str):
    """
    Safely load a diabetes pipeline ('basic', 'enhanced', 'clinical').
    Cached in _DIABETES_MODELS dict.
    """
    global _DIABETES_MODELS
    if model_key not in _DIABETES_MODELS:
        filename = f"diabetes_{model_key}_model.joblib"
        model_path = os.path.join(SAVED_MODELS_DIR, filename)
        if os.path.exists(model_path):
            try:
                import joblib
                _DIABETES_MODELS[model_key] = joblib.load(model_path)
            except Exception as e:
                print(f"[MLPredictor] Error loading {filename}: {e}")
                _DIABETES_MODELS[model_key] = None
        else:
            _DIABETES_MODELS[model_key] = None
    return _DIABETES_MODELS[model_key]


class MLPredictor:
    """
    Core Machine Learning & XAI Predictor.
    Executes disease risk prediction models and attached XAI explainers.
    """

    DISEASES = [
        "diabetes", "heart_disease", "stroke",
        "hypertension", "obesity", "kidney_disease",
        "fatty_liver", "depression", "sleep_disorder", "thyroid",
    ]

    @classmethod
    def predict_disease(cls, disease: str, raw_features: Dict[str, Any]) -> float:
        """
        Predict calibrated disease probability (0.0 to 100.0) for a given disease.
        """
        disease_key = disease.lower().replace(" ", "_")
        
        # Route to multi-tier diabetes model if diabetes
        if disease_key == "diabetes":
            detailed = cls.predict_diabetes_detailed(raw_features)
            return detailed.get("probability", 15.0)

        norm_features = FeaturePipeline.extract_features(raw_features)

        # DataFrame preserving column names
        df_feat = pd.DataFrame([norm_features])[FEATURE_NAMES]

        model = _get_model(disease_key)
        scaler = _get_scaler()

        if model is not None and scaler is not None:
            try:
                X_scaled = scaler.transform(df_feat)
                prob = float(model.predict_proba(X_scaled)[0, 1]) * 100.0
                return round(max(3.0, min(95.0, prob)), 1)
            except Exception as e:
                print(f"[MLPredictor] Error during inference for {disease}: {e}")

        # Clinically calibrated fallback if models are not yet loaded
        return cls._calibrated_fallback(disease_key, norm_features)

    @classmethod
    def predict_diabetes_detailed(cls, raw_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safe multi-tier diabetes prediction routing:
        - Validates whether optional clinical vitals (Glucose, BP, Cholesterol) are genuinely available.
        - Routes to Model A+ (Enhanced) if ALL 3 enhanced vitals are valid.
        - Otherwise routes to Model A (Basic Self-Reported).
        - Returns dict with probability, predicted_class, model_type, model_display_name, disclaimer.
        """
        # Validate gender strictly (no silent default to Female)
        is_gender_valid, gender_val = _validate_gender(raw_features.get("gender"))
        if not is_gender_valid:
            return {
                "error": "Invalid or missing gender attribute. Accepted values: Male, Female, Other.",
                "model_type": "validation_error",
                "model_display_name": "Validation Error",
                "probability": 15.0
            }

        norm = FeaturePipeline.extract_features(raw_features)

        # Check enhanced clinical vitals validity
        glucose_valid = _is_valid_numeric(raw_features.get("blood_sugar_fasting"), 40.0, 300.0)
        bp_valid = _is_valid_numeric(raw_features.get("blood_pressure_systolic"), 60.0, 250.0)
        chol_valid = _is_valid_numeric(raw_features.get("cholesterol_level"), 80.0, 500.0)

        use_enhanced = glucose_valid and bp_valid and chol_valid

        # Extract common self-reported features
        age_val = float(raw_features.get("age", norm.get("age", 40.0)) or 40.0)
        bmi_val = float(norm.get("bmi", 24.5))

        act_raw = raw_features.get("exercise_frequency", "1-2x per week")
        act_val = "Low" if act_raw == "Never" else ("High" if act_raw == "5+ times per week" else "Moderate")

        smk_raw = raw_features.get("smoking_status", "Never")
        smk_val = "Current" if smk_raw == "Current" else ("Former" if smk_raw == "Former" else "Never")

        alc_raw = raw_features.get("alcohol_intake", "None")
        alc_val = "Regular" if alc_raw == "Heavy" else ("Occasional" if alc_raw in ("Occasional", "Moderate") else "Missing")

        fam_diab = "Yes" if raw_features.get("family_diabetes") else "No"

        if use_enhanced:
            model_enhanced = _get_diabetes_pipeline("enhanced")
            if model_enhanced is not None:
                try:
                    glucose_val = float(raw_features["blood_sugar_fasting"])
                    bp_val = float(raw_features["blood_pressure_systolic"])
                    chol_val = float(raw_features["cholesterol_level"])
                    
                    # Extract PERSONAL hypertension status (NOT family_hypertension)
                    htn_val = _extract_personal_hypertension(raw_features, bp_val)

                    df_feat = pd.DataFrame([{
                        "Gender": gender_val,
                        "Physical Activity": act_val,
                        "Smoking Status": smk_val,
                        "Alcohol Intake": alc_val,
                        "Family History": fam_diab,
                        "Hypertension": htn_val,
                        "Age": age_val,
                        "BMI": bmi_val,
                        "Glucose": glucose_val,
                        "Blood Pressure": bp_val,
                        "Cholesterol": chol_val,
                    }])

                    prob = float(model_enhanced.predict_proba(df_feat)[0, 1]) * 100.0
                    prob = round(max(3.0, min(95.0, prob)), 1)
                    return {
                        "probability": prob,
                        "predicted_class": "Diabetic" if prob >= 50.0 else "Non-diabetic",
                        "model_type": "enhanced",
                        "model_display_name": "Enhanced Diabetes Risk Assessment",
                        "disclaimer": "Includes validated fasting blood sugar, blood pressure, and cholesterol vitals.",
                        "used_features": list(df_feat.columns)
                    }
                except Exception as e:
                    print(f"[MLPredictor] Model A+ prediction error, falling back to Model A: {e}")

        # Fallback / Default: Model A (Basic Self-Reported)
        model_basic = _get_diabetes_pipeline("basic")
        if model_basic is not None:
            try:
                df_feat = pd.DataFrame([{
                    "Gender": gender_val,
                    "Physical Activity": act_val,
                    "Smoking Status": smk_val,
                    "Alcohol Intake": alc_val,
                    "Family History": fam_diab,
                    "Age": age_val,
                    "BMI": bmi_val,
                }])

                prob = float(model_basic.predict_proba(df_feat)[0, 1]) * 100.0
                prob = round(max(3.0, min(95.0, prob)), 1)
                return {
                    "probability": prob,
                    "predicted_class": "Diabetic" if prob >= 50.0 else "Non-diabetic",
                    "model_type": "basic",
                    "model_display_name": "Lifestyle-Based Diabetes Risk Indicator",
                    "disclaimer": "This estimate is based on self-reported demographic and lifestyle information and should not be interpreted as a clinical diagnosis.",
                    "used_features": list(df_feat.columns)
                }
            except Exception as e:
                print(f"[MLPredictor] Model A prediction error: {e}")

        # Clinically calibrated fallback if models are not loaded
        fallback_prob = cls._calibrated_fallback("diabetes", norm)
        return {
            "probability": fallback_prob,
            "predicted_class": "Diabetic" if fallback_prob >= 50.0 else "Non-diabetic",
            "model_type": "fallback",
            "model_display_name": "Epidemiological Diabetes Risk Fallback",
            "disclaimer": "Logistic epidemiological fallback calculation.",
            "used_features": list(norm.keys())
        }

    @classmethod
    def predict_diabetes_clinical(cls, raw_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Model B — Full Clinical Diabetes Prediction method.
        Requires all 14 genuine clinical features.
        Rejects missing or default values. Not called by standard questionnaire.
        """
        # Validate gender strictly
        is_gender_valid, gender_val = _validate_gender(raw_features.get("gender", raw_features.get("Gender")))
        if not is_gender_valid:
            return {
                "error": "Invalid or missing gender attribute. Accepted values: Male, Female, Other.",
                "model_type": "clinical",
                "model_display_name": "Clinical Diabetes Risk Assessment"
            }

        required_cols = [
            "Gender", "Physical Activity", "Smoking Status", "Alcohol Intake",
            "Family History", "Hypertension", "Age", "BMI", "Glucose",
            "Blood Pressure", "Skin Thickness", "Insulin", "Cholesterol",
            "Diabetes Pedigree Function"
        ]

        missing = []
        for col in required_cols:
            if col not in raw_features or raw_features[col] is None or str(raw_features[col]).strip() == "":
                missing.append(col)

        if missing:
            return {
                "error": "Missing required clinical features",
                "missing_features": missing,
                "model_type": "clinical",
                "model_display_name": "Clinical Diabetes Risk Assessment"
            }

        model_clinical = _get_diabetes_pipeline("clinical")
        if model_clinical is None:
            return {
                "error": "Clinical model binary not available",
                "model_type": "clinical",
                "model_display_name": "Clinical Diabetes Risk Assessment"
            }

        try:
            # Copy raw features dict and ensure Gender is normalized
            clean_features = dict(raw_features)
            clean_features["Gender"] = gender_val

            df_feat = pd.DataFrame([clean_features])[required_cols]
            prob = float(model_clinical.predict_proba(df_feat)[0, 1]) * 100.0
            prob = round(max(3.0, min(95.0, prob)), 1)
            return {
                "probability": prob,
                "predicted_class": "Diabetic" if prob >= 50.0 else "Non-diabetic",
                "model_type": "clinical",
                "model_display_name": "Clinical Diabetes Risk Assessment",
                "disclaimer": "Full 14-feature clinical laboratory assessment.",
                "used_features": required_cols
            }
        except Exception as e:
            return {
                "error": f"Clinical prediction execution error: {e}",
                "model_type": "clinical",
                "model_display_name": "Clinical Diabetes Risk Assessment"
            }

    @classmethod
    def _calibrated_fallback(cls, disease_key: str, features: Dict[str, float]) -> float:
        """Clinically realistic logistic probability calculation for fallback."""
        def sigmoid(z):
            return 1.0 / (1.0 + np.exp(-z))

        age = features.get("age", 40.0)
        bmi = features.get("bmi", 24.5)
        bp_sys = features.get("blood_pressure_systolic", 120.0)
        fasting_sugar = features.get("blood_sugar_fasting", 95.0)
        smoking = features.get("smoking_active", 0.0)
        alcohol = features.get("alcohol_heavy", 0.0)
        exercise = features.get("exercise_duration_min", 25.0)
        stress = features.get("stress_level", 4.5)
        sleep = features.get("sleep_hours", 7.2)
        water = features.get("water_intake_L", 2.2)
        fam_score = features.get("family_history_score", 0.5)

        if disease_key == "diabetes":
            z = -2.0 + 0.08 * (bmi - 25) + 0.04 * (fasting_sugar - 100) + 0.6 * fam_score - 0.02 * exercise + 0.03 * (age - 40)
        elif disease_key == "heart_disease":
            z = -2.2 + 1.2 * smoking + 0.04 * (bp_sys - 120) + 0.05 * (bmi - 25) + 0.2 * stress + 0.8 * alcohol + 0.6 * fam_score - 0.025 * exercise
        elif disease_key == "stroke":
            z = -2.5 + 0.05 * (bp_sys - 120) + 1.2 * smoking + 0.04 * (age - 50) + 0.6 * fam_score + 0.7 * alcohol
        elif disease_key == "hypertension":
            z = -1.8 + 0.06 * (bp_sys - 120) + 0.2 * stress + 0.05 * (bmi - 25) + 0.8 * alcohol - 0.3 * water
        elif disease_key == "obesity":
            z = -1.5 + 0.45 * (bmi - 25) - 0.02 * exercise + 0.25 * (features.get("fast_food_per_week", 2.0)) - 0.15 * (features.get("fruit_veg_servings", 4.0))
        elif disease_key == "kidney_disease":
            z = -2.5 + 0.04 * (bp_sys - 120) + 0.03 * (fasting_sugar - 100) - 0.5 * water + 0.8 * smoking + 0.03 * (age - 45)
        elif disease_key == "fatty_liver":
            z = -2.0 + 0.16 * (bmi - 25) + 1.2 * alcohol + 0.25 * (features.get("fast_food_per_week", 2.0)) - 0.02 * exercise
        elif disease_key == "depression":
            z = -1.8 + 0.35 * stress - 0.4 * (sleep - 7) - 0.015 * exercise - 0.15 * (features.get("fruit_veg_servings", 4.0))
        elif disease_key == "sleep_disorder":
            z = -1.8 - 0.7 * (sleep - 7) + 0.25 * stress + 0.05 * (bmi - 25)
        elif disease_key == "thyroid":
            z = -2.2 + 0.15 * stress + 0.6 * fam_score + 0.02 * (age - 35)
        else:
            z = -2.0

        return round(max(3.0, min(95.0, sigmoid(z) * 100.0)), 1)

    @classmethod
    def predict_all(cls, raw_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run inference for all diseases and generate SHAP & LIME XAI explanations.

        Args:
            raw_features: Questionnaire or merged daily log features.

        Returns:
            Dict containing:
              - probabilities: {disease: prob}
              - shap_explanations: {disease: shap_dict}
              - lime_explanation: lime_dict
        """
        probabilities = {}
        shap_explanations = {}

        detailed_diabetes = cls.predict_diabetes_detailed(raw_features)

        for disease in cls.DISEASES:
            disease_key = disease.lower().replace(" ", "_")
            if disease_key == "diabetes":
                prob = detailed_diabetes.get("probability", 15.0)
                probabilities[disease] = prob
                shap_res = ShapExplainer.calculate_shap_values(
                    "diabetes", raw_features, target_prob=prob, detailed_diabetes=detailed_diabetes
                )
            else:
                prob = cls.predict_disease(disease, raw_features)
                probabilities[disease] = prob
                shap_res = ShapExplainer.calculate_shap_values(disease, raw_features, target_prob=prob)

            shap_explanations[disease] = shap_res

        lime_res = LimeExplainer.explain_instance(raw_features, detailed_diabetes=detailed_diabetes)

        return {
            "probabilities": probabilities,
            "shap_explanations": shap_explanations,
            "lime_explanation": lime_res,
        }
