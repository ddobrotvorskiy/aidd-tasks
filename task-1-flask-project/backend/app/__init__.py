from __future__ import annotations

import os
from datetime import timedelta

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()


def create_app(config_override: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=False)

    from app.config import settings

    app.config["SQLALCHEMY_DATABASE_URI"] = settings.SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["JWT_SECRET_KEY"] = settings.JWT_SECRET_KEY
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRES_MINUTES
    )
    app.config["MAX_CONTENT_LENGTH"] = settings.MAX_CONTENT_LENGTH
    app.config["UPLOAD_FOLDER"] = settings.UPLOAD_FOLDER

    if config_override:
        app.config.update(config_override)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from app.routes.auth import auth_bp
    from app.routes.employees import employees_bp
    from app.routes.profile import profile_bp
    from app.routes.uploads import uploads_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(employees_bp, url_prefix="/api/employees")
    app.register_blueprint(profile_bp, url_prefix="/api/profile")
    app.register_blueprint(uploads_bp)

    from app.routes.errors import register_error_handlers

    register_error_handlers(app)

    return app
