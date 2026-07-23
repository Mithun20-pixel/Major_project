"""
ml/predictor.py - ML Prediction & XAI Inference Engine
======================================================
Unified ML predictor that runs disease risk inference, computes SHAP values,
and generates LIME explanations for any feature set.
"""

from typing import Dict, Any, Tuple
from ml.feature_pipeline import FeaturePipeline
from ml.shap_explainer import ShapExplainer
from ml.lime_explainer import LimeExplainer


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
    def predict_all(cls, raw_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run inference for all diseases and generate XAI explanations.

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

        for disease in cls.DISEASES:
            shap_res = ShapExplainer.calculate_shap_values(disease, raw_features)
            probabilities[disease] = shap_res["predicted_value"]
            shap_explanations[disease] = shap_res

        lime_res = LimeExplainer.explain_instance(raw_features)

        return {
            "probabilities": probabilities,
            "shap_explanations": shap_explanations,
            "lime_explanation": lime_res,
        }
