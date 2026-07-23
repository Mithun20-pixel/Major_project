"""
routes/admin.py - Admin Blueprint
===================================
Handles: Admin login, user management, dataset upload, model retraining,
         prediction statistics, report downloads, and user deletion.
"""

from flask import (
    Blueprint, render_template, redirect,
    url_for, flash, request, jsonify, current_app
)
from flask_login import login_required, current_user
from functools import wraps

from extensions import db
from models.user        import User
from models.prediction  import Prediction
from models.model_log   import ModelLog
from models.report      import Report
from utils.file_utils   import allowed_file, save_uploaded_file

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
    """Admin overview: user count, prediction count, model statuses."""
    stats = {
        "total_users":       User.query.filter_by(is_deleted=False).count(),
        "total_predictions": Prediction.query.count(),
        "active_models":     ModelLog.query.filter_by(is_active=True).count(),
    }
    return render_template("admin/dashboard.html", stats=stats)


# ── User management ────────────────────────────────────────────────────────

@admin_bp.route("/users")
@login_required
@admin_required
def users():
    """Paginated user list."""
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config.get("USERS_PER_PAGE", 20)
    users_page = (
        User.query.filter_by(is_deleted=False)
        .order_by(User.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return render_template("admin/users.html", users=users_page)


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
    """
    Trigger model retraining.
    In Phase 1, this is a stub that will be connected to the ML service in Phase 3.
    """
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
