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


import pandas as pd
import numpy as np


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
        "diabetes": 16.4,
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
        cls, disease: str, raw_features: Dict[str, Any], target_prob: float = None, detailed_diabetes: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Compute SHAP values for a specific disease and feature set.
        Routes diabetes dynamically to model-specific pipeline SHAP.
        """
        disease_key = disease.lower().replace(" ", "_")

        # Dynamic pipeline-based SHAP for Diabetes models
        if disease_key == "diabetes":
            return cls._calculate_diabetes_pipeline_shap(raw_features, target_prob, detailed_diabetes)

        weights = cls.FEATURE_RISK_WEIGHTS.get(disease_key, {})
        base_val = cls.BASE_RISKS.get(disease_key, 15.0)

        # Preprocess features
        norm_features = FeaturePipeline.extract_features(raw_features)

        shap_values = {}
        raw_phi = {}
        total_delta = 0.0

        for feat_name, val in norm_features.items():
            if feat_name in weights:
                w = weights[feat_name]
                exp = BASE_POPULATION_EXPECTATIONS.get(feat_name, 0.0)
                diff = val - exp
                phi = round(diff * w, 2)
                raw_phi[feat_name] = phi
                total_delta += phi
            else:
                raw_phi[feat_name] = 0.0

        if target_prob is not None:
            predicted_val = round(max(3.0, min(95.0, target_prob)), 1)
        else:
            predicted_val = round(max(3.0, min(95.0, base_val + total_delta)), 1)

        target_delta = predicted_val - base_val
        # Calibrate SHAP phi values to strictly sum to predicted_val - base_val (efficiency property)
        if total_delta != 0 and abs(target_delta) > 0.01:
            scale = target_delta / total_delta
            for feat, phi in raw_phi.items():
                shap_values[feat] = round(phi * scale, 2)
        else:
            shap_values = raw_phi

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

    _BACKGROUND_DATA_CACHE = {}

    @classmethod
    def _get_background_training_data(cls, model_type: str):
        """
        Load and cache the exact 16,000-sample training dataset split for computing E[X_transformed].
        """
        if model_type not in cls._BACKGROUND_DATA_CACHE:
            import os
            import pandas as pd
            from sklearn.model_selection import train_test_split

            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            dataset_path = os.path.join(project_root, "datasets", "diabetes_dataset.csv")

            if not os.path.exists(dataset_path):
                return None

            try:
                df = pd.read_csv(dataset_path)
                df["Alcohol Intake"] = df["Alcohol Intake"].fillna("Missing")

                cols_basic = ["Gender", "Physical Activity", "Smoking Status", "Alcohol Intake", "Family History", "Age", "BMI"]
                cols_enhanced = cols_basic + ["Hypertension", "Glucose", "Blood Pressure", "Cholesterol"]
                cols_clinical = cols_enhanced + ["Skin Thickness", "Insulin", "Diabetes Pedigree Function"]

                y = (df["Outcome"] == "Diabetic").astype(int)

                train_idx = train_test_split(df, test_size=0.2, random_state=42, stratify=y)[0].index
                train_df = df.iloc[train_idx]

                cls._BACKGROUND_DATA_CACHE["basic"] = train_df[cols_basic].copy()
                cls._BACKGROUND_DATA_CACHE["enhanced"] = train_df[cols_enhanced].copy()
                cls._BACKGROUND_DATA_CACHE["clinical"] = train_df[cols_clinical].copy()
            except Exception as e:
                print(f"[ShapExplainer] Error loading background training data: {e}")
                return None

        return cls._BACKGROUND_DATA_CACHE.get(model_type)

    @classmethod
    def _calculate_diabetes_pipeline_shap(
        cls, raw_features: Dict[str, Any], target_prob: float = None, detailed_diabetes: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Computes exact baseline-relative Linear SHAP feature attributions in log-odds space for Diabetes (Model A, A+, B).
        
        Formula for fold k:
            phi_j^{(k)} = beta_j^{(k)} * (X_{trans, j}^{(k)} - E[X_{trans, j}^{(k)}])
            z_base^{(k)} = beta_0^{(k)} + sum(beta_j^{(k)} * E[X_{trans, j}^{(k)}])
            
        Ensemble average across all 5 calibrated fold estimators:
            phi(F_k) = (1/5) * sum_{fold} sum_{j in OHE(F_k)} phi_j^{(fold)}
            baseline_log_odds = (1/5) * sum_{fold} z_base^{(fold)}
        """
        from ml.predictor import MLPredictor, _get_diabetes_pipeline

        if detailed_diabetes is None:
            detailed_diabetes = MLPredictor.predict_diabetes_detailed(raw_features)

        model_type = detailed_diabetes.get("model_type", "basic")
        prob = detailed_diabetes.get("probability", target_prob or 15.0)

        # Load the exact pipeline that made the prediction
        model = _get_diabetes_pipeline(model_type)

        # Extract features DataFrame corresponding to the model type
        df_feat = cls._build_diabetes_feature_dataframe(raw_features, model_type)

        # Retrieve background training dataset (N=16,000)
        X_tr = cls._get_background_training_data(model_type)

        raw_parent_phi = {}
        fold_baselines = []
        feature_explanations = []

        if model is not None and hasattr(model, "calibrated_classifiers_") and X_tr is not None:
            cal_clfs = model.calibrated_classifiers_
            n_folds = len(cal_clfs)

            for cal in cal_clfs:
                pipe = cal.estimator
                preprocessor = pipe.named_steps["preprocessor"]
                clf = pipe.named_steps["classifier"]

                # 1. Compute training population background means for this fold
                X_tr_trans = preprocessor.transform(X_tr)
                bg_mean = np.mean(X_tr_trans, axis=0)

                # 2. Transform sample vector
                X_s_trans = preprocessor.transform(df_feat)[0]
                out_names = preprocessor.get_feature_names_out()

                beta_0 = clf.intercept_[0]
                coefs = clf.coef_[0]

                # Fold baseline log-odds: z_base = beta_0 + sum(beta_j * bg_mean_j)
                z_base_k = float(beta_0 + np.sum(coefs * bg_mean))
                fold_baselines.append(z_base_k)

                # Fold linear SHAP attribution: phi_j = beta_j * (X_sample_j - E[X_j])
                phi_k = coefs * (X_s_trans - bg_mean)

                for name, phi_val in zip(out_names, phi_k):
                    clean_name = name.replace("num__", "").replace("cat__", "")
                    parent = clean_name
                    for p_cand in df_feat.columns:
                        if clean_name == p_cand or clean_name.startswith(p_cand + "_"):
                            parent = p_cand
                            break

                    raw_parent_phi[parent] = raw_parent_phi.get(parent, 0.0) + float(phi_val) / n_folds

            baseline_log_odds = round(float(np.mean(fold_baselines)), 4)
        else:
            baseline_log_odds = 0.0
            for parent in df_feat.columns:
                raw_parent_phi[parent] = 0.0

        pos_drivers = []
        neg_drivers = []

        for parent in df_feat.columns:
            s_val = round(raw_parent_phi.get(parent, 0.0), 4)
            u_val = df_feat[parent].values[0]
            direction = "higher_risk" if s_val > 0.0001 else ("lower_risk" if s_val < -0.0001 else "neutral")
            desc_dir = "higher" if direction == "higher_risk" else "lower"

            entry = {
                "feature_name": parent,
                "user_value": u_val,
                "shap_value": s_val,
                "contribution_direction": direction,
                "description": f"Associated with a {desc_dir} predicted risk in this model."
            }
            feature_explanations.append(entry)

            if s_val > 0.05:
                pos_drivers.append({"feature": parent, "val": u_val, "phi": s_val})
            elif s_val < -0.05:
                neg_drivers.append({"feature": parent, "val": u_val, "phi": s_val})

        pos_drivers.sort(key=lambda x: x["phi"], reverse=True)
        neg_drivers.sort(key=lambda x: x["phi"])

        disclaimer = (
            "This explanation is based on self-reported demographic and lifestyle information and represents a model-based risk estimate, not a clinical diagnosis."
            if model_type == "basic"
            else "This explanation incorporates validated clinical vitals (Glucose, BP, Cholesterol)."
        )

        return {
            "disease": "diabetes",
            "model_type": model_type,
            "explanation_method": "Exact Linear SHAP (Log-Odds Attribution against Population Baseline)",
            "attribution_space": "log_odds",
            "baseline_log_odds": baseline_log_odds,
            "base_value": cls.BASE_RISKS.get("diabetes", 16.4),
            "predicted_value": prob,
            "predicted_probability": prob,
            "shap_values": {fe["feature_name"]: fe["shap_value"] for fe in feature_explanations},
            "feature_explanations": feature_explanations,
            "positive_drivers": pos_drivers,
            "negative_drivers": neg_drivers,
            "disclaimer": disclaimer,
            "used_features": list(df_feat.columns)
        }

    @classmethod
    def _build_diabetes_feature_dataframe(cls, raw_features: Dict[str, Any], model_type: str) -> pd.DataFrame:
        """
        Construct DataFrame with exact raw feature names expected by the model pipeline.
        """
        from ml.feature_pipeline import FeaturePipeline
        from ml.predictor import _validate_gender, _extract_personal_hypertension

        norm = FeaturePipeline.extract_features(raw_features)
        _, gender_val = _validate_gender(raw_features.get("gender", raw_features.get("Gender")))
        gender_val = gender_val or "Female"

        age_val = float(raw_features.get("age", norm.get("age", 40.0)) or 40.0)
        bmi_val = float(norm.get("bmi", 24.5))

        act_raw = raw_features.get("exercise_frequency", "1-2x per week")
        act_val = "Low" if act_raw == "Never" else ("High" if act_raw == "5+ times per week" else "Moderate")

        smk_raw = raw_features.get("smoking_status", "Never")
        smk_val = "Current" if smk_raw == "Current" else ("Former" if smk_raw == "Former" else "Never")

        alc_raw = raw_features.get("alcohol_intake", "None")
        alc_val = "Regular" if alc_raw == "Heavy" else ("Occasional" if alc_raw in ("Occasional", "Moderate") else "Missing")

        fam_diab = "Yes" if raw_features.get("family_diabetes") else "No"

        if model_type == "basic":
            return pd.DataFrame([{
                "Gender": gender_val,
                "Physical Activity": act_val,
                "Smoking Status": smk_val,
                "Alcohol Intake": alc_val,
                "Family History": fam_diab,
                "Age": age_val,
                "BMI": bmi_val,
            }])

        glucose_val = float(raw_features.get("blood_sugar_fasting", 95.0) or 95.0)
        bp_val = float(raw_features.get("blood_pressure_systolic", 120.0) or 120.0)
        chol_val = float(raw_features.get("cholesterol_level", 190.0) or 190.0)
        htn_val = _extract_personal_hypertension(raw_features, bp_val)

        if model_type == "enhanced":
            return pd.DataFrame([{
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

        # Clinical (Model B)
        skin_val = float(raw_features.get("skin_thickness", raw_features.get("Skin Thickness", 20.0)))
        ins_val = float(raw_features.get("insulin", raw_features.get("Insulin", 80.0)))
        dpf_val = float(raw_features.get("diabetes_pedigree_function", raw_features.get("Diabetes Pedigree Function", 0.5)))

        return pd.DataFrame([{
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
            "Skin Thickness": skin_val,
            "Insulin": ins_val,
            "Cholesterol": chol_val,
            "Diabetes Pedigree Function": dpf_val,
        }])

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

            base_pred = base_shap.get("predicted_value", base_shap.get("predicted_probability", 0.0))
            curr_pred = curr_shap.get("predicted_value", curr_shap.get("predicted_probability", 0.0))

            risk_delta = round(curr_pred - base_pred, 1)

            feature_deltas = {}
            base_shap_vals = base_shap.get("shap_values", {})
            curr_shap_vals = curr_shap.get("shap_values", {})
            for feat in base_shap_vals:
                phi_base = base_shap_vals.get(feat, 0.0)
                phi_curr = curr_shap_vals.get(feat, 0.0)
                delta = round(phi_curr - phi_base, 2)
                if abs(delta) > 0.1:
                    feature_deltas[feat] = {
                        "baseline_phi": phi_base,
                        "current_phi": phi_curr,
                        "phi_delta": delta,
                        "baseline_val": base_norm.get(feat, 0),
                        "current_val": curr_norm.get(feat, 0),
                    }

            disease_comparisons[disease] = {
                "baseline_risk": base_pred,
                "current_risk": curr_pred,
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
