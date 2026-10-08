"""
extensions.py - Flask Extension Instances
==========================================
All Flask extension objects are instantiated here (unbound).
They are registered with the app in app.py via init_app().

Importing from this module instead of from 'app' breaks the
circular import chain:
    app.py → models → app.py  (CIRCULAR)
    app.py → models → extensions.py  (SAFE)
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db            = SQLAlchemy()
login_manager = LoginManager()
csrf          = CSRFProtect()
mail          = Mail()
bcrypt        = Bcrypt()
migrate       = Migrate()
jwt           = JWTManager()
cors          = CORS()
