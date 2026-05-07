"""
Proctoring blueprint  –  /api/proctor/*

Endpoints
---------
POST /api/proctor/analyse          – analyse a webcam frame
POST /api/proctor/alert            – manually log an alert (e.g. tab-switch)
GET  /api/proctor/alerts           – list alerts (admin: all, student: own sessions)
GET  /api/proctor/stats            – dashboard summary statistics (admin)
"""

import base64
import logging
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .ai import FaceDetector
from .models import Alert, ExamSession, User, db

logger = logging.getLogger(__name__)
proctor_bp = Blueprint("proctor", __name__, url_prefix="/api/proctor")

# Single shared detector instance (lazy-initialised per worker)
_detector: FaceDetector | None = None


def _get_detector() -> FaceDetector:
    global _detector
    if _detector is None:
        _detector = FaceDetector(use_mediapipe=True)
    return _detector


def _current_user() -> User | None:
    return db.session.get(User, get_jwt_identity())


def _get_session_or_404(session_id: int):
    session = db.session.get(ExamSession, session_id)
    if not session:
        return None, (jsonify({"error": "Session not found."}), 404)
    return session, None


# ── Analyse frame ─────────────────────────────────────────────────────────────
@proctor_bp.route("/analyse", methods=["POST"])
@jwt_required()
def analyse_frame():
    """
    Accepts a JSON body with:
      - session_id : int
      - frame      : base64-encoded JPEG/PNG from the browser webcam
    Returns detected alerts and face count.
    """
    user = _current_user()
    if not user:
        return jsonify({"error": "Unauthorized."}), 401

    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    frame_b64 = data.get("frame") or ""

    if not session_id or not frame_b64:
        return jsonify({"error": "session_id and frame are required."}), 400

    # Validate session ownership
    session, err = _get_session_or_404(session_id)
    if err:
        return err
    if user.role == "student" and session.student_id != user.id:
        return jsonify({"error": "Forbidden."}), 403
    if session.status != "active":
        return jsonify({"error": "Session is not active."}), 400

    # Decode base64 frame
    try:
        # Strip data-URL prefix if present
        if "," in frame_b64:
            frame_b64 = frame_b64.split(",", 1)[1]
        frame_bytes = base64.b64decode(frame_b64)
    except Exception:
        return jsonify({"error": "Invalid base64 frame."}), 400

    max_size = current_app.config.get("MAX_FRAME_SIZE", 1_048_576)
    if len(frame_bytes) > max_size:
        return jsonify({"error": "Frame too large."}), 413

    # Run AI analysis
    detector = _get_detector()
    result = detector.analyse_frame(frame_bytes)

    # Persist each alert
    saved_alerts = []
    for alert_info in result.alerts:
        alert = Alert(
            session_id=session_id,
            alert_type=alert_info["type"],
            confidence=alert_info.get("confidence", 1.0),
            message=alert_info.get("message", ""),
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.session.add(alert)
        saved_alerts.append(alert_info)

    if result.alerts:
        session.alert_count = (session.alert_count or 0) + len(result.alerts)

    db.session.commit()

    return jsonify(
        {
            "face_count": result.face_count,
            "looking_away": result.looking_away,
            "alerts": saved_alerts,
            "annotated_frame": result.annotated_frame_b64,
        }
    ), 200


# ── Manual alert (e.g. browser-side events) ───────────────────────────────────
@proctor_bp.route("/alert", methods=["POST"])
@jwt_required()
def manual_alert():
    """
    Log browser-side events such as tab-switching or copy-paste attempts.
    Body: { session_id, alert_type, message }
    """
    user = _current_user()
    if not user:
        return jsonify({"error": "Unauthorized."}), 401

    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    alert_type = (data.get("alert_type") or "").strip()
    message = (data.get("message") or "").strip()

    if not session_id or not alert_type:
        return jsonify({"error": "session_id and alert_type are required."}), 400

    session, err = _get_session_or_404(session_id)
    if err:
        return err
    if user.role == "student" and session.student_id != user.id:
        return jsonify({"error": "Forbidden."}), 403

    alert = Alert(
        session_id=session_id,
        alert_type=alert_type,
        confidence=1.0,
        message=message or f"Browser event: {alert_type}",
    )
    db.session.add(alert)
    session.alert_count = (session.alert_count or 0) + 1
    db.session.commit()

    return jsonify({"message": "Alert logged.", "alert": alert.to_dict()}), 201


# ── List alerts ───────────────────────────────────────────────────────────────
@proctor_bp.route("/alerts", methods=["GET"])
@jwt_required()
def list_alerts():
    user = _current_user()
    if not user:
        return jsonify({"error": "Unauthorized."}), 401

    session_id = request.args.get("session_id", type=int)

    if user.role == "admin":
        query = Alert.query
        if session_id:
            query = query.filter_by(session_id=session_id)
    else:
        # Students can only view alerts from their own sessions
        own_session_ids = [
            s.id for s in ExamSession.query.filter_by(student_id=user.id).all()
        ]
        query = Alert.query.filter(Alert.session_id.in_(own_session_ids))
        if session_id:
            if session_id not in own_session_ids:
                return jsonify({"error": "Forbidden."}), 403
            query = query.filter_by(session_id=session_id)

    alerts = query.order_by(Alert.timestamp.desc()).limit(500).all()
    return jsonify([a.to_dict() for a in alerts]), 200


# ── Dashboard stats (admin) ────────────────────────────────────────────────────
@proctor_bp.route("/stats", methods=["GET"])
@jwt_required()
def stats():
    user = _current_user()
    if not user or user.role != "admin":
        return jsonify({"error": "Admin access required."}), 403

    total_sessions = ExamSession.query.count()
    active_sessions = ExamSession.query.filter_by(status="active").count()
    flagged_sessions = ExamSession.query.filter_by(status="flagged").count()
    total_alerts = Alert.query.count()

    alert_breakdown = {}
    for alert_type, count in (
        db.session.query(Alert.alert_type, db.func.count(Alert.id))
        .group_by(Alert.alert_type)
        .all()
    ):
        alert_breakdown[alert_type] = count

    return jsonify(
        {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "flagged_sessions": flagged_sessions,
            "total_alerts": total_alerts,
            "alert_breakdown": alert_breakdown,
        }
    ), 200
