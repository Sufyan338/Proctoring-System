"""
Configuration settings for the Proctoring System backend.
Reads from environment variables with sane defaults for development.
"""

import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production-xyz123")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-change-in-production-abc456")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    # ── Database ──────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'proctoring.db')}",
    )
    # Render / Railway provide a postgres:// URI; SQLAlchemy needs postgresql://
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins (set in env for production)
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    # ── Frame analysis ────────────────────────────────────────────────────────
    # Max uploaded frame size in bytes (1 MB default)
    MAX_FRAME_SIZE = int(os.environ.get("MAX_FRAME_SIZE", 1_048_576))

    # ── Alert thresholds ──────────────────────────────────────────────────────
    # Seconds without a face before generating a "no face" alert
    NO_FACE_THRESHOLD = int(os.environ.get("NO_FACE_THRESHOLD", 5))

    # ── Admin defaults ────────────────────────────────────────────────────────
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@proctor.local")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@12345")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


# Active configuration resolved by FLASK_ENV
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
