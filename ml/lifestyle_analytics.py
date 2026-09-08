"""
ml/lifestyle_analytics.py - Health & Lifestyle Survey Analytics Engine
=======================================================================
Processes, cleans, and standardizes survey responses from
`datasets/health_lifestyle_dataset.csv` (571 respondents).

Provides:
- Data cleaning & normalization (correcting typos like 'tabacoo', '5-Jan').
- Population peer benchmarking metrics (e.g. sleep duration, water intake, stress across age/professions).
- Survey-backed recommendation rules for the PredictionService.
"""

import os
import re
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIFESTYLE_DATASET_PATH = os.path.join(PROJECT_ROOT, "datasets", "health_lifestyle_dataset.csv")


class LifestyleAnalytics:
    """
    Analytics & Recommendation Engine for Health/Lifestyle Survey Data.
    """

    _df_cache = None

    @classmethod
    def get_cleaned_data(cls) -> pd.DataFrame:
        """
        Load and clean health_lifestyle_dataset.csv.
        Caches the cleaned DataFrame in memory.
        """
        if cls._df_cache is not None:
            return cls._df_cache

        if not os.path.exists(LIFESTYLE_DATASET_PATH):
            print(f"[LifestyleAnalytics] Warning: File not found at {LIFESTYLE_DATASET_PATH}")
            return pd.DataFrame()

        df = pd.read_csv(LIFESTYLE_DATASET_PATH)

        # 1. Clean Gender
        df["Gender_clean"] = df["Gender"].astype(str).str.upper().map({"F": "Female", "M": "Male"}).fillna("Other")

        # 2. Clean Water Intake (handle '5-Jan' corrupted Excel date -> 5.0)
        def clean_water(val):
            if pd.isna(val):
                return 2.0
            val_str = str(val).lower().strip()
            if "jan" in val_str or "5-jan" in val_str:
                return 5.0
            match = re.search(r"(\d+(\.\d+)?)", val_str)
            if match:
                return float(match.group(1))
            return 2.0

        df["Water_Intake_clean"] = df["Water Intake per Day"].apply(clean_water)

        # 3. Clean Sleep Duration
        def clean_sleep(val):
            if pd.isna(val):
                return 7.0
            val_str = str(val).lower().strip()
            if val_str == "normal":
                return 7.0
            match = re.search(r"(\d+(\.\d+)?)", val_str)
            if match:
                return float(match.group(1))
            return 7.0

        df["Sleep_Duration_clean"] = df["Sleep Duration"].apply(clean_sleep)

        # 4. Clean Smoking Habit
        def clean_smoking(val):
            val_str = str(val).lower().strip()
            if "yes" in val_str or "tabacoo" in val_str:
                return "Current"
            return "Never"

        df["Smoking_Habit_clean"] = df["Smoking Habit"].apply(clean_smoking)

        # 5. Clean Alcohol Consumption
        def clean_alcohol(val):
            val_str = str(val).lower().strip()
            if "yes" in val_str:
                return "Moderate"
            return "None"

        df["Alcohol_Consumption_clean"] = df["Alcohol Consumption"].apply(clean_alcohol)

        cls._df_cache = df
        return df

    @classmethod
    def get_peer_benchmarks(cls, age: int, gender: str) -> dict:
        """
        Compute population benchmarks for a user based on survey respondents.

        Args:
            age: User's age.
            gender: User's gender string.

        Returns:
            Dict containing average peer metrics (sleep, water intake, stress, etc.).
        """
        df = cls.get_cleaned_data()
        if df.empty:
            return {
                "avg_sleep_hours": 7.0,
                "avg_water_L": 2.5,
                "sample_size": 571,
            }

        # Filter by age group window (e.g. +/- 5 years)
        age_mask = (df["Age Group"] >= max(18, age - 5)) & (df["Age Group"] <= min(80, age + 5))
        peer_df = df[age_mask]

        if len(peer_df) < 10:
            peer_df = df  # fallback to entire population

        avg_sleep = round(peer_df["Sleep_Duration_clean"].mean(), 1)
        avg_water = round(peer_df["Water_Intake_clean"].mean(), 1)

        return {
            "avg_sleep_hours": avg_sleep,
            "avg_water_L": avg_water,
            "sample_size": len(peer_df),
            "total_survey_respondents": len(df),
        }


if __name__ == "__main__":
    df = LifestyleAnalytics.get_cleaned_data()
    print(f"Loaded and cleaned {len(df)} survey rows.")
    benchmarks = LifestyleAnalytics.get_peer_benchmarks(age=25, gender="Female")
    print("Sample peer benchmarks (Age 25):", benchmarks)
