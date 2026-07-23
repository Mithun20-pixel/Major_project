"""
routes/api.py - REST API Blueprint (v1)
=========================================
JSON endpoints consumed by the frontend charts and AJAX calls.
All endpoints are login-required.
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc

from models.prediction     import Prediction
from models.questionnaire  import Questionnaire

api_bp = Blueprint("api", __name__)


# ── Health Score data ──────────────────────────────────────────────────────

@api_bp.route("/health-scores/<int:prediction_id>")
@login_required
def health_scores(prediction_id: int):
    """Return health scores as JSON for gauge charts."""
    pred = Prediction.query.filter_by(
        id=prediction_id, user_id=current_user.id
    ).first_or_404()
    return jsonify({"success": True, "data": pred.health_scores})


# ── Disease risk data ──────────────────────────────────────────────────────

@api_bp.route("/disease-risks/<int:prediction_id>")
@login_required
def disease_risks(prediction_id: int):
    """Return disease probabilities as JSON for risk charts."""
    pred = Prediction.query.filter_by(
        id=prediction_id, user_id=current_user.id
    ).first_or_404()
    return jsonify({"success": True, "data": pred.disease_risks})


# ── Historical trend data ──────────────────────────────────────────────────

@api_bp.route("/history-trend")
@login_required
def history_trend():
    """
    Return the last N predictions' overall health score for a line chart.
    Query param: n (default 10)
    """
    n = min(request.args.get("n", 10, type=int), 50)
    predictions = (
        Prediction.query
        .filter_by(user_id=current_user.id)
        .order_by(desc(Prediction.created_at))
        .limit(n)
        .all()
    )
    data = [
        {
            "date":          p.created_at.strftime("%Y-%m-%d"),
            "health_score":  p.overall_health_score,
            "prediction_id": p.id,
        }
        for p in reversed(predictions)
    ]
    return jsonify({"success": True, "data": data})


# ── Latest prediction summary ──────────────────────────────────────────────

@api_bp.route("/latest-prediction")
@login_required
def latest_prediction():
    """Return the most recent prediction as JSON."""
    pred = (
        Prediction.query
        .filter_by(user_id=current_user.id)
        .order_by(desc(Prediction.created_at))
        .first()
    )
    if not pred:
        return jsonify({"success": False, "message": "No predictions found."}), 404
    return jsonify({"success": True, "data": pred.to_dict()})


# ── Admin stats (admin only) ───────────────────────────────────────────────

@api_bp.route("/admin/stats")
@login_required
def admin_stats():
    """Return aggregate statistics for admin charts."""
    if not current_user.is_admin:
        return jsonify({"error": "Forbidden"}), 403

    from models.user      import User
    from models.model_log import ModelLog

    return jsonify({
        "total_users":       User.query.filter_by(is_deleted=False).count(),
        "total_predictions": Prediction.query.count(),
        "active_models":     ModelLog.query.filter_by(is_active=True).count(),
    })


# ── Tracker: Paginated daily logs ─────────────────────────────────────────

@api_bp.route("/tracker/logs")
@login_required
def tracker_logs():
    """
    Return paginated daily health logs for the current user.

    Query params:
        page  (int, default=1)
        per_page (int, default=10, max=30)
        days  (int, default=30) — how many days back to look

    Returns:
        JSON: {success, data: [log dicts], total, page, pages}
    """
    from models.daily_health_log import DailyHealthLog
    from datetime import date, timedelta

    page     = request.args.get("page",     1,  type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 30)
    days     = min(request.args.get("days",  30, type=int), 90)
    cutoff   = date.today() - timedelta(days=days)

    paginated = (
        DailyHealthLog.query
        .filter(
            DailyHealthLog.user_id  == current_user.id,
            DailyHealthLog.log_date >= cutoff,
        )
        .order_by(DailyHealthLog.log_date.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify({
        "success": True,
        "data":    [log.to_dict() for log in paginated.items],
        "total":   paginated.total,
        "page":    paginated.page,
        "pages":   paginated.pages,
    })


# ── Tracker: Weekly + Monthly stats ───────────────────────────────────────

@api_bp.route("/tracker/stats")
@login_required
def tracker_stats():
    """
    Return weekly and monthly aggregated statistics for the current user.

    Returns:
        JSON: {success, weekly: {...}, monthly: {...}}
    """
    from services.tracker_service import TrackerService

    service = TrackerService(current_app._get_current_object())
    return jsonify({
        "success": True,
        "weekly":  service.get_weekly_stats(current_user.id),
        "monthly": service.get_monthly_stats(current_user.id),
    })
