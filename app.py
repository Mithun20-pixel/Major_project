"""
app.py - Application Factory
=============================
Creates and configures the Flask application using the factory pattern.

Usage:
    from app import create_app
    app = create_app('development')
    app.run()
"""

import os
from flask import Flask, render_template

from config import get_config

# ── Extension instances (imported from extensions.py to avoid circular imports) ──
from extensions import db, login_manager, csrf, mail, bcrypt, migrate



def create_app(env: str = None) -> Flask:
    """
    Application factory function.

    Args:
        env: Environment name ('development', 'testing', 'production').
             Reads FLASK_ENV from environment if not supplied.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # ── Load configuration ─────────────────────────────────────────────────
    cfg = get_config(env)
    app.config.from_object(cfg)

    # ── Ensure required directories exist ─────────────────────────────────
    _create_directories(app)

    # ── Initialise Flask extensions ────────────────────────────────────────
    _init_extensions(app)

    # ── Register Blueprints ────────────────────────────────────────────────
    _register_blueprints(app)

    # ── Register error handlers ────────────────────────────────────────────
    _register_error_handlers(app)

    # ── Shell context for `flask shell` ───────────────────────────────────
    _register_shell_context(app)

    return app


# ── Private helpers ────────────────────────────────────────────────────────

def _create_directories(app: Flask) -> None:
    """Create runtime directories if they do not already exist."""
    dirs = [
        app.config["UPLOAD_FOLDER"],
        app.config["DATASET_FOLDER"],
        app.config["REPORTS_FOLDER"],
        app.config["MODELS_FOLDER"],
    ]
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)


def _init_extensions(app: Flask) -> None:
    """Bind all Flask extensions to the application instance."""
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    # Configure Flask-Login behaviour
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id: int):
        """Load user from DB for Flask-Login session management."""
        from models.user import User
        return User.query.get(int(user_id))


def _register_blueprints(app: Flask) -> None:
    """Import and register all application Blueprints."""
    from routes.auth    import auth_bp
    from routes.main    import main_bp
    from routes.predict import predict_bp
    from routes.admin   import admin_bp
    from routes.api     import api_bp
    from routes.tracker import tracker_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp,    url_prefix="/auth")
    app.register_blueprint(predict_bp, url_prefix="/predict")
    app.register_blueprint(admin_bp,   url_prefix="/admin")
    app.register_blueprint(api_bp,     url_prefix="/api/v1")
    app.register_blueprint(tracker_bp)


def _register_error_handlers(app: Flask) -> None:
    """Register custom HTTP error page handlers."""

    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500


def _register_shell_context(app: Flask) -> None:
    """Push models into the Flask shell context for convenience."""

    @app.shell_context_processor
    def make_shell_context():
        from models.user           import User
        from models.questionnaire  import Questionnaire
        from models.prediction     import Prediction
        from models.recommendation import Recommendation
        from models.report         import Report
        from models.model_log      import ModelLog
        from models.admin          import Admin
        from models.daily_health_log import DailyHealthLog
        return {
            "db": db,
            "User": User,
            "Questionnaire": Questionnaire,
            "Prediction": Prediction,
            "Recommendation": Recommendation,
            "Report": Report,
            "ModelLog": ModelLog,
            "Admin": Admin,
            "DailyHealthLog": DailyHealthLog,
        }


# ── Entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    env_name = os.environ.get("FLASK_ENV", "development")
    application = create_app(env_name)
    application.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=application.config["DEBUG"],
    )
