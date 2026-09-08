"""
ml/train_diabetes_real.py - Real Dataset Diabetes Model Trainer
================================================================
Trains a calibrated RandomForestClassifier model on the real-world dataset
`datasets/diabetes_dataset.csv` (20,000 records).

Handles:
- Categorical feature encoding and missing value imputation (Alcohol Intake: 49.6%).
- Class imbalance mitigation (83.6% Diabetic vs 16.4% Non-diabetic) using balanced class weights.
- Feature scaling with StandardScaler.
- Probability calibration using CalibratedClassifierCV.
- Saving trained model binary and feature mapper metadata to `ml/saved_models/`.
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, brier_score_loss, classification_report
from sklearn.preprocessing import StandardScaler

# Path setup
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_PATH = os.path.join(PROJECT_ROOT, "datasets", "diabetes_dataset.csv")
SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
os.makedirs(SAVED_MODELS_DIR, exist_ok=True)

# Define column schema
FEATURE_COLUMNS = [
    "Gender", "Age", "Physical Activity", "Smoking Status", "Alcohol Intake",
    "Glucose", "Blood Pressure", "Skin Thickness", "Insulin", "BMI",
    "Cholesterol", "Diabetes Pedigree Function", "Family History", "Hypertension"
]
TARGET_COLUMN = "Outcome"


def preprocess_diabetes_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, dict]:
    """
    Preprocess raw diabetes DataFrame.
    Encodes categorical features and handles missing values.
    """
    df = df.copy()

    # 1. Target encoding: Diabetic -> 1, Non-diabetic -> 0
    y = (df[TARGET_COLUMN] == "Diabetic").astype(int)

    # 2. Handle missing Alcohol Intake (fill with 'Missing')
    df["Alcohol Intake"] = df["Alcohol Intake"].fillna("Missing")

    # 3. Categorical encoding mappings
    gender_map = {"Male": 1, "Female": 0}
    activity_map = {"Low": 0, "Moderate": 1, "High": 2}
    smoking_map = {"Never": 0, "Former": 1, "Current": 2}
    alcohol_map = {"Missing": 0, "Occasional": 1, "Regular": 2}
    family_map = {"No": 0, "Yes": 1}
    hypertension_map = {"No": 0, "Yes": 1}

    df["Gender_enc"] = df["Gender"].map(gender_map).fillna(0)
    df["Physical_Activity_enc"] = df["Physical Activity"].map(activity_map).fillna(1)
    df["Smoking_Status_enc"] = df["Smoking Status"].map(smoking_map).fillna(0)
    df["Alcohol_Intake_enc"] = df["Alcohol Intake"].map(alcohol_map).fillna(0)
    df["Family_History_enc"] = df["Family History"].map(family_map).fillna(0)
    df["Hypertension_enc"] = df["Hypertension"].map(hypertension_map).fillna(0)

    # Feature matrix columns
    encoded_feature_names = [
        "Gender_enc", "Age", "Physical_Activity_enc", "Smoking_Status_enc",
        "Alcohol_Intake_enc", "Glucose", "Blood Pressure", "Skin Thickness",
        "Insulin", "BMI", "Cholesterol", "Diabetes Pedigree Function",
        "Family_History_enc", "Hypertension_enc"
    ]

    X = df[encoded_feature_names]

    mappings = {
        "gender_map": gender_map,
        "activity_map": activity_map,
        "smoking_map": smoking_map,
        "alcohol_map": alcohol_map,
        "family_map": family_map,
        "hypertension_map": hypertension_map,
        "feature_names": encoded_feature_names,
    }

    return X, y, mappings


def train_and_save_real_diabetes_model():
    print(f"Loading real diabetes dataset from: {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH)

    print(f"Dataset shape: {df.shape}")
    X, y, mappings = preprocess_diabetes_data(df)

    # Train / Test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Fit & save dedicated Scaler
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    scaler_path = os.path.join(SAVED_MODELS_DIR, "diabetes_real_scaler.joblib")
    joblib.dump(scaler, scaler_path)
    print(f"Saved real diabetes scaler to {scaler_path}")

    # Train RandomForest with class weight balancing
    base_clf = RandomForestClassifier(
        n_estimators=150,
        max_depth=8,
        min_samples_split=5,
        random_state=42,
        class_weight="balanced"
    )

    calibrated_clf = CalibratedClassifierCV(estimator=base_clf, method="sigmoid", cv=5)
    calibrated_clf.fit(X_train_scaled, y_train)

    # Evaluate model
    probs = calibrated_clf.predict_proba(X_test_scaled)[:, 1]
    preds = (probs >= 0.5).astype(int)

    auc = roc_auc_score(y_test, probs)
    acc = accuracy_score(y_test, preds)
    brier = brier_score_loss(y_test, probs)

    print("\n================ REAL DIABETES MODEL EVALUATION ================")
    print(f"ROC-AUC     : {auc:.4f}")
    print(f"Accuracy    : {acc:.4f}")
    print(f"Brier Score : {brier:.4f}")
    print("\nClassification Report:\n", classification_report(y_test, preds, target_names=["Non-diabetic", "Diabetic"]))
    print("================================================================\n")

    # Save model and metadata
    model_path = os.path.join(SAVED_MODELS_DIR, "diabetes_model.joblib")
    joblib.dump(calibrated_clf, model_path)
    print(f"Saved calibrated real diabetes model to: {model_path}")

    meta_path = os.path.join(SAVED_MODELS_DIR, "diabetes_real_metadata.joblib")
    joblib.dump(mappings, meta_path)
    print(f"Saved feature metadata to: {meta_path}")


if __name__ == "__main__":
    train_and_save_real_diabetes_model()
