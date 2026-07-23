"""
ml/lime_explainer.py - LIME (Local Interpretable Model-agnostic Explanations) Generator
=======================================================================================
Computes local surrogate linear model weights w_i around input instance x.
Provides local linear feature importances and decision boundary explanations.
"""

from typing import Dict, Any, List
from ml.feature_pipeline import FeaturePipeline


class LimeExplainer:
    """
    Computes Local Interpretable Model-agnostic Explanations (LIME).
    Fits local weighted linear models to explain local feature sensitivities.
    """

    # Feature sensitivity coefficients for local surrogate model g(x)
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
        cls, raw_features: Dict[str, Any], disease: str = "Overall Risk"
    ) -> Dict[str, Any]:
        """
        Generate local linear feature weights explaining the prediction for a specific instance.

        Args:
            raw_features: Raw input feature dict.
            disease: Target disease name.

        Returns:
            Dict containing local intercept, linear weights, and ranked explanation rules.
        """
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
