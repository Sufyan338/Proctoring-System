"""
Tests for proctoring endpoints and AI face detector.
"""

import base64
import io
import os
import struct
import zlib

import numpy as np
import pytest


# ── Helpers to generate minimal test frames ───────────────────────────────────

def _make_jpeg_bytes(width: int = 320, height: int = 240) -> bytes:
    """Create a minimal solid-colour JPEG using OpenCV."""
    import cv2
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:, :] = (100, 150, 200)  # BGR
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def _make_frame_b64(width: int = 320, height: int = 240) -> str:
    """Return base64-encoded JPEG."""
    return base64.b64encode(_make_jpeg_bytes(width, height)).decode()


# ── Fixture: an active exam session ──────────────────────────────────────────

@pytest.fixture()
def active_session(client, student_user, auth_headers_admin):
    """Create an exam via admin, then start a session as student."""
    exam_res = client.post(
        "/api/exams/",
        json={"title": "Proctor Test Exam", "duration_minutes": 10},
        headers=auth_headers_admin,
    )
    exam = exam_res.get_json()

    user, student_h = student_user
    sess_res = client.post(f"/api/exams/{exam['id']}/start", headers=student_h)
    session = sess_res.get_json()

    return session, student_h


# ── Analyse frame ─────────────────────────────────────────────────────────────

class TestAnalyseFrame:
    def test_analyse_returns_ok(self, client, active_session):
        session, headers = active_session
        res = client.post(
            "/api/proctor/analyse",
            json={"session_id": session["id"], "frame": _make_frame_b64()},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.get_json()
        assert "face_count" in data
        assert "alerts" in data
        assert isinstance(data["alerts"], list)

    def test_analyse_missing_fields(self, client, active_session):
        session, headers = active_session
        res = client.post(
            "/api/proctor/analyse",
            json={"session_id": session["id"]},
            headers=headers,
        )
        assert res.status_code == 400

    def test_analyse_invalid_base64(self, client, active_session):
        session, headers = active_session
        res = client.post(
            "/api/proctor/analyse",
            json={"session_id": session["id"], "frame": "!!!not-valid-base64!!!"},
            headers=headers,
        )
        assert res.status_code == 400

    def test_analyse_no_auth(self, client, active_session):
        session, _ = active_session
        res = client.post(
            "/api/proctor/analyse",
            json={"session_id": session["id"], "frame": _make_frame_b64()},
        )
        assert res.status_code == 401


# ── Manual alert ──────────────────────────────────────────────────────────────

class TestManualAlert:
    def test_log_tab_switch(self, client, active_session):
        session, headers = active_session
        res = client.post(
            "/api/proctor/alert",
            json={
                "session_id": session["id"],
                "alert_type": "tab_switch",
                "message": "Student left the tab.",
            },
            headers=headers,
        )
        assert res.status_code == 201
        assert res.get_json()["alert"]["alert_type"] == "tab_switch"

    def test_log_alert_missing_fields(self, client, active_session):
        session, headers = active_session
        res = client.post(
            "/api/proctor/alert",
            json={"session_id": session["id"]},
            headers=headers,
        )
        assert res.status_code == 400


# ── List alerts ───────────────────────────────────────────────────────────────

class TestListAlerts:
    def test_admin_can_list_all_alerts(self, client, auth_headers_admin):
        res = client.get("/api/proctor/alerts", headers=auth_headers_admin)
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)

    def test_no_token(self, client):
        res = client.get("/api/proctor/alerts")
        assert res.status_code == 401


# ── Stats ─────────────────────────────────────────────────────────────────────

class TestStats:
    def test_stats_admin(self, client, auth_headers_admin):
        res = client.get("/api/proctor/stats", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.get_json()
        assert "total_sessions" in data
        assert "total_alerts" in data

    def test_stats_student_forbidden(self, client, student_user):
        _, headers = student_user
        res = client.get("/api/proctor/stats", headers=headers)
        assert res.status_code == 403


# ── Unit test: FaceDetector ───────────────────────────────────────────────────

class TestFaceDetector:
    def test_analyse_blank_frame(self):
        """A blank frame should return a no_face or valid result without crashing."""
        from backend.ai import FaceDetector

        detector = FaceDetector(use_mediapipe=False)
        jpeg_bytes = _make_jpeg_bytes()
        result = detector.analyse_frame(jpeg_bytes)

        assert hasattr(result, "face_count")
        assert hasattr(result, "alerts")
        assert isinstance(result.alerts, list)
        detector.close()

    def test_analyse_corrupt_frame(self):
        """Corrupt data should not raise an exception."""
        from backend.ai import FaceDetector

        detector = FaceDetector(use_mediapipe=False)
        result = detector.analyse_frame(b"\x00\x01\x02corrupt")
        assert len(result.alerts) > 0  # should flag no_face / decode error
        detector.close()
