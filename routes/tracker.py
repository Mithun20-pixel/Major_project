"""
routes/tracker.py - Daily Health Tracker Blueprint
====================================================
Handles all routes for the Daily Lifestyle Tracking & Health Progress
Monitoring module.

Routes:
    GET  /tracker/log            → Show daily log form (or "already logged" message)
    POST /tracker/log            → Validate + save daily log
    GET  /tracker/progress       → Health progress dashboard
    GET  /tracker/weekly         → Weekly summary page
    GET  /tracker/monthly        → Monthly summary page
    GET  /tracker/comparison     → Baseline vs. current comparison
    GET  /tracker/coach          → AI Health Coach recommendations
    GET  /tracker/api/chart-data → JSON endpoint for Chart.js trend data
    GET  /tracker/reports/weekly → Generate + download weekly PDF report
    GET  /tracker/reports/monthly→ Generate + download monthly PDF report

All routes require authentication.
Users can only access their own data (enforced via current_user.id).
"""

import io
import json
from datetime import date, timedelta

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify, current_app, send_file
)
from flask_login import login_required, current_user

from extensions import db
from forms.daily_log import DailyHealthLogForm
from services.tracker_service import TrackerService


tracker_bp = Blueprint(
    "tracker",
    __name__,
    template_folder="../templates/tracker",
    url_prefix="/tracker",
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_service() -> TrackerService:
    """Create a TrackerService bound to the current Flask app."""
    return TrackerService(current_app._get_current_object())


# ── Daily Log Form ─────────────────────────────────────────────────────────

@tracker_bp.route("/log", methods=["GET", "POST"])
@login_required
def log_form():
    """
    Display the daily health log form and handle submission.

    GET:  Render the multi-section log form. If today has already been logged,
          display an info message and disable the form.
    POST: Validate inputs, prevent duplicates, persist via TrackerService,
          and redirect to the progress dashboard.
    """
    service   = _get_service()
    today_log = service.get_today_log(current_user.id)

    # If already logged today, show a confirmation view
    if today_log and request.method == "GET":
        return render_template(
            "tracker/log_form.html",
            form=None,
            today_log=today_log,
            already_logged=True,
        )

    form = DailyHealthLogForm()

    if form.validate_on_submit():
        try:
            log = service.save_log(current_user.id, form)
            flash(
                f"✅ Daily health log for {log.log_date.strftime('%B %d, %Y')} saved! "
                "Your progress has been updated.",
                "success",
            )
            return redirect(url_for("tracker.progress"))

        except ValueError as exc:
            flash(str(exc), "warning")

    return render_template(
        "tracker/log_form.html",
        form=form,
        today_log=None,
        already_logged=False,
    )


# ── Health Progress Dashboard ──────────────────────────────────────────────

@tracker_bp.route("/progress")
@login_required
def progress():
    """
    Health Progress Dashboard.

    Displays:
    - Overall health score
    - Current disease risk
    - Weekly + monthly progress summary cards
    - Streak counter
    - Trend chart data (passed as JSON for Chart.js)
    - AI coach tip preview (top 3)
    """
    service = _get_service()

    recent_logs    = service.get_logs(current_user.id, days=30)
    weekly_stats   = service.get_weekly_stats(current_user.id)
    monthly_stats  = service.get_monthly_stats(current_user.id)
    updated_risk   = service.compute_updated_risk(current_user.id)
    streak         = service.get_log_streak(current_user.id)
    coach_tips     = service.get_health_coach_tips(current_user.id)[:3]
    chart_data     = service.get_chart_data(current_user.id, days=30)
    today_log      = service.get_today_log(current_user.id)

    return render_template(
        "tracker/progress.html",
        recent_logs   = recent_logs,
        weekly_stats  = weekly_stats,
        monthly_stats = monthly_stats,
        updated_risk  = updated_risk,
        streak        = streak,
        coach_tips    = coach_tips,
        chart_data    = json.dumps(chart_data),
        today_log     = today_log,
        log_count     = len(recent_logs),
    )


# ── Weekly Summary ─────────────────────────────────────────────────────────

@tracker_bp.route("/weekly")
@login_required
def weekly_summary():
    """
    Detailed weekly summary page.

    Shows 7-day log table, averages, and improvement percentages
    compared to the previous week.
    """
    service      = _get_service()
    weekly_stats = service.get_weekly_stats(current_user.id)
    chart_data   = service.get_chart_data(current_user.id, days=7)
    logs         = service.get_logs(current_user.id, days=7)

    return render_template(
        "tracker/weekly.html",
        weekly_stats = weekly_stats,
        chart_data   = json.dumps(chart_data),
        logs         = logs,
    )


# ── Monthly Summary ────────────────────────────────────────────────────────

@tracker_bp.route("/monthly")
@login_required
def monthly_summary():
    """
    Detailed monthly summary page.

    Shows 30-day log table, averages, improvement percentage,
    and monthly trend charts.
    """
    service       = _get_service()
    monthly_stats = service.get_monthly_stats(current_user.id)
    chart_data    = service.get_chart_data(current_user.id, days=30)
    logs          = service.get_logs(current_user.id, days=30)

    return render_template(
        "tracker/monthly.html",
        monthly_stats = monthly_stats,
        chart_data    = json.dumps(chart_data),
        logs          = logs,
    )


# ── Progress Comparison ────────────────────────────────────────────────────

@tracker_bp.route("/comparison")
@login_required
def comparison():
    """
    Side-by-side comparison of baseline prediction vs. current risk.

    Highlights diseases that improved or worsened and shows
    health score delta.
    """
    service    = _get_service()
    comparison = service.get_progress_comparison(current_user.id)

    return render_template(
        "tracker/comparison.html",
        comparison = comparison,
    )


# ── AI Health Coach ────────────────────────────────────────────────────────

@tracker_bp.route("/coach")
@login_required
def coach():
    """
    AI Health Coach page.

    Displays personalised dynamic recommendations derived from the
    last 7 days of health logs.
    """
    service    = _get_service()
    tips       = service.get_health_coach_tips(current_user.id)
    weekly     = service.get_weekly_stats(current_user.id)
    comparison = service.get_progress_comparison(current_user.id)

    return render_template(
        "tracker/coach.html",
        tips       = tips,
        weekly     = weekly,
        comparison = comparison,
    )


# ── JSON Chart Data Endpoint ───────────────────────────────────────────────

@tracker_bp.route("/api/chart-data")
@login_required
def chart_data_api():
    """
    JSON endpoint for Chart.js trend data.

    Query params:
        days (int, default=30): How many days of history to return.

    Returns:
        JSON object with labels and per-metric arrays.
    """
    days    = request.args.get("days", 30, type=int)
    days    = max(7, min(90, days))  # clamp to 7–90 range
    service = _get_service()
    data    = service.get_chart_data(current_user.id, days=days)
    return jsonify(data)


# ── PDF Report: Weekly ─────────────────────────────────────────────────────

@tracker_bp.route("/reports/weekly")
@login_required
def weekly_report():
    """
    Generate and stream a weekly PDF health report for download.

    The report includes:
    - Lifestyle summary (7-day averages)
    - Disease risk comparison table
    - Personalised recommendations
    - Medical disclaimer
    """
    service       = _get_service()
    weekly_stats  = service.get_weekly_stats(current_user.id)
    logs          = service.get_logs(current_user.id, days=7)
    tips          = service.get_health_coach_tips(current_user.id)
    comparison    = service.get_progress_comparison(current_user.id)

    pdf_bytes = _generate_pdf_report(
        report_type  = "Weekly",
        user         = current_user,
        stats        = weekly_stats,
        logs         = logs,
        tips         = tips,
        comparison   = comparison,
    )

    filename = f"weekly_health_report_{date.today().isoformat()}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype     = "application/pdf",
        as_attachment= True,
        download_name= filename,
    )


# ── PDF Report: Monthly ────────────────────────────────────────────────────

@tracker_bp.route("/reports/monthly")
@login_required
def monthly_report():
    """
    Generate and stream a monthly PDF health report for download.

    The report includes:
    - 30-day lifestyle averages
    - Full disease risk comparison table
    - AI coach recommendations
    - Progress analysis
    - Medical disclaimer
    """
    service       = _get_service()
    monthly_stats = service.get_monthly_stats(current_user.id)
    logs          = service.get_logs(current_user.id, days=30)
    tips          = service.get_health_coach_tips(current_user.id)
    comparison    = service.get_progress_comparison(current_user.id)

    pdf_bytes = _generate_pdf_report(
        report_type  = "Monthly",
        user         = current_user,
        stats        = monthly_stats,
        logs         = logs,
        tips         = tips,
        comparison   = comparison,
    )

    filename = f"monthly_health_report_{date.today().isoformat()}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype     = "application/pdf",
        as_attachment= True,
        download_name= filename,
    )


# ── PDF Generation ─────────────────────────────────────────────────────────

def _generate_pdf_report(
    report_type: str,
    user,
    stats: dict,
    logs: list,
    tips: list,
    comparison,
) -> bytes:
    """
    Build a PDF health report using ReportLab and return raw bytes.

    Args:
        report_type: "Weekly" or "Monthly"
        user:        Current user ORM instance.
        stats:       Dict from get_weekly_stats() or get_monthly_stats().
        logs:        List of DailyHealthLog instances.
        tips:        AI coach tip dicts.
        comparison:  Progress comparison dict (may be None).

    Returns:
        Raw PDF bytes.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable,
    )

    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(
        buf,
        pagesize   = A4,
        leftMargin = 2 * cm,
        rightMargin= 2 * cm,
        topMargin  = 2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()

    # ── Custom styles ──────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "Title",
        parent    = styles["Heading1"],
        fontSize  = 22,
        textColor = colors.HexColor("#6C63FF"),
        spaceAfter= 6,
    )
    heading2 = ParagraphStyle(
        "H2",
        parent    = styles["Heading2"],
        fontSize  = 14,
        textColor = colors.HexColor("#4ecdc4"),
        spaceBefore= 14,
        spaceAfter = 6,
    )
    normal = styles["Normal"]
    small  = ParagraphStyle("small", parent=normal, fontSize=9, textColor=colors.grey)

    # ── Build elements ─────────────────────────────────────────────────────
    story = []

    # Cover
    story.append(Paragraph(f"🩺 HealthAI – {report_type} Health Report", title_style))
    story.append(Paragraph(
        f"<b>User:</b> {user.full_name} &nbsp;|&nbsp; "
        f"<b>Email:</b> {user.email} &nbsp;|&nbsp; "
        f"<b>Generated:</b> {date.today().strftime('%B %d, %Y')}",
        normal,
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#6C63FF")))
    story.append(Spacer(1, 0.4 * cm))

    # ── Lifestyle Summary ──────────────────────────────────────────────────
    story.append(Paragraph(f"{report_type} Lifestyle Summary", heading2))

    period_key = "this_week" if report_type == "Weekly" else "this_month"
    avgs = stats.get(period_key, {})

    if avgs:
        tbl_data = [["Metric", "Average", "Target", "Status"]]
        metric_config = [
            ("sleep_hours",       "Sleep (hours)",        "7–9 hrs"),
            ("water_intake",      "Water Intake (L)",     "≥ 2.5 L"),
            ("exercise_minutes",  "Exercise (min)",       "≥ 30 min"),
            ("steps",             "Steps Walked",         "≥ 10,000"),
            ("stress_level",      "Stress Level (1–10)",  "≤ 5"),
            ("fruits",            "Fruit Servings",       "≥ 3"),
            ("vegetables",        "Vegetables Servings",  "≥ 3"),
            ("health_score",      "Daily Health Score",   "≥ 70"),
        ]
        targets_good = {
            "sleep_hours": lambda v: 7 <= v <= 9,
            "water_intake": lambda v: v >= 2.5,
            "exercise_minutes": lambda v: v >= 30,
            "steps": lambda v: v >= 10000,
            "stress_level": lambda v: v <= 5,
            "fruits": lambda v: v >= 3,
            "vegetables": lambda v: v >= 3,
            "health_score": lambda v: v >= 70,
        }
        for key, label, target in metric_config:
            val = avgs.get(key, "–")
            if isinstance(val, float):
                val_str = f"{val:.1f}"
            else:
                val_str = str(val)
            check = targets_good.get(key)
            try:
                status = "✅ Good" if check and check(float(val_str)) else "⚠️ Improve"
            except Exception:
                status = "–"
            tbl_data.append([label, val_str, target, status])

        tbl = Table(tbl_data, colWidths=[6 * cm, 3 * cm, 3 * cm, 3 * cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#6C63FF")),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f8ff")]),
            ("GRID",        (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph("No lifestyle data available for this period.", normal))

    story.append(Spacer(1, 0.5 * cm))

    # ── Disease Risk Comparison ────────────────────────────────────────────
    if comparison:
        story.append(Paragraph("Disease Risk Comparison", heading2))
        risk_data = [["Disease", "Baseline Risk", "Current Risk", "Change"]]
        for disease, change in (comparison.get("diff") or {}).items():
            base_prob = (comparison.get("baseline") or {}).get(disease, "–")
            curr_prob = (comparison.get("current") or {}).get(disease, "–")
            if isinstance(base_prob, (int, float)):
                base_str = f"{base_prob:.1f}%"
            else:
                base_str = str(base_prob)
            if isinstance(curr_prob, (int, float)):
                curr_str = f"{curr_prob:.1f}%"
            else:
                curr_str = str(curr_prob)
            arrow    = "↓" if change < 0 else ("↑" if change > 0 else "→")
            risk_data.append([disease, base_str, curr_str, f"{arrow} {abs(change):.1f}%"])

        if len(risk_data) > 1:
            rtbl = Table(risk_data, colWidths=[5.5 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm])
            rtbl.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#4ecdc4")),
                ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
                ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0ffff")]),
                ("GRID",        (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("FONTSIZE",    (0, 0), (-1, -1), 9),
            ]))
            story.append(rtbl)

    story.append(Spacer(1, 0.5 * cm))

    # ── AI Coach Recommendations ───────────────────────────────────────────
    if tips:
        story.append(Paragraph("AI Health Coach Recommendations", heading2))
        for tip in tips:
            story.append(Paragraph(f"• {tip['message']}", normal))
            story.append(Spacer(1, 0.2 * cm))

    story.append(Spacer(1, 0.5 * cm))

    # ── Medical Disclaimer ─────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "⚕️ <b>Medical Disclaimer:</b> This report is generated by an AI-based system "
        "for educational and informational purposes only. It is NOT a substitute for "
        "professional medical advice, diagnosis, or treatment. Always consult a qualified "
        "healthcare provider with any questions regarding your health.",
        small,
    ))

    doc.build(story)
    return buf.getvalue()
