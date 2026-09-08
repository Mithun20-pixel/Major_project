"""
utils/activity_tracker.py - User Activity Tracking Utility
============================================================
Provides helper function log_user_activity() to record user actions (logins, predictions, daily logs).
"""

from flask import request
from extensions import db
from models.activity_log import UserActivityLog


def log_user_activity(user, action: str, details: str = None) -> UserActivityLog | None:
    """
    Log a user activity to the database.

    Args:
        user: The User ORM object (or None for guest/anonymous).
        action: Short string description of the action (e.g., "Logged In", "Ran Risk Prediction").
        details: Additional contextual metadata or summary.

    Returns:
        UserActivityLog instance if successfully logged, or None on failure.
    """
    try:
        user_id = user.id if user and hasattr(user, "id") else None

        # Capture IP address and browser User-Agent
        ip_address = request.remote_addr if request else None
        if request and request.headers.get("X-Forwarded-For"):
            ip_address = request.headers.get("X-Forwarded-For").split(",")[0].strip()

        user_agent = request.user_agent.string if request and request.user_agent else None
        if user_agent and len(user_agent) > 250:
            user_agent = user_agent[:250] + "..."

        activity = UserActivityLog(
            user_id    = user_id,
            action     = action,
            details    = details,
            ip_address = ip_address,
            user_agent = user_agent,
        )

        db.session.add(activity)
        db.session.commit()
        return activity
    except Exception as e:
        db.session.rollback()
        print(f"[ActivityTracker] Error logging activity: {e}")
        return None
