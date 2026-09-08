"""
ml/train_diabetes_basic.py - Model A (Basic Self-Reported Diabetes Model)
========================================================================
Trains Model A for users completing the basic health questionnaire without
any optional clinical measurements.

Features used (7 non-clinical features):
- Categorical: Gender, Physical Activity, Smoking Status, Alcohol Intake, Family History
- Numerical: Age, BMI

Preprocess: ColumnTransformer (OneHotEncoder + StandardScaler) inside a single Pipeline.
Evaluation: Compares RandomForestClassifier, LogisticRegression, and HistGradientBoosting.
Saves: ml/saved_models/diabetes_basic_model.joblib
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, brier_score_loss, confusion_matrix, classification_report
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_PATH = os.path.join(PROJECT_ROOT, "datasets", "diabetes_dataset.csv")
SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
os.makedirs(SAVED_MODELS_DIR, exist_ok=True)

# Feature definitions for Model A (Basic Self-Reported)
CAT_FEATURES = ["Gender", "Physical Activity", "Smoking Status", "Alcohol Intake", "Family History"]
NUM_FEATURES = ["Age", "BMI"]
FEATURE_COLUMNS = CAT_FEATURES + NUM_FEATURES
TARGET_COLUMN = "Outcome"


def train_basic_model():
    print(f"=== MODEL A (BASIC SELF-REPORTED DIABETES MODEL) TRAINING ===")
    print(f"Loading dataset from: {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH)
    print(f"Dataset Total Rows: {len(df)}")

    # 1. Clean missing values (Alcohol Intake: 49.6% missing)
    df["Alcohol Intake"] = df["Alcohol Intake"].fillna("Missing")

    # 2. Target separation
    X = df[FEATURE_COLUMNS].copy()
    y = (df[TARGET_COLUMN] == "Diabetic").astype(int)

    print(f"Features used ({len(FEATURE_COLUMNS)}): {FEATURE_COLUMNS}")
    print(f"Target Distribution: Diabetic={sum(y==1)} ({sum(y==1)/len(y)*100:.1f}%), Non-diabetic={sum(y==0)} ({sum(y==0)/len(y)*100:.1f}%)")

    # 3. Stratified 80/20 train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Train sample count: {len(X_train)}, Test sample count: {len(X_test)}")

    # 4. Preprocessing Pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUM_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT_FEATURES)
        ]
    )

    # 5. Candidate Classifiers Comparison
    candidates = {
        "RandomForest": RandomForestClassifier(
            n_estimators=150, max_depth=8, min_samples_split=5,
            class_weight="balanced", random_state=42
        ),
        "LogisticRegression": LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=42
        ),
        "HistGradientBoosting": HistGradientBoostingClassifier(
            class_weight="balanced", random_state=42
        )
    }

    results = {}
    best_name = None
    best_auc = -1.0
    best_calibrated_pipeline = None

    print("\n--- Evaluating Candidate Algorithms ---")
    for name, clf in candidates.items():
        pipe = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", clf)
        ])
        
        # Calibration wrapper
        calibrated_clf = CalibratedClassifierCV(estimator=pipe, method="sigmoid", cv=5)
        calibrated_clf.fit(X_train, y_train)

        probs = calibrated_clf.predict_proba(X_test)[:, 1]
        preds = (probs >= 0.5).astype(int)

        auc = roc_auc_score(y_test, probs)
        acc = accuracy_score(y_test, preds)
        macro_f1 = f1_score(y_test, preds, average="macro")
        brier = brier_score_loss(y_test, probs)

        cm = confusion_matrix(y_test, preds)
        
        results[name] = {
            "accuracy": round(acc, 4),
            "precision_diabetic": round(precision_score(y_test, preds, pos_label=1), 4),
            "recall_diabetic": round(recall_score(y_test, preds, pos_label=1), 4),
            "f1_diabetic": round(f1_score(y_test, preds, pos_label=1), 4),
            "precision_non_diabetic": round(precision_score(y_test, preds, pos_label=0), 4),
            "recall_non_diabetic": round(recall_score(y_test, preds, pos_label=0), 4),
            "f1_non_diabetic": round(f1_score(y_test, preds, pos_label=0), 4),
            "macro_f1": round(macro_f1, 4),
            "roc_auc": round(auc, 4),
            "brier_score": round(brier, 4),
            "confusion_matrix": cm.tolist(),
            "calibrated_model": calibrated_clf
        }

        print(f"[{name:<20}] ROC-AUC: {auc:.4f} | Accuracy: {acc:.4f} | Macro-F1: {macro_f1:.4f} | Brier: {brier:.4f}")

        if auc > best_auc:
            best_auc = auc
            best_name = name
            best_calibrated_pipeline = calibrated_clf

    print(f"\n---> Selected Algorithm for Model A (Basic): {best_name} (ROC-AUC: {best_auc:.4f})")

    # 6. Save the selected complete pipeline
    model_path = os.path.join(SAVED_MODELS_DIR, "diabetes_basic_model.joblib")
    joblib.dump(best_calibrated_pipeline, model_path)
    print(f"Saved complete Model A pipeline to: {model_path}")

    # 7. Save metadata
    meta_path = os.path.join(SAVED_MODELS_DIR, "diabetes_basic_metadata.joblib")
    meta_data = {
        "model_type": "Model A (Basic Self-Reported)",
        "selected_algorithm": best_name,
        "features": FEATURE_COLUMNS,
        "cat_features": CAT_FEATURES,
        "num_features": NUM_FEATURES,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "metrics": results[best_name],
        "all_candidate_metrics": {k: {m: v[m] for m in v if m != "calibrated_model"} for k, v in results.items()}
    }
    joblib.dump(meta_data, meta_path)
    print(f"Saved Model A metadata to: {meta_path}\n")

    return meta_data


if __name__ == "__main__":
    train_basic_model()
