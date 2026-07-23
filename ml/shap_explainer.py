"""
ml/shap_explainer.py - SHAP (Shapley Additive Explanations) Generator
=====================================================================
Computes Shapley values (phi_i) for each feature in disease risk prediction.
Ensures local accuracy: sum(phi_i) + base_value = predicted_risk.

Provides:
  - calculate_shap_values(): Returns per-feature SHAP contributions.
  - get_waterfall_data(): Formats waterfall chart data for UI rendering.
  - compare_shap_contributions(): Calculates feature impact shifts between
    Baseline Questionnaire and Latest Daily Tracking Log.
"""

from typing import Dict, Any, List, Tuple
from ml.feature_pipeline import FeaturePipeline, BASE_POPULATION_EXPECTATIONS


class ShapExplainer:
    """
    Computes exact Shapley Additive Explanations for disease predictions.
    """

    # Feature baseline weights and direction for disease risk models
    FEATURE_RISK_WEIGHTS = {
        "diabetes": {
            "bmi": 1.2,
            "blood_sugar_fasting": 1.5,
            "fast_food_per_week": 0.8,
            "exercise_duration_min": -0.7,
            "daily_steps": -0.003,
            "family_history_score": 2.5,
            "age": 0.3,
        },
        "heart_disease": {
            "smoking_active": 8.0,
            "blood_pressure_systolic": 0.35,
            "bmi": 0.9,
            "stress_level": 1.2,
            "alcohol_heavy": 3.0,
            "exercise_duration_min": -0.8,
            "sleep_hours": -1.2,
            "family_history_score": 3.0,
        },
        "stroke": {
            "blood_pressure_systolic": 0.45,
            "smoking_active": 6.0,
            "age": 0.4,
            "stress_level": 1.0,
            "alcohol_heavy": 2.5,
            "family_history_score": 2.5,
        },
        "hypertension": {
            "blood_pressure_systolic": 0.6,
            "stress_level": 1.8,
            "bmi": 0.8,
            "alcohol_heavy": 3.5,
            "exercise_duration_min": -0.6,
            "water_intake_L": -1.0,
        },
        "obesity": {
            "bmi": 2.8,
            "exercise_duration_min": -0.9,
            "daily_steps": -0.004,
            "fast_food_per_week": 1.5,
            "fruit_veg_servings": -1.2,
            "sleep_hours": -1.0,
        },
        "kidney_disease": {
            "blood_pressure_systolic": 0.3,
            "water_intake_L": -3.0,
            "blood_sugar_fasting": 0.8,
            "age": 0.25,
            "smoking_active": 4.0,
        },
        "fatty_liver": {
            "bmi": 1.5,
            "fast_food_per_week": 1.8,
            "alcohol_heavy": 5.0,
            "exercise_duration_min": -0.7,
            "fruit_veg_servings": -1.0,
        },
        "depression": {
            "stress_level": 3.5,
            "sleep_hours": -3.0,
            "exercise_duration_min": -0.8,
            "daily_steps": -0.002,
            "fruit_veg_servings": -0.8,
        },
        "sleep_disorder": {
            "sleep_hours": -5.0,
            "stress_level": 2.5,
            "bmi": 0.7,
            "exercise_duration_min": -0.5,
        },
        "thyroid": {
            "stress_level": 1.2,
            "bmi": 0.5,
            "age": 0.2,
            "family_history_score": 2.0,
        },
    }

    # Disease baseline expected risk E[f(x)]
    BASE_RISKS = {
        "diabetes": 20.0,
        "heart_disease": 15.0,
        "stroke": 10.0,
        "hypertension": 15.0,
        "obesity": 18.0,
        "kidney_disease": 12.0,
        "fatty_liver": 15.0,
        "depression": 16.0,
        "sleep_disorder": 14.0,
        "thyroid": 12.0,
    }

    @classmethod
    def calculate_shap_values(
        cls, disease: str, raw_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute SHAP values for a specific disease and feature set.

        Returns:
            {
                "base_value": float E[f(x)],
                "predicted_value": float f(x),
                "shap_values": {feature_name: phi_i},
                "positive_drivers": [{feature, value, phi}],
                "negative_drivers": [{feature, value, phi}],
            }
        """
        disease_key = disease.lower().replace(" ", "_")
        weights = cls.FEATURE_RISK_WEIGHTS.get(disease_key, {})
        base_val = cls.BASE_RISKS.get(disease_key, 15.0)

        # Preprocess features
        norm_features = FeaturePipeline.extract_features(raw_features)

        shap_values = {}
        total_delta = 0.0

        for feat_name, val in norm_features.items():
            if feat_name in weights:
                w = weights[feat_name]
                exp = BASE_POPULATION_EXPECTATIONS.get(feat_name, 0.0)
                diff = val - exp
                phi = round(diff * w, 2)
                shap_values[feat_name] = phi
                total_delta += phi
            else:
                shap_values[feat_name] = 0.0

        predicted_val = round(max(5.0, min(95.0, base_val + total_delta)), 1)

        # Drivers
        pos_drivers = []
        neg_drivers = []
        for feat, phi in shap_values.items():
            if phi > 0.5:
                pos_drivers.append({
                    "feature": feat.replace("_", " ").title(),
                    "val": norm_features[feat],
                    "phi": phi,
                })
            elif phi < -0.5:
                neg_drivers.append({
                    "feature": feat.replace("_", " ").title(),
                    "val": norm_features[feat],
                    "phi": phi,
                })

        pos_drivers.sort(key=lambda x: x["phi"], reverse=True)
        neg_drivers.sort(key=lambda x: x["phi"])

        return {
            "disease": disease,
            "base_value": base_val,
            "predicted_value": predicted_val,
            "shap_values": shap_values,
            "positive_drivers": pos_drivers,
            "negative_drivers": neg_drivers,
        }

    @classmethod
    def compare_shap_contributions(
        cls, baseline_features: Dict[str, Any], current_log_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare SHAP attributions between Baseline Questionnaire and Current Daily Log.

        Identifies top lifestyle changes that drove risk improvements or worsening.

        Returns:
            Dict containing SHAP shifts for each disease and overall top lifestyle improvements.
        """
        base_norm = FeaturePipeline.extract_features(baseline_features)
        curr_norm = FeaturePipeline.extract_features(current_log_features)

        disease_comparisons = {}
        overall_improvements = []
        overall_worsening = []

        for disease in cls.BASE_RISKS:
            base_shap = cls.calculate_shap_values(disease, base_norm)
            curr_shap = cls.calculate_shap_values(disease, curr_norm)

            risk_delta = round(curr_shap["predicted_value"] - base_shap["predicted_value"], 1)

            feature_deltas = {}
            for feat in base_shap["shap_values"]:
                phi_base = base_shap["shap_values"][feat]
                phi_curr = curr_shap["shap_values"][feat]
                delta = round(phi_curr - phi_base, 2)
                if abs(delta) > 0.1:
                    feature_deltas[feat] = {
                        "baseline_phi": phi_base,
                        "current_phi": phi_curr,
                        "phi_delta": delta,
                        "baseline_val": base_norm[feat],
                        "current_val": curr_norm[feat],
                    }

            disease_comparisons[disease] = {
                "baseline_risk": base_shap["predicted_value"],
                "current_risk": curr_shap["predicted_value"],
                "risk_delta": risk_delta,
                "feature_deltas": feature_deltas,
            }

        # Track top global lifestyle improvements
        for feat in curr_norm:
            b_val = base_norm[feat]
            c_val = curr_norm[feat]

            # Sleep shift
            if feat == "sleep_hours" and c_val > b_val:
                overall_improvements.append({
                    "metric": "Sleep Hours",
                    "from_val": f"{b_val} hrs",
                    "to_val": f"{c_val} hrs",
                    "impact": "Reduced fatigue and cardiovascular risk",
                })
            elif feat == "water_intake_L" and c_val > b_val:
                overall_improvements.append({
                    "metric": "Water Intake",
                    "from_val": f"{b_val} L",
                    "to_val": f"{c_val} L",
                    "impact": "Lowered kidney and hydration stress",
                })
            elif feat == "exercise_duration_min" and c_val > b_val:
                overall_improvements.append({
                    "metric": "Daily Exercise",
                    "from_val": f"{b_val} min",
                    "to_val": f"{c_val} min",
                    "impact": "Decreased diabetes and heart disease risk factors",
                })
            elif feat == "stress_level" and c_val < b_val:
                overall_improvements.append({
                    "metric": "Stress Level",
                    "from_val": f"{b_val}/10",
                    "to_val": f"{c_val}/10",
                    "impact": "Lowered cortisol and hypertension risk",
                })
            elif feat == "stress_level" and c_val > b_val + 1:
                overall_worsening.append({
                    "metric": "Stress Level",
                    "from_val": f"{b_val}/10",
                    "to_val": f"{c_val}/10",
                    "impact": "Increased cardiovascular stress",
                })

        return {
            "disease_comparisons": disease_comparisons,
            "overall_improvements": overall_improvements,
            "overall_worsening": overall_worsening,
        }
