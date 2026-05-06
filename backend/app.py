"""
Main Flask application factory for the Proctoring System backend.

Usage
-----
    # development
    flask --app backend.app run --debug

    # production (gunicorn)
    gunicorn backend.app:create_app()

Environment variables
---------------------
FLASK_ENV          development | production  (default: development)
SECRET_KEY         Flask secret key
JWT_SECRET_KEY     JWT signing key
DATABASE_URL       SQLAlchemy connection string (SQLite default)
CORS_ORIGINS       Comma-separated CORS allow-list  (default: *)
ADMIN_EMAIL        Seed admin email  (default: admin@proctor.local)
ADMIN_PASSWORD     Seed admin password  (default: Admin@12345)
"""

import logging
import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from .config import config
from .models import User, db

logger = logging.getLogger(__name__)


def create_app(env: str | None = None) -> Flask:
    env = env or os.environ.get("FLASK_ENV", "development")
    cfg = config.get(env, config["default"])

    app = Flask(__name__, static_folder="../frontend", static_url_path="")
    app.config.from_object(cfg)

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)

    JWTManager(app)

    origins = app.config.get("CORS_ORIGINS", "*")
    if isinstance(origins, str) and origins != "*":
        origins = [o.strip() for o in origins.split(",")]
    CORS(app, resources={r"/api/*": {"origins": origins}})

    # ── Blueprints ────────────────────────────────────────────────────────────
    from .auth import auth_bp
    from .exam import exam_bp
    from .proctoring import proctor_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(exam_bp)
    app.register_blueprint(proctor_bp)

    # ── DB init + seed ────────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        _seed_admin(app)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "env": env}), 200

    # ── SPA catch-all – serve frontend for non-API routes ─────────────────────
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        static_dir = app.static_folder
        if not static_dir:
            return jsonify({"error": "Not found."}), 404
        # Always use send_from_directory which safely validates the path
        # against the static_folder root, preventing path traversal.
        if path and os.path.exists(os.path.join(static_dir, path)):
            return send_from_directory(static_dir, path)
        if os.path.exists(os.path.join(static_dir, "index.html")):
            return send_from_directory(static_dir, "index.html")
        return jsonify({"error": "Not found."}), 404

    return app


def _seed_admin(app: Flask) -> None:
    """Create the default admin account if it doesn't exist."""
    email = app.config["ADMIN_EMAIL"]
    pwd = app.config["ADMIN_PASSWORD"]
    if not User.query.filter_by(email=email).first():
        admin = User(name="Admin", email=email, role="admin")
        admin.set_password(pwd)
        db.session.add(admin)
        db.session.commit()
        logger.info("Seeded admin account: %s", email)


# Allow `python -m backend.app` or `flask run`
app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug)
