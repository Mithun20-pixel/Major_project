"""
routes/admin.py - Admin Blueprint & Monitoring System
======================================================
Handles: Admin dashboard, user management, user activity logs,
         detailed user inspection, dataset upload, model retraining,
         and prediction statistics.
"""

from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Blueprint, render_template, redirect,
    url_for, flash, request, jsonify, current_app
)
from flask_login import login_required, current_user

from extensions import db
from models.user            import User
from models.prediction      import Prediction
from models.model_log       import ModelLog
from models.report          import Report
from models.daily_health_log import DailyHealthLog
from models.activity_log   import UserActivityLog
from utils.file_utils       import allowed_file, save_uploaded_file

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


# ── Admin-only decorator ───────────────────────────────────────────────────

def admin_required(f):
    """
    Decorator that checks if the current user has the admin role.
    Returns 403 if not authorised.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            from flask import abort
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ── Admin dashboard ────────────────────────────────────────────────────────

@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    """Admin overview: user count, active users, prediction count, activity logs, and recent feed."""
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)

    stats = {
        "total_users":       User.query.filter_by(is_deleted=False).count(),
        "active_today":      User.query.filter(User.last_login >= cutoff_24h).count(),
        "total_predictions": Prediction.query.count(),
        "total_daily_logs":  DailyHealthLog.query.count(),
        "total_activities":  UserActivityLog.query.count(),
        "active_models":     ModelLog.query.filter_by(is_active=True).count(),
    }

    recent_activities = (
        UserActivityLog.query
        .order_by(UserActivityLog.created_at.desc())
        .limit(10)
        .all()
    )

    recent_users = (
        User.query.filter_by(is_deleted=False)
        .order_by(User.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_activities=recent_activities,
        recent_users=recent_users
    )


# ── User management & Activity Logs ───────────────────────────────────────

@admin_bp.route("/users")
@login_required
@admin_required
def users():
    """Paginated user list with activity metrics."""
    page = request.args.get("page", 1, type=int)
    search_query = request.args.get("q", "").strip()
    per_page = current_app.config.get("USERS_PER_PAGE", 20)

    query = User.query.filter_by(is_deleted=False)

    if search_query:
        query = query.filter(
            (User.full_name.ilike(f"%{search_query}%")) |
            (User.email.ilike(f"%{search_query}%"))
        )

    users_page = (
        query.order_by(User.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return render_template("admin/users.html", users=users_page, q=search_query)


@admin_bp.route("/users/<int:user_id>")
@login_required
@admin_required
def user_detail(user_id: int):
    """
    Detailed profile inspector for a specific user.
    Shows user profile details, activity log history, disease predictions, and daily health logs.
    """
    user = User.query.get_or_404(user_id)

    activity_logs = (
        UserActivityLog.query.filter_by(user_id=user.id)
        .order_by(UserActivityLog.created_at.desc())
        .limit(50)
        .all()
    )

    predictions = (
        Prediction.query.filter_by(user_id=user.id)
        .order_by(Prediction.created_at.desc())
        .limit(10)
        .all()
    )

    daily_logs = (
        DailyHealthLog.query.filter_by(user_id=user.id)
        .order_by(DailyHealthLog.log_date.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "admin/user_detail.html",
        user=user,
        activity_logs=activity_logs,
        predictions=predictions,
        daily_logs=daily_logs
    )


@admin_bp.route("/activities")
@login_required
@admin_required
def activities():
    """Paginated real-time user activity logs feed."""
    page = request.args.get("page", 1, type=int)
    action_filter = request.args.get("action", "").strip()
    search_query = request.args.get("q", "").strip()
    per_page = 30

    query = UserActivityLog.query

    if action_filter:
        query = query.filter(UserActivityLog.action.ilike(f"%{action_filter}%"))

    if search_query:
        query = query.join(User, isouter=True).filter(
            (User.full_name.ilike(f"%{search_query}%")) |
            (User.email.ilike(f"%{search_query}%")) |
            (UserActivityLog.action.ilike(f"%{search_query}%")) |
            (UserActivityLog.details.ilike(f"%{search_query}%")) |
            (UserActivityLog.ip_address.ilike(f"%{search_query}%"))
        )

    logs_page = (
        query.order_by(UserActivityLog.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return render_template(
        "admin/activities.html",
        logs=logs_page,
        action_filter=action_filter,
        q=search_query
    )


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id: int):
    """Soft-delete a user account."""
    user = User.query.get_or_404(user_id)
    user.is_deleted = True
    user.is_active  = False
    db.session.commit()
    flash(f"User {user.email} has been deactivated.", "warning")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_user(user_id: int):
    """Enable or disable a user account."""
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    status = "enabled" if user.is_active else "disabled"
    flash(f"User {user.email} has been {status}.", "info")
    return redirect(url_for("admin.users"))


# ── Dataset upload ─────────────────────────────────────────────────────────

@admin_bp.route("/datasets/upload", methods=["GET", "POST"])
@login_required
@admin_required
def upload_dataset():
    """Upload a CSV / Excel training dataset."""
    if request.method == "POST":
        file = request.files.get("dataset")
        if not file or file.filename == "":
            flash("No file selected.", "danger")
            return redirect(request.url)

        if not allowed_file(file.filename, current_app.config["ALLOWED_EXTENSIONS"]):
            flash("Only CSV and Excel files are allowed.", "danger")
            return redirect(request.url)

        filename = save_uploaded_file(
            file, current_app.config["DATASET_FOLDER"]
        )
        flash(f"Dataset '{filename}' uploaded successfully.", "success")
        return redirect(url_for("admin.upload_dataset"))

    return render_template("admin/upload_dataset.html")


# ── Model retraining ───────────────────────────────────────────────────────

@admin_bp.route("/models/retrain", methods=["GET", "POST"])
@login_required
@admin_required
def retrain_models():
    """Trigger model retraining overview."""
    model_logs = ModelLog.query.order_by(ModelLog.created_at.desc()).limit(50).all()
    return render_template("admin/retrain.html", model_logs=model_logs)


# ── Prediction statistics ──────────────────────────────────────────────────

@admin_bp.route("/statistics")
@login_required
@admin_required
def statistics():
    """Aggregate prediction statistics across all users."""
    total_predictions = Prediction.query.count()
    return render_template(
        "admin/statistics.html",
        total_predictions=total_predictions,
    )
