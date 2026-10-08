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
from extensions import db, login_manager, csrf, mail, bcrypt, migrate, jwt, cors



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

    # ── Seed default admin account ─────────────────────────────────────────
    _seed_default_admin(app)

    return app


# ── Private helpers ────────────────────────────────────────────────────────

def _seed_default_admin(app: Flask) -> None:
    """Ensure database tables exist and default admin user admin@healthai.com is present."""
    with app.app_context():
        try:
            db.create_all()

            # Ensure questionnaires table has cigarettes_per_day column (for existing DBs)
            try:
                from sqlalchemy import inspect, text
                inspector = inspect(db.engine)
                if "questionnaires" in inspector.get_table_names():
                    cols = [c["name"] for c in inspector.get_columns("questionnaires")]
                    if "cigarettes_per_day" not in cols:
                        db.session.execute(text("ALTER TABLE questionnaires ADD COLUMN cigarettes_per_day INTEGER NULL"))
                        db.session.commit()
            except Exception as migration_err:
                app.logger.warning(f"Schema migration warning: {migration_err}")

            from models.user import User
            from models.admin import Admin

            admin_email = "admin@healthai.com"
            admin_user = User.query.filter_by(email=admin_email).first()
            if not admin_user:
                admin_user = User(
                    full_name="System Administrator",
                    email=admin_email,
                    role="admin",
                    is_email_verified=True,
                    is_active=True,
                    age=30,
                    gender="Other",
                )
                admin_user.password = "Admin@1234"
                db.session.add(admin_user)
                db.session.commit()

            if not Admin.query.filter_by(email=admin_email).first():
                admin_record = Admin(
                    full_name="System Administrator",
                    email=admin_email,
                    is_active=True,
                )
                admin_record.password = "Admin@1234"
                db.session.add(admin_record)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[AdminSeed] Error seeding admin account: {e}")

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
    jwt.init_app(app)

    cors_origins = app.config.get("CORS_ORIGINS", "*")
    cors.init_app(app, resources={r"/api/mobile/*": {"origins": cors_origins}})

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
    from routes.api_mobile import api_mobile_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp,    url_prefix="/auth")
    app.register_blueprint(predict_bp, url_prefix="/predict")
    app.register_blueprint(admin_bp,   url_prefix="/admin")
    app.register_blueprint(api_bp,     url_prefix="/api/v1")
    app.register_blueprint(tracker_bp)
    app.register_blueprint(api_mobile_bp, url_prefix="/api/mobile")

    # Exempt the mobile API from CSRF protection as it uses JWT
    csrf.exempt(api_mobile_bp)


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
