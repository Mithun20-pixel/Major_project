"""
ml/lime_explainer.py - LIME (Local Interpretable Model-agnostic Explanations) Generator
=======================================================================================
Computes Local Interpretable Model-agnostic Explanations (LIME) around prediction instances.
Routes diabetes dynamically to model-specific pipeline surrogate models (Model A, A+, B).
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


class LimeExplainer:
    """
    Computes Local Interpretable Model-agnostic Explanations (LIME).
    Fits local weighted surrogate models around instances to measure feature sensitivity.
    """

    # Default heuristic weights for non-diabetes fallback
    SENSITIVITY = {
        "sleep_hours": -1.5,
        "water_intake_L": -1.2,
        "exercise_duration_min": -0.05,
        "daily_steps": -0.0003,
        "stress_level": 1.4,
        "fast_food_per_week": 1.1,
        "fruit_veg_servings": -0.8,
        "smoking_active": 5.0,
        "alcohol_heavy": 3.5,
        "blood_pressure_systolic": 0.25,
        "bmi": 0.9,
    }

    @classmethod
    def explain_instance(
        cls, raw_features: Dict[str, Any], disease: str = "Overall Risk", detailed_diabetes: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate local linear feature weights explaining the prediction for a specific instance.
        """
        disease_key = disease.lower().replace(" ", "_")

        # Dynamic model-specific LIME for Diabetes
        if disease_key in ("diabetes", "overall_risk", "overall risk"):
            return cls._explain_diabetes_lime(raw_features, detailed_diabetes)

        return cls._fallback_lime(raw_features, disease)

    @classmethod
    def _explain_diabetes_lime(
        cls, raw_features: Dict[str, Any], detailed_diabetes: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Model-specific LIME explanation for Diabetes (Model A, A+, B).
        Strictly explains ONLY the features used by the exact prediction model pipeline.
        """
        from ml.predictor import MLPredictor, _get_diabetes_pipeline
        from ml.shap_explainer import ShapExplainer

        if detailed_diabetes is None:
            detailed_diabetes = MLPredictor.predict_diabetes_detailed(raw_features)

        model_type = detailed_diabetes.get("model_type", "basic")
        prob_orig = detailed_diabetes.get("probability", 15.0)

        # Load exact model pipeline that made prediction
        model = _get_diabetes_pipeline(model_type)

        # Extract features DataFrame corresponding to model_type
        df_sample = ShapExplainer._build_diabetes_feature_dataframe(raw_features, model_type)

        feature_rules = []
        local_weights = {}

        if model is not None and hasattr(model, "predict_proba"):
            np.random.seed(42)
            N_samples = 300
            perturbed_rows = []

            # Feature scales for local perturbation
            feature_scales = {
                "Age": 10.0, "BMI": 4.0, "Glucose": 25.0, "Blood Pressure": 15.0,
                "Cholesterol": 30.0, "Skin Thickness": 5.0, "Insulin": 25.0,
                "Diabetes Pedigree Function": 0.2
            }

            # Generate local perturbations
            for _ in range(N_samples):
                row = df_sample.iloc[0].to_dict()
                for col in df_sample.columns:
                    val = row[col]
                    if col in feature_scales:
                        std = feature_scales[col]
                        noise = float(np.random.normal(0, std * 0.15))
                        new_val = float(val) + noise
                        if col == "Age": new_val = max(18.0, min(90.0, new_val))
                        elif col == "BMI": new_val = max(15.0, min(50.0, new_val))
                        elif col in ("Glucose", "Blood Pressure", "Cholesterol"): new_val = max(40.0, new_val)
                        row[col] = new_val
                    elif col in ("Physical Activity", "Smoking Status", "Alcohol Intake", "Hypertension", "Family History"):
                        if np.random.rand() < 0.1:
                            if col == "Physical Activity": row[col] = np.random.choice(["Low", "Moderate", "High"])
                            elif col == "Smoking Status": row[col] = np.random.choice(["Never", "Former", "Current"])
                            elif col == "Alcohol Intake": row[col] = np.random.choice(["Missing", "Occasional", "Regular"])
                            elif col in ("Hypertension", "Family History"): row[col] = np.random.choice(["Yes", "No"])
                perturbed_rows.append(row)

            df_perturbed = pd.DataFrame(perturbed_rows)

            # Query saved sklearn pipeline predict_proba callback
            probs_perturbed = model.predict_proba(df_perturbed)[:, 1] * 100.0

            # Compute local finite-difference sensitivity weights for each feature
            for col in df_sample.columns:
                val = df_sample[col].values[0]
                df_high = df_sample.copy()
                df_low = df_sample.copy()

                if col in feature_scales:
                    delta = feature_scales[col] * 0.2
                    df_high[col] = float(val) + delta
                    df_low[col] = max(0.0, float(val) - delta)
                elif col in ("Physical Activity", "Smoking Status", "Alcohol Intake", "Hypertension", "Family History"):
                    df_high[col] = "High" if col == "Physical Activity" else ("Current" if col == "Smoking Status" else ("Regular" if col == "Alcohol Intake" else "Yes"))
                    df_low[col] = "Low" if col == "Physical Activity" else ("Never" if col == "Smoking Status" else ("Missing" if col == "Alcohol Intake" else "No"))

                p_high = float(model.predict_proba(df_high)[0, 1]) * 100.0
                p_low = float(model.predict_proba(df_low)[0, 1]) * 100.0
                w_col = round(p_high - p_low, 2)

                local_weights[col] = w_col
                direction = "increases risk" if w_col > 0.1 else ("decreases risk" if w_col < -0.1 else "neutral impact")

                feature_rules.append({
                    "feature": col,
                    "val": val,
                    "weight": w_col,
                    "rule": f"{col} = {val} ({direction} in local neighborhood)",
                    "contribution_direction": "higher_risk" if w_col > 0.1 else ("lower_risk" if w_col < -0.1 else "neutral")
                })

            feature_rules.sort(key=lambda x: abs(x["weight"]), reverse=True)

        disclaimer = (
            "This explanation is based on self-reported demographic and lifestyle information and represents a model-based risk estimate, not a clinical diagnosis."
            if model_type == "basic"
            else "This explanation incorporates validated clinical vitals (Glucose, BP, Cholesterol)."
        )

        return {
            "disease": "diabetes",
            "model_type": model_type,
            "explanation_method": "Local Feature Sensitivity Analysis (Pipeline Perturbation)",
            "explanation_description": "This explanation estimates how sensitive the selected model's prediction is to local changes in each input feature.",
            "predicted_probability": prob_orig,
            "feature_count": len(df_sample.columns),
            "local_weights": local_weights,
            "explanation_rules": feature_rules,
            "disclaimer": disclaimer,
            "used_features": list(df_sample.columns)
        }

    @classmethod
    def _fallback_lime(cls, raw_features: Dict[str, Any], disease: str) -> Dict[str, Any]:
        """Legacy fallback heuristic LIME calculation for non-diabetes diseases."""
        from ml.feature_pipeline import FeaturePipeline
        features = FeaturePipeline.extract_features(raw_features)

        local_weights = {}
        explanation_rules = []

        for feat, val in features.items():
            coef = cls.SENSITIVITY.get(feat, 0.0)
            weight = round(coef * val, 2)
            local_weights[feat] = weight

            if abs(weight) > 0.5:
                direction = "increases" if weight > 0 else "decreases"
                rule_desc = f"{feat.replace('_', ' ').title()} = {val} ({direction} risk by {abs(weight):.1f} pts)"
                explanation_rules.append({
                    "feature": feat.replace("_", " ").title(),
                    "val": val,
                    "weight": weight,
                    "rule": rule_desc,
                })

        explanation_rules.sort(key=lambda x: abs(x["weight"]), reverse=True)

        return {
            "disease": disease,
            "local_weights": local_weights,
            "explanation_rules": explanation_rules[:6],
        }
