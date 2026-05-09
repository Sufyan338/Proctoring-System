"""
Exam blueprint  –  /api/exams/*

Endpoints
---------
POST   /api/exams/                   – create exam (admin)
GET    /api/exams/                   – list all active exams
GET    /api/exams/<id>               – get single exam
DELETE /api/exams/<id>               – delete exam (admin)

POST   /api/exams/<id>/start         – student starts an exam session
POST   /api/exams/sessions/<sid>/end – student ends session
GET    /api/exams/sessions/          – list sessions (admin: all, student: own)
GET    /api/exams/sessions/<sid>     – get single session details + alerts
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .models import Alert, Exam, ExamSession, User, db

exam_bp = Blueprint("exams", __name__, url_prefix="/api/exams")


def _current_user() -> User | None:
    return db.session.get(User, get_jwt_identity())


def _get_entity(model, entity_id: int):
    return db.session.get(model, entity_id)


# ── Create exam ───────────────────────────────────────────────────────────────
@exam_bp.route("/", methods=["POST"])
@jwt_required()
def create_exam():
    user = _current_user()
    if not user or user.role != "admin":
        return jsonify({"error": "Admin access required."}), 403

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required."}), 400

    exam = Exam(
        title=title,
        description=data.get("description", ""),
        duration_minutes=int(data.get("duration_minutes", 60)),
        created_by=user.id,
    )
    db.session.add(exam)
    db.session.commit()
    return jsonify(exam.to_dict()), 201


# ── List exams ────────────────────────────────────────────────────────────────
@exam_bp.route("/", methods=["GET"])
@jwt_required()
def list_exams():
    exams = Exam.query.filter_by(is_active=True).order_by(Exam.created_at.desc()).all()
    return jsonify([e.to_dict() for e in exams]), 200


# ── Get single exam ───────────────────────────────────────────────────────────
@exam_bp.route("/<int:exam_id>", methods=["GET"])
@jwt_required()
def get_exam(exam_id: int):
    exam = _get_entity(Exam, exam_id)
    if not exam:
        return jsonify({"error": "Exam not found."}), 404
    return jsonify(exam.to_dict()), 200


# ── Delete exam ───────────────────────────────────────────────────────────────
@exam_bp.route("/<int:exam_id>", methods=["DELETE"])
@jwt_required()
def delete_exam(exam_id: int):
    user = _current_user()
    if not user or user.role != "admin":
        return jsonify({"error": "Admin access required."}), 403

    exam = _get_entity(Exam, exam_id)
    if not exam:
        return jsonify({"error": "Exam not found."}), 404
    exam.is_active = False
    db.session.commit()
    return jsonify({"message": "Exam deactivated."}), 200


# ── Start session ─────────────────────────────────────────────────────────────
@exam_bp.route("/<int:exam_id>/start", methods=["POST"])
@jwt_required()
def start_session(exam_id: int):
    user = _current_user()
    if not user or user.role != "student":
        return jsonify({"error": "Only students can start exam sessions."}), 403

    exam = Exam.query.filter_by(id=exam_id, is_active=True).first_or_404()

    # Prevent duplicate active sessions
    existing = ExamSession.query.filter_by(
        student_id=user.id, exam_id=exam_id, status="active"
    ).first()
    if existing:
        return jsonify({"message": "Session already active.", "session": existing.to_dict()}), 200

    session = ExamSession(student_id=user.id, exam_id=exam_id)
    db.session.add(session)
    db.session.commit()
    return jsonify(session.to_dict()), 201


# ── End session ───────────────────────────────────────────────────────────────
@exam_bp.route("/sessions/<int:session_id>/end", methods=["POST"])
@jwt_required()
def end_session(session_id: int):
    user = _current_user()
    session = _get_entity(ExamSession, session_id)
    if not session:
        return jsonify({"error": "Session not found."}), 404

    if user.role == "student" and session.student_id != user.id:
        return jsonify({"error": "Forbidden."}), 403

    session.ended_at = datetime.now(timezone.utc).replace(tzinfo=None)
    alert_cnt = session.alerts.count()
    session.alert_count = alert_cnt
    session.status = "flagged" if alert_cnt > 3 else "completed"
    db.session.commit()
    return jsonify(session.to_dict()), 200


# ── List sessions ─────────────────────────────────────────────────────────────
@exam_bp.route("/sessions/", methods=["GET"])
@jwt_required()
def list_sessions():
    user = _current_user()
    if user.role == "admin":
        sessions = ExamSession.query.order_by(ExamSession.started_at.desc()).all()
    else:
        sessions = (
            ExamSession.query.filter_by(student_id=user.id)
            .order_by(ExamSession.started_at.desc())
            .all()
        )
    return jsonify([s.to_dict() for s in sessions]), 200


# ── Get session detail ────────────────────────────────────────────────────────
@exam_bp.route("/sessions/<int:session_id>", methods=["GET"])
@jwt_required()
def get_session(session_id: int):
    user = _current_user()
    session = _get_entity(ExamSession, session_id)
    if not session:
        return jsonify({"error": "Session not found."}), 404

    if user.role == "student" and session.student_id != user.id:
        return jsonify({"error": "Forbidden."}), 403

    data = session.to_dict()
    data["alerts"] = [a.to_dict() for a in session.alerts.order_by(Alert.timestamp.asc()).all()]
    return jsonify(data), 200
