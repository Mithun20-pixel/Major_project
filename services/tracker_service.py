"""
services/tracker_service.py - Daily Health Tracker Service
============================================================
Handles all business logic for the Daily Lifestyle Tracking module.

Key responsibilities:
    - save_log()               → Persist a validated DailyHealthLog entry
    - get_logs()               → Retrieve recent logs for a user
    - get_weekly_stats()       → Weekly averages + % change vs prior week
    - get_monthly_stats()      → Monthly averages + % change vs prior month
    - compute_updated_risk()   → Overlay latest log onto baseline questionnaire,
                                 re-run PredictionService to get updated disease risks
    - get_progress_comparison()→ Baseline prediction vs. latest updated prediction
    - get_health_coach_tips()  → Dynamic AI coach messages derived from log trends
    - get_chart_data()         → Formatted time-series data for Chart.js
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Optional

from flask import Flask
from sqlalchemy import and_, func

from extensions import db
from models.daily_health_log import DailyHealthLog
from models.prediction import Prediction
from models.questionnaire import Questionnaire


class TrackerService:
    """
    Orchestrates all tracker-related queries and computations.

    Usage:
        service = TrackerService(current_app._get_current_object())
        log = service.save_log(user_id=1, form=form)
        stats = service.get_weekly_stats(user_id=1)
    """

    # ── Healthy target benchmarks ──────────────────────────────────────────
    TARGETS = {
        "sleep_hours":       8.0,
        "sleep_quality":     4.0,
        "water_intake":      2.5,
        "exercise_minutes": 30.0,
        "steps":          10_000,
        "stress_level":      5.0,
        "fruits":            3.0,
        "vegetables":        3.0,
    }

    def __init__(self, app: Flask):
        """
        Args:
            app: The Flask application instance (required for app context).
        """
        self.app = app

    # ── Core CRUD ─────────────────────────────────────────────────────────

    def save_log(self, user_id: int, form) -> DailyHealthLog:
        """
        Validate uniqueness and persist a new DailyHealthLog entry.

        Args:
            user_id: ID of the authenticated user.
            form:    A validated DailyHealthLogForm instance.

        Returns:
            The newly created DailyHealthLog ORM instance.

        Raises:
            ValueError: If a log already exists for the specified date.
        """
        target_date = form.log_date.data

        # Prevent duplicate entries for the same date
        existing = DailyHealthLog.query.filter_by(
            user_id=user_id, log_date=target_date
        ).first()
        if existing:
            raise ValueError(
                f"You have already logged data for {target_date.strftime('%B %d, %Y')}. "
                "Please select a different date or edit today's entry."
            )

        log = DailyHealthLog(
            user_id          = user_id,
            log_date         = target_date,
            # Sleep
            sleep_hours      = form.sleep_hours.data,
            sleep_quality    = form.sleep_quality.data,
            # Water
            water_intake     = form.water_intake.data,
            # Exercise
            exercise_minutes = form.exercise_minutes.data,
            steps            = form.steps.data,
            workout_type     = form.workout_type.data or None,
            # Meals
            breakfast        = bool(form.breakfast.data),
            lunch            = bool(form.lunch.data),
            dinner           = bool(form.dinner.data),
            # Food quality
            fruits           = form.fruits.data or 0,
            vegetables       = form.vegetables.data or 0,
            junk_food        = bool(form.junk_food.data),
            sugary_drinks    = bool(form.sugary_drinks.data),
            # Habits
            smoking          = bool(form.smoking.data),
            alcohol          = bool(form.alcohol.data),
            tobacco          = bool(form.tobacco.data),
            # Mental health
            stress_level     = form.stress_level.data,
            mood             = form.mood.data,
            anxiety_level    = form.anxiety_level.data or None,
            # Vitals
            weight           = form.weight.data,
            blood_pressure   = (form.blood_pressure.data or "").strip() or None,
            blood_sugar      = form.blood_sugar.data or None,
            heart_rate       = form.heart_rate.data or None,
        )

        db.session.add(log)
        db.session.commit()
        return log

    def get_logs(self, user_id: int, days: int = 30) -> list[DailyHealthLog]:
        """
        Retrieve the most recent `days` logs for a user, ordered by date DESC.

        Args:
            user_id: ID of the user.
            days:    How many calendar days back to query.

        Returns:
            List of DailyHealthLog instances.
        """
        cutoff = date.today() - timedelta(days=days)
        return (
            DailyHealthLog.query
            .filter(
                DailyHealthLog.user_id == user_id,
                DailyHealthLog.log_date >= cutoff,
            )
            .order_by(DailyHealthLog.log_date.desc())
            .all()
        )

    def get_today_log(self, user_id: int) -> Optional[DailyHealthLog]:
        """Return the log for today, or None if not yet submitted."""
        return DailyHealthLog.query.filter_by(
            user_id=user_id, log_date=date.today()
        ).first()

    def get_log_streak(self, user_id: int) -> int:
        """
        Calculate the current consecutive-day logging streak.

        Returns the number of consecutive days (ending today or yesterday)
        for which the user has a log entry.
        """
        all_dates = {
            row.log_date
            for row in DailyHealthLog.query
            .filter_by(user_id=user_id)
            .with_entities(DailyHealthLog.log_date)
            .all()
        }
        streak = 0
        check = date.today()
        while check in all_dates:
            streak += 1
            check -= timedelta(days=1)
        # Also count if yesterday is the last log (they haven't logged today yet)
        if streak == 0:
            check = date.today() - timedelta(days=1)
            while check in all_dates:
                streak += 1
                check -= timedelta(days=1)
        return streak

    # ── Aggregations ─────────────────────────────────────────────────────

    def get_weekly_stats(self, user_id: int) -> dict:
        """
        Compute weekly averages for this week vs. last week.

        Returns:
            {
                "this_week":   {metric: avg},
                "last_week":   {metric: avg},
                "changes":     {metric: % change},
                "log_count":   int,
            }
        """
        today = date.today()
        this_week_start = today - timedelta(days=6)
        last_week_start = today - timedelta(days=13)
        last_week_end   = today - timedelta(days=7)

        this_week_logs = self._get_logs_in_range(user_id, this_week_start, today)
        last_week_logs = self._get_logs_in_range(user_id, last_week_start, last_week_end)

        this_avg = self._compute_averages(this_week_logs)
        last_avg = self._compute_averages(last_week_logs)
        changes  = self._compute_changes(this_avg, last_avg)

        return {
            "this_week": this_avg,
            "last_week": last_avg,
            "changes":   changes,
            "log_count": len(this_week_logs),
        }

    def get_monthly_stats(self, user_id: int) -> dict:
        """
        Compute monthly averages for this month vs. last month.

        Returns:
            {
                "this_month":  {metric: avg},
                "last_month":  {metric: avg},
                "changes":     {metric: % change},
                "log_count":   int,
            }
        """
        today = date.today()
        this_month_start = today - timedelta(days=29)
        last_month_start = today - timedelta(days=59)
        last_month_end   = today - timedelta(days=30)

        this_month_logs = self._get_logs_in_range(user_id, this_month_start, today)
        last_month_logs = self._get_logs_in_range(user_id, last_month_start, last_month_end)

        this_avg = self._compute_averages(this_month_logs)
        last_avg = self._compute_averages(last_month_logs)
        changes  = self._compute_changes(this_avg, last_avg)

        return {
            "this_month": this_avg,
            "last_month": last_avg,
            "changes":    changes,
            "log_count":  len(this_month_logs),
        }

    # ── Updated risk computation ──────────────────────────────────────────

    def compute_updated_risk(self, user_id: int) -> Optional[dict]:
        """
        Overlay the latest daily log onto the user's baseline questionnaire
        and re-run the rule-based disease risk and health score calculations.

        Does NOT create a new Prediction row — results are returned as a dict
        for display only.

        Args:
            user_id: ID of the authenticated user.

        Returns:
            Dict with keys: disease_risks, health_scores, updated_at.
            None if the user has no baseline questionnaire or no daily logs.
        """
        from services.prediction_service import PredictionService

        # Find the most recent completed questionnaire for the user
        baseline_q = (
            Questionnaire.query
            .filter_by(user_id=user_id, is_complete=True)
            .order_by(Questionnaire.created_at.desc())
            .first()
        )
        if baseline_q is None:
            return None

        # Find the most recent daily log
        latest_log = (
            DailyHealthLog.query
            .filter_by(user_id=user_id)
            .order_by(DailyHealthLog.log_date.desc())
            .first()
        )
        if latest_log is None:
            return None

        # Build a merged feature dict: baseline questionnaire + daily log overrides
        features = baseline_q.to_feature_dict()
        features = self._overlay_log_on_features(features, latest_log)

        # Re-run the rule-based engine
        svc = PredictionService(self.app)
        disease_risks  = svc.predict_diseases(features)
        health_scores  = svc.calculate_health_scores(features)

        return {
            "disease_risks":  disease_risks,
            "health_scores":  health_scores,
            "updated_at":     latest_log.log_date.isoformat(),
        }

    def get_progress_comparison(self, user_id: int) -> Optional[dict]:
        """
        Compare the user's baseline Prediction with the latest computed risk.

        Returns:
            {
                "baseline":   {disease: {probability, risk_level}},
                "current":    {disease: {probability, risk_level}},
                "diff":       {disease: % change},
                "improved":   [disease names],
                "worsened":   [disease names],
                "score_baseline":  {score_dim: value},
                "score_current":   {score_dim: value},
                "score_diff":      {score_dim: % change},
            }
            None if insufficient data.
        """
        # Baseline: the first (oldest) completed prediction
        baseline_pred = (
            Prediction.query
            .filter_by(user_id=user_id)
            .order_by(Prediction.created_at.asc())
            .first()
        )
        if baseline_pred is None:
            return None

        updated = self.compute_updated_risk(user_id)
        if updated is None:
            return None

        baseline_risks = {
            k: v["probability"]
            for k, v in baseline_pred.disease_risks.items()
        }
        current_risks = updated["disease_risks"]

        # Compute risk difference (current − baseline)
        diff = {}
        improved = []
        worsened = []

        # Map display disease names to internal keys
        disease_key_map = {
            "Diabetes":       "diabetes",
            "Heart Disease":  "heart_disease",
            "Stroke":         "stroke",
            "Hypertension":   "hypertension",
            "Obesity":        "obesity",
            "Kidney Disease": "kidney_disease",
            "Fatty Liver":    "fatty_liver",
            "Depression":     "depression",
            "Sleep Disorder": "sleep_disorder",
            "Thyroid Disease": "thyroid",
        }

        for display_name, key in disease_key_map.items():
            base_prob    = baseline_risks.get(display_name, 0) or 0
            current_prob = current_risks.get(key, 0) or 0
            change       = round(current_prob - base_prob, 1)
            diff[display_name] = change
            if change < -1:
                improved.append(display_name)
            elif change > 1:
                worsened.append(display_name)

        # Health score comparison
        base_scores = baseline_pred.health_scores
        curr_scores = updated["health_scores"]
        score_diff  = {
            dim: round(
                curr_scores.get(dim, 0) - (base_scores.get(dim) or 0), 1
            )
            for dim in curr_scores
        }

        # ── XAI SHAP & LIME comparison ─────────────────────────────────────
        from ml.shap_explainer import ShapExplainer
        from ml.lime_explainer import LimeExplainer

        baseline_q = Questionnaire.query.filter_by(user_id=user_id, is_complete=True).order_by(Questionnaire.created_at.desc()).first()
        latest_log = DailyHealthLog.query.filter_by(user_id=user_id).order_by(DailyHealthLog.log_date.desc()).first()

        base_feat = baseline_q.to_feature_dict() if baseline_q else {}
        curr_feat = self._overlay_log_on_features(base_feat.copy(), latest_log) if latest_log else base_feat

        xai_shap = ShapExplainer.compare_shap_contributions(base_feat, curr_feat)
        lime_curr = LimeExplainer.explain_instance(curr_feat)

        return {
            "baseline":       baseline_risks,
            "current":        {k.replace("_", " ").title(): v for k, v in current_risks.items()},
            "diff":           diff,
            "improved":       improved,
            "worsened":       worsened,
            "score_baseline": base_scores,
            "score_current":  curr_scores,
            "score_diff":     score_diff,
            "baseline_date":  baseline_pred.created_at.strftime("%b %d, %Y"),
            "current_date":   updated["updated_at"],
            "xai_shap":       xai_shap,
            "lime_curr":      lime_curr,
        }

    # ── AI Health Coach ───────────────────────────────────────────────────

    def get_health_coach_tips(self, user_id: int) -> list[dict]:
        """
        Generate dynamic AI coach messages from the last 7 days of logs.

        Each tip is a dict:
            {
                "icon":     Bootstrap icon class,
                "category": str,
                "message":  str,
                "type":     "success" | "warning" | "info" | "danger",
            }

        Returns:
            List of tip dicts (up to 8), ordered by priority.
        """
        logs = self._get_logs_in_range(
            user_id,
            date.today() - timedelta(days=6),
            date.today(),
        )

        if not logs:
            return [{
                "icon":     "bi-journal-plus",
                "category": "Getting Started",
                "message":  "Start logging your daily health data to receive personalised AI coaching tips.",
                "type":     "info",
            }]

        tips = []
        avgs = self._compute_averages(logs)

        # ── Sleep ──────────────────────────────────────────────────────────
        sleep_avg = avgs.get("sleep_hours", 0)
        if sleep_avg < 6:
            tips.append({
                "icon":     "bi-moon-stars",
                "category": "Sleep",
                "message":  (
                    f"⚠️ Sleep has averaged only {sleep_avg:.1f} hours over the last "
                    f"{len(logs)} day(s). Aim for 7–9 hours to reduce cardiovascular and "
                    "mental health risk."
                ),
                "type": "danger",
            })
        elif sleep_avg >= 7:
            tips.append({
                "icon":     "bi-moon-stars-fill",
                "category": "Sleep",
                "message":  (
                    f"✅ Great sleep consistency! You averaged {sleep_avg:.1f} hours this week. "
                    "Keep it up — quality sleep supports immune function and weight regulation."
                ),
                "type": "success",
            })

        # ── Water ──────────────────────────────────────────────────────────
        water_avg = avgs.get("water_intake", 0)
        if water_avg < 1.5:
            tips.append({
                "icon":     "bi-droplet-half",
                "category": "Hydration",
                "message":  (
                    f"💧 Average water intake is low ({water_avg:.1f} L/day). "
                    "Aim for at least 2.5 L to support kidney function and energy levels."
                ),
                "type": "warning",
            })
        elif water_avg >= 2.5:
            tips.append({
                "icon":     "bi-droplet-fill",
                "category": "Hydration",
                "message":  (
                    f"✅ Excellent hydration! Averaging {water_avg:.1f} L/day. "
                    "Staying hydrated supports skin health and cognitive performance."
                ),
                "type": "success",
            })

        # ── Exercise ───────────────────────────────────────────────────────
        ex_avg = avgs.get("exercise_minutes", 0)
        if ex_avg < 20:
            tips.append({
                "icon":     "bi-bicycle",
                "category": "Exercise",
                "message":  (
                    f"🏃 Exercise is averaging only {ex_avg:.0f} min/day. "
                    "Even 30 minutes of brisk walking daily reduces diabetes risk by up to 30%."
                ),
                "type": "warning",
            })
        elif ex_avg >= 45:
            tips.append({
                "icon":     "bi-trophy",
                "category": "Exercise",
                "message":  (
                    f"🏆 Outstanding! You are exercising {ex_avg:.0f} min/day on average. "
                    "Consistent exercise significantly lowers cardiovascular disease risk."
                ),
                "type": "success",
            })

        # ── Stress ─────────────────────────────────────────────────────────
        stress_avg = avgs.get("stress_level", 0)
        if stress_avg >= 7:
            tips.append({
                "icon":     "bi-emoji-frown",
                "category": "Mental Health",
                "message":  (
                    f"😰 Stress levels have been high (avg {stress_avg:.1f}/10). "
                    "Try 10 minutes of deep breathing or mindfulness meditation daily "
                    "to reduce cortisol and improve heart health."
                ),
                "type": "danger",
            })
        elif stress_avg <= 3:
            tips.append({
                "icon":     "bi-emoji-smile",
                "category": "Mental Health",
                "message":  (
                    f"✅ Excellent stress management (avg {stress_avg:.1f}/10). "
                    "Low stress protects cardiovascular health and immune function."
                ),
                "type": "success",
            })

        # ── Junk food ──────────────────────────────────────────────────────
        junk_count = sum(1 for log in logs if log.junk_food)
        if junk_count >= 4:
            tips.append({
                "icon":     "bi-cup-hot",
                "category": "Diet",
                "message":  (
                    f"🍔 Junk food was consumed {junk_count} out of {len(logs)} days. "
                    "Reducing processed food intake can lower inflammation and decrease "
                    "obesity, diabetes, and heart disease risk."
                ),
                "type": "warning",
            })

        # ── Smoking ────────────────────────────────────────────────────────
        smoking_count = sum(1 for log in logs if log.smoking)
        if smoking_count > 0:
            tips.append({
                "icon":     "bi-x-circle-fill",
                "category": "Habits",
                "message":  (
                    f"🚭 Smoking was logged {smoking_count} day(s) this week. "
                    "Quitting smoking is the single most impactful change you can make "
                    "to reduce stroke, heart disease, and lung cancer risk."
                ),
                "type": "danger",
            })

        # ── Progress comparison tip ────────────────────────────────────────
        progress = self.get_progress_comparison(user_id)
        if progress and progress.get("improved"):
            improved_str = ", ".join(progress["improved"][:3])
            tips.append({
                "icon":     "bi-graph-down-arrow",
                "category": "Disease Risk",
                "message":  (
                    f"📉 Great progress! Your risk for {improved_str} has improved "
                    "compared to your baseline assessment. Keep your current habits."
                ),
                "type": "success",
            })
        elif progress and progress.get("worsened"):
            worsened_str = ", ".join(progress["worsened"][:2])
            tips.append({
                "icon":     "bi-graph-up-arrow",
                "category": "Disease Risk",
                "message":  (
                    f"📈 Risk for {worsened_str} has increased since your baseline. "
                    "Focus on the lifestyle areas highlighted in your progress comparison."
                ),
                "type": "warning",
            })

        return tips[:8]  # Return at most 8 tips

    # ── Chart data ────────────────────────────────────────────────────────

    def get_chart_data(self, user_id: int, days: int = 30) -> dict:
        """
        Build a JSON-serialisable dict of time-series data for Chart.js.

        Args:
            user_id: ID of the authenticated user.
            days:    Number of days of data to include.

        Returns:
            {
                "labels":           [date strings],
                "sleep":            [float],
                "water":            [float],
                "exercise":         [int],
                "weight":           [float],
                "stress":           [int],
                "health_score":     [float],
            }
        """
        logs = self._get_logs_in_range(
            user_id,
            date.today() - timedelta(days=days - 1),
            date.today(),
        )
        # Reverse so oldest → newest for Chart.js
        logs = list(reversed(logs))

        return {
            "labels":       [log.log_date.strftime("%b %d") for log in logs],
            "sleep":        [log.sleep_hours for log in logs],
            "water":        [log.water_intake for log in logs],
            "exercise":     [log.exercise_minutes for log in logs],
            "weight":       [log.weight for log in logs],
            "stress":       [log.stress_level for log in logs],
            "health_score": [log.healthy_habits_score for log in logs],
            "steps":        [log.steps for log in logs],
        }

    # ── Private helpers ───────────────────────────────────────────────────

    def _get_logs_in_range(
        self, user_id: int, start: date, end: date
    ) -> list[DailyHealthLog]:
        """Fetch logs for a user within [start, end] inclusive."""
        return (
            DailyHealthLog.query
            .filter(
                DailyHealthLog.user_id == user_id,
                DailyHealthLog.log_date >= start,
                DailyHealthLog.log_date <= end,
            )
            .order_by(DailyHealthLog.log_date.desc())
            .all()
        )

    def _compute_averages(self, logs: list[DailyHealthLog]) -> dict:
        """
        Compute per-metric averages over a list of log instances.

        Returns a dict of metric → average value (rounded to 1 decimal).
        Returns an empty dict if logs is empty.
        """
        if not logs:
            return {}

        n = len(logs)
        metrics = [
            "sleep_hours", "sleep_quality", "water_intake",
            "exercise_minutes", "steps", "stress_level",
            "fruits", "vegetables", "weight",
        ]
        avgs = {}
        for m in metrics:
            values = [getattr(log, m) for log in logs if getattr(log, m) is not None]
            avgs[m] = round(sum(values) / len(values), 1) if values else 0.0

        # Boolean percentages
        avgs["junk_food_pct"]    = round(sum(1 for l in logs if l.junk_food)    / n * 100, 0)
        avgs["sugary_drink_pct"] = round(sum(1 for l in logs if l.sugary_drinks) / n * 100, 0)
        avgs["smoking_pct"]      = round(sum(1 for l in logs if l.smoking)       / n * 100, 0)
        avgs["alcohol_pct"]      = round(sum(1 for l in logs if l.alcohol)       / n * 100, 0)

        # Average daily health score
        avgs["health_score"] = round(
            sum(log.healthy_habits_score for log in logs) / n, 1
        )

        return avgs

    def _compute_changes(self, current: dict, previous: dict) -> dict:
        """
        Compute percentage change between two average dicts.

        Returns: {metric: % change (can be negative for improvement on stress, etc.)}
        Metrics where an increase is bad (stress, junk food, smoking) are inverted
        so positive % = improvement.
        """
        # Metrics where LOWER is better (positive change = worsening)
        lower_is_better = {
            "stress_level", "junk_food_pct", "sugary_drink_pct",
            "smoking_pct", "alcohol_pct",
        }

        changes = {}
        for key, curr_val in current.items():
            prev_val = previous.get(key, 0)
            if prev_val and prev_val != 0:
                raw_pct = ((curr_val - prev_val) / abs(prev_val)) * 100
                # Invert for metrics where lower is better
                if key in lower_is_better:
                    raw_pct = -raw_pct
                changes[key] = round(raw_pct, 1)
            else:
                changes[key] = 0.0
        return changes

    def _overlay_log_on_features(
        self, features: dict, log: DailyHealthLog
    ) -> dict:
        """
        Merge a daily log's relevant fields into a questionnaire feature dict.

        The log overrides lifestyle fields (sleep, water, exercise, stress)
        while permanent fields (family history, medical history) stay from baseline.

        Args:
            features: Dict from Questionnaire.to_feature_dict().
            log:      Most recent DailyHealthLog instance.

        Returns:
            Updated feature dict.
        """
        # Override dynamic lifestyle features from the latest log
        features["sleep_hours"]    = log.sleep_hours
        features["stress_level"]   = log.stress_level
        features["water_intake_L"] = log.water_intake

        # Map exercise minutes to frequency bucket
        if log.exercise_minutes == 0:
            features["exercise_frequency"] = "Never"
        elif log.exercise_minutes < 30:
            features["exercise_frequency"] = "1-2x per week"
        elif log.exercise_minutes < 60:
            features["exercise_frequency"] = "3-4x per week"
        else:
            features["exercise_frequency"] = "5+ times per week"

        features["exercise_duration_min"] = log.exercise_minutes
        features["daily_steps"]           = log.steps

        # Map diet data
        features["fruit_veg_servings"] = (log.fruits or 0) + (log.vegetables or 0)
        features["fast_food_per_week"]  = 7 if log.junk_food else 0  # daily → weekly
        features["sugar_intake"]        = "High" if log.sugary_drinks else features.get("sugar_intake", "Moderate")

        # Smoking
        if log.smoking:
            features["smoking_status"] = "Current"

        # Alcohol
        if log.alcohol:
            features["alcohol_intake"] = "Moderate"

        # Weight → recalculate BMI if height known
        if log.weight and features.get("bmi") is not None:
            # bmi_height derived from original bmi + weight
            old_bmi    = features.get("bmi", 22)
            old_weight = features.get("weight_kg", log.weight)
            if old_weight and old_bmi:
                h_sq = old_weight / old_bmi  # height² in m²
                features["bmi"] = round(log.weight / h_sq, 2)

        return features
