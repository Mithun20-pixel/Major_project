"""
ml/train_models.py - ML Disease Prediction Model Trainer
=========================================================
Trains calibrated Machine Learning models (CalibratedClassifierCV with
RandomForestClassifier) on synthetic clinical dataset representing epidemiological
disease risk distributions (NHANES/Framingham data).

Saves model binaries to ml/saved_models/ for inference.
"""

import os
import sys

# Ensure root workspace directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, brier_score_loss
from sklearn.preprocessing import StandardScaler

from ml.feature_pipeline import FEATURE_NAMES

SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
os.makedirs(SAVED_MODELS_DIR, exist_ok=True)

DISEASES = [
    "diabetes", "heart_disease", "stroke",
    "hypertension", "obesity", "kidney_disease",
    "fatty_liver", "depression", "sleep_disorder", "thyroid",
]


def generate_clinical_dataset(n_samples: int = 8000, seed: int = 42) -> pd.DataFrame:
    """
    Generate synthetic health dataset with realistic population distributions
    and epidemiologically sound disease risk relationships.
    """
    np.random.seed(seed)

    # 1. Continuous Demographics & Vitals
    age = np.random.uniform(18, 80, n_samples)
    height_m = np.random.normal(1.70, 0.10, n_samples)
    height_m = np.clip(height_m, 1.40, 2.10)
    weight_kg = np.random.normal(72, 16, n_samples)
    weight_kg = np.clip(weight_kg, 40, 150)
    bmi = weight_kg / (height_m ** 2)
    
    sleep_hours = np.random.normal(7.0, 1.2, n_samples)
    sleep_hours = np.clip(sleep_hours, 3.0, 12.0)
    
    water_intake_L = np.random.gamma(3.0, 0.8, n_samples)
    water_intake_L = np.clip(water_intake_L, 0.5, 6.0)
    
    exercise_duration_min = np.random.exponential(25.0, n_samples)
    exercise_duration_min = np.clip(exercise_duration_min, 0.0, 180.0)
    
    daily_steps = exercise_duration_min * np.random.uniform(80, 150, n_samples) + np.random.normal(3000, 1500, n_samples)
    daily_steps = np.clip(daily_steps, 500, 25000)
    
    stress_level = np.random.randint(1, 11, n_samples).astype(float)
    fruit_veg_servings = np.random.poisson(3.5, n_samples).astype(float)
    fast_food_per_week = np.random.poisson(2.0, n_samples).astype(float)
    
    smoking_active = np.random.choice([0.0, 1.0], size=n_samples, p=[0.80, 0.20])
    alcohol_heavy = np.random.choice([0.0, 1.0], size=n_samples, p=[0.85, 0.15])
    family_history_score = np.random.choice([0.0, 0.5, 1.0, 1.5, 2.0], size=n_samples, p=[0.4, 0.3, 0.15, 0.1, 0.05])
    
    blood_pressure_systolic = 100 + (age * 0.3) + (bmi * 0.8) + (stress_level * 1.5) + (smoking_active * 6.0) + np.random.normal(0, 8, n_samples)
    blood_pressure_systolic = np.clip(blood_pressure_systolic, 90, 200)
    
    blood_sugar_fasting = 75 + (bmi * 0.9) + (fast_food_per_week * 1.5) - (exercise_duration_min * 0.1) + np.random.normal(0, 10, n_samples)
    blood_sugar_fasting = np.clip(blood_sugar_fasting, 70, 250)

    df = pd.DataFrame({
        "age": age,
        "bmi": bmi,
        "sleep_hours": sleep_hours,
        "water_intake_L": water_intake_L,
        "exercise_duration_min": exercise_duration_min,
        "daily_steps": daily_steps,
        "stress_level": stress_level,
        "fruit_veg_servings": fruit_veg_servings,
        "fast_food_per_week": fast_food_per_week,
        "smoking_active": smoking_active,
        "alcohol_heavy": alcohol_heavy,
        "family_history_score": family_history_score,
        "blood_pressure_systolic": blood_pressure_systolic,
        "blood_sugar_fasting": blood_sugar_fasting,
    })

    # 2. Epidemiological Logistic Risk Models for Target Generation
    def sigmoid(z):
        return 1.0 / (1.0 + np.exp(-z))

    df["diabetes_prob"] = sigmoid(
        -2.0 + 0.08 * (bmi - 25) + 0.04 * (blood_sugar_fasting - 100)
        + 0.6 * family_history_score - 0.02 * exercise_duration_min + 0.03 * (age - 40)
    )
    df["diabetes_target"] = (np.random.uniform(0, 1, n_samples) < df["diabetes_prob"]).astype(int)

    df["heart_disease_prob"] = sigmoid(
        -2.2 + 1.2 * smoking_active + 0.04 * (blood_pressure_systolic - 120)
        + 0.05 * (bmi - 25) + 0.2 * stress_level + 0.8 * alcohol_heavy
        + 0.6 * family_history_score - 0.025 * exercise_duration_min
    )
    df["heart_disease_target"] = (np.random.uniform(0, 1, n_samples) < df["heart_disease_prob"]).astype(int)

    df["stroke_prob"] = sigmoid(
        -2.5 + 0.05 * (blood_pressure_systolic - 120) + 1.2 * smoking_active
        + 0.04 * (age - 50) + 0.6 * family_history_score + 0.7 * alcohol_heavy
    )
    df["stroke_target"] = (np.random.uniform(0, 1, n_samples) < df["stroke_prob"]).astype(int)

    df["hypertension_prob"] = sigmoid(
        -1.8 + 0.06 * (blood_pressure_systolic - 120) + 0.2 * stress_level
        + 0.05 * (bmi - 25) + 0.8 * alcohol_heavy - 0.3 * water_intake_L
    )
    df["hypertension_target"] = (np.random.uniform(0, 1, n_samples) < df["hypertension_prob"]).astype(int)

    df["obesity_prob"] = sigmoid(
        -1.5 + 0.45 * (bmi - 25) - 0.02 * exercise_duration_min
        + 0.25 * fast_food_per_week - 0.15 * fruit_veg_servings
    )
    df["obesity_target"] = (np.random.uniform(0, 1, n_samples) < df["obesity_prob"]).astype(int)

    df["kidney_disease_prob"] = sigmoid(
        -2.5 + 0.04 * (blood_pressure_systolic - 120) + 0.03 * (blood_sugar_fasting - 100)
        - 0.5 * water_intake_L + 0.8 * smoking_active + 0.03 * (age - 45)
    )
    df["kidney_disease_target"] = (np.random.uniform(0, 1, n_samples) < df["kidney_disease_prob"]).astype(int)

    df["fatty_liver_prob"] = sigmoid(
        -2.0 + 0.16 * (bmi - 25) + 1.2 * alcohol_heavy + 0.25 * fast_food_per_week
        - 0.02 * exercise_duration_min
    )
    df["fatty_liver_target"] = (np.random.uniform(0, 1, n_samples) < df["fatty_liver_prob"]).astype(int)

    df["depression_prob"] = sigmoid(
        -1.8 + 0.35 * stress_level - 0.4 * (sleep_hours - 7)
        - 0.015 * exercise_duration_min - 0.15 * fruit_veg_servings
    )
    df["depression_target"] = (np.random.uniform(0, 1, n_samples) < df["depression_prob"]).astype(int)

    df["sleep_disorder_prob"] = sigmoid(
        -1.8 - 0.7 * (sleep_hours - 7) + 0.25 * stress_level + 0.05 * (bmi - 25)
    )
    df["sleep_disorder_target"] = (np.random.uniform(0, 1, n_samples) < df["sleep_disorder_prob"]).astype(int)

    df["thyroid_prob"] = sigmoid(
        -2.2 + 0.15 * stress_level + 0.6 * family_history_score + 0.02 * (age - 35)
    )
    df["thyroid_target"] = (np.random.uniform(0, 1, n_samples) < df["thyroid_prob"]).astype(int)

    return df


def train_and_save_all_models():
    """
    Trains calibrated classifiers for each disease and saves models + scaler.
    """
    print("Generating epidemiological synthetic dataset...")
    df = generate_clinical_dataset(n_samples=8000, seed=42)

    X = df[FEATURE_NAMES]
    
    # Fit & save StandardScaler with feature names preserved
    scaler = StandardScaler()
    scaler.fit(X)
    
    scaler_path = os.path.join(SAVED_MODELS_DIR, "scaler.joblib")
    joblib.dump(scaler, scaler_path)
    print(f"Saved scaler to {scaler_path}")

    metrics_summary = {}

    for disease in DISEASES:
        y = df[f"{disease}_target"]
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        X_train_scaled = scaler.transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        base_clf = RandomForestClassifier(
            n_estimators=120, max_depth=7, random_state=42, class_weight="balanced"
        )
        
        calibrated_clf = CalibratedClassifierCV(estimator=base_clf, method="sigmoid", cv=3)
        calibrated_clf.fit(X_train_scaled, y_train)

        probs = calibrated_clf.predict_proba(X_test_scaled)[:, 1]
        preds = (probs >= 0.5).astype(int)
        
        auc = roc_auc_score(y_test, probs)
        acc = accuracy_score(y_test, preds)
        brier = brier_score_loss(y_test, probs)

        metrics_summary[disease] = {
            "ROC-AUC": round(auc, 4),
            "Accuracy": round(acc, 4),
            "Brier Score": round(brier, 4),
        }

        # Save model
        model_path = os.path.join(SAVED_MODELS_DIR, f"{disease}_model.joblib")
        joblib.dump(calibrated_clf, model_path)

    print("\n================ MODEL TRAINING SUMMARY ================")
    for disease, res in metrics_summary.items():
        print(f"{disease:<16}: ROC-AUC = {res['ROC-AUC']:.4f} | Accuracy = {res['Accuracy']:.4f} | Brier = {res['Brier Score']:.4f}")
    print("========================================================\n")


if __name__ == "__main__":
    train_and_save_all_models()
