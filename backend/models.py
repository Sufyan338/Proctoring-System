"""
SQLAlchemy ORM models for the Proctoring System.

Tables
------
users          – students and admins
exams          – exam definitions
exam_sessions  – a student's attempt at an exam
alerts         – cheating alerts generated during a session
"""

import datetime as _dt
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


# ─────────────────────────────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")  # 'student' | 'admin'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    is_active = db.Column(db.Boolean, default=True)

    # relationships
    sessions = db.relationship("ExamSession", back_populates="student", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Exam
# ─────────────────────────────────────────────────────────────────────────────
class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    duration_minutes = db.Column(db.Integer, default=60)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    is_active = db.Column(db.Boolean, default=True)

    # relationships
    sessions = db.relationship("ExamSession", back_populates="exam", lazy="dynamic")
    creator = db.relationship("User", foreign_keys=[created_by])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "duration_minutes": self.duration_minutes,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Exam Session  (one row per student–exam attempt)
# ─────────────────────────────────────────────────────────────────────────────
class ExamSession(db.Model):
    __tablename__ = "exam_sessions"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    ended_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="active")  # active | completed | flagged
    alert_count = db.Column(db.Integer, default=0)

    # relationships
    student = db.relationship("User", back_populates="sessions")
    exam = db.relationship("Exam", back_populates="sessions")
    alerts = db.relationship("Alert", back_populates="session", lazy="dynamic")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student.name if self.student else None,
            "exam_id": self.exam_id,
            "exam_title": self.exam.title if self.exam else None,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "status": self.status,
            "alert_count": self.alert_count,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Alert  (cheating event attached to a session)
# ─────────────────────────────────────────────────────────────────────────────
ALERT_TYPES = (
    "no_face",
    "multiple_faces",
    "looking_away",
    "suspicious_movement",
    "tab_switch",
    "phone_detected",
)


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("exam_sessions.id"), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, default=1.0)   # 0.0 – 1.0
    message = db.Column(db.Text, default="")
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    frame_snapshot = db.Column(db.Text, nullable=True)  # base64 thumbnail (optional)

    # relationship
    session = db.relationship("ExamSession", back_populates="alerts")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "alert_type": self.alert_type,
            "confidence": self.confidence,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }
