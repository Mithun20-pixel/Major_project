"""
routes/main.py - Main / Dashboard Blueprint
============================================
Handles: Landing page, User Dashboard, Profile, History, Report download.
"""

from flask import (
    Blueprint, render_template, redirect,
    url_for, flash, request, abort, send_from_directory,
    current_app
)
from flask_login import login_required, current_user
from sqlalchemy import desc

from extensions import db
from models.user        import User
from models.prediction  import Prediction
from models.report      import Report
from forms.profile      import ProfileUpdateForm

main_bp = Blueprint("main", __name__, template_folder="../templates/main")


# ── Landing page ───────────────────────────────────────────────────────────

@main_bp.route("/")
def index():
    """Public landing page."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("main/index.html")


# ── Dashboard ──────────────────────────────────────────────────────────────

@main_bp.route("/dashboard")
@login_required
def dashboard():
    """
    User dashboard showing:
    - Latest prediction summary
    - Health score gauges
    - Prediction history chart
    - Recent recommendations
    - Daily Health Log CTA
    """
    from models.daily_health_log import DailyHealthLog
    from datetime import date

    # Last 5 predictions for the history panel
    recent_predictions = (
        Prediction.query
        .filter_by(user_id=current_user.id)
        .order_by(desc(Prediction.created_at))
        .limit(5)
        .all()
    )

    # Latest prediction (for main gauges/charts)
    latest = recent_predictions[0] if recent_predictions else None

    # Today's daily log (if any)
    today_log = DailyHealthLog.query.filter_by(
        user_id=current_user.id, log_date=date.today()
    ).first()

    return render_template(
        "main/dashboard.html",
        latest_prediction=latest,
        recent_predictions=recent_predictions,
        today_log=today_log,
    )



# ── Prediction History ─────────────────────────────────────────────────────

@main_bp.route("/history")
@login_required
def history():
    """
    Paginated table of all past predictions for the current user.
    """
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config.get("PREDICTIONS_PER_PAGE", 10)

    predictions = (
        Prediction.query
        .filter_by(user_id=current_user.id)
        .order_by(desc(Prediction.created_at))
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return render_template("main/history.html", predictions=predictions)


# ── Profile ────────────────────────────────────────────────────────────────

@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """
    Allow the user to update their personal details and profile photo.
    """
    form = ProfileUpdateForm(obj=current_user)

    if form.validate_on_submit():
        current_user.full_name = form.full_name.data.strip()
        current_user.age       = form.age.data
        current_user.gender    = form.gender.data
        current_user.height_cm = form.height_cm.data
        current_user.weight_kg = form.weight_kg.data
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("main.profile"))

    return render_template("main/profile.html", form=form)


# ── Download Health Report ─────────────────────────────────────────────────

@main_bp.route("/reports/download/<int:report_id>")
@login_required
def download_report(report_id: int):
    """
    Serve a PDF report file.
    Ensures the requesting user owns the report (no IDOR vulnerability).
    """
    report = Report.query.filter_by(
        id=report_id, user_id=current_user.id
    ).first_or_404()

    return send_from_directory(
        current_app.config["REPORTS_FOLDER"],
        report.file_name,
        as_attachment=True,
        download_name=report.file_name,
    )


# ── About / Info ───────────────────────────────────────────────────────────

@main_bp.route("/about")
def about():
    """Static about page describing the application."""
    return render_template("main/about.html")
