"""
Authentication blueprint  –  /api/auth/*

Endpoints
---------
POST /api/auth/register   – register a new student
POST /api/auth/login      – obtain JWT access token
GET  /api/auth/me         – return current user info (requires auth)
GET  /api/auth/users      – list all users (admin only)
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
)

from .models import User, db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ── helpers ───────────────────────────────────────────────────────────────────
def _get_current_user() -> User | None:
    uid = get_jwt_identity()
    return db.session.get(User, uid)


def _require_admin(user: User):
    if not user or user.role != "admin":
        return jsonify({"error": "Admin access required."}), 403
    return None


# ── register ──────────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role", "student")

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    if role not in ("student", "admin"):
        return jsonify({"error": "role must be 'student' or 'admin'."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered."}), 409

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=user.id)
    return jsonify({"message": "Registered successfully.", "token": token, "user": user.to_dict()}), 201


# ── login ─────────────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password."}), 401
    if not user.is_active:
        return jsonify({"error": "Account disabled. Contact administrator."}), 403

    token = create_access_token(identity=user.id)
    return jsonify({"token": token, "user": user.to_dict()}), 200


# ── /me ───────────────────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user = _get_current_user()
    if not user:
        return jsonify({"error": "User not found."}), 404
    return jsonify(user.to_dict()), 200


# ── list users (admin) ────────────────────────────────────────────────────────
@auth_bp.route("/users", methods=["GET"])
@jwt_required()
def list_users():
    user = _get_current_user()
    err = _require_admin(user)
    if err:
        return err

    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users]), 200
