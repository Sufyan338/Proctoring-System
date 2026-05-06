"""
AI face / cheating detection logic.

Uses OpenCV's Haar Cascade for face detection (works without GPU,
no large model downloads required for CI) and optionally MediaPipe
for more accurate gaze / head-pose estimation.

Falls back gracefully when MediaPipe is not installed.
"""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass, field
from typing import List

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ── Optional MediaPipe import ──────────────────────────────────────────────
try:
    import mediapipe as mp

    _MP_AVAILABLE = True
    _mp_face_mesh = mp.solutions.face_mesh
    _mp_drawing = mp.solutions.drawing_utils
except ImportError:
    _MP_AVAILABLE = False
    logger.warning("MediaPipe not installed – falling back to Haar-cascade only.")

# ── Haar Cascade (always available with opencv-python) ────────────────────
_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
_face_cascade = cv2.CascadeClassifier(_CASCADE_PATH)


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class DetectionResult:
    face_count: int = 0
    looking_away: bool = False
    suspicious_movement: bool = False
    alerts: List[dict] = field(default_factory=list)
    # Annotated frame as base64 JPEG (thumbnail)
    annotated_frame_b64: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Core detector
# ─────────────────────────────────────────────────────────────────────────────
class FaceDetector:
    """
    Stateful detector that analyses individual frames.

    Parameters
    ----------
    use_mediapipe : bool
        Whether to attempt MediaPipe Face Mesh for gaze estimation.
    min_face_confidence : float
        Not used by Haar but kept for API compatibility.
    """

    # Landmark indices used for gaze / head-pose (MediaPipe 468-landmark model)
    # Nose tip, left eye outer, right eye outer, chin, forehead
    _LANDMARK_INDICES = [1, 33, 263, 152, 10]

    def __init__(self, use_mediapipe: bool = True, min_face_confidence: float = 0.5):
        self._use_mp = use_mediapipe and _MP_AVAILABLE
        self._face_mesh = None
        if self._use_mp:
            self._face_mesh = _mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=4,
                refine_landmarks=False,
                min_detection_confidence=min_face_confidence,
                min_tracking_confidence=0.5,
            )

    # ── Public API ────────────────────────────────────────────────────────────
    def analyse_frame(self, frame_bytes: bytes) -> DetectionResult:
        """
        Decode *frame_bytes* (JPEG / PNG) and run all checks.

        Returns a :class:`DetectionResult` with detected issues.
        """
        result = DetectionResult()

        # Decode to numpy array
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            result.alerts.append(
                {"type": "no_face", "confidence": 1.0, "message": "Could not decode frame."}
            )
            return result

        # Resize to 640×480 for consistent processing speed
        frame = cv2.resize(frame, (640, 480))
        annotated = frame.copy()

        if self._use_mp:
            self._analyse_mediapipe(frame, annotated, result)
        else:
            self._analyse_haar(frame, annotated, result)

        # Encode annotated frame as small JPEG thumbnail
        result.annotated_frame_b64 = self._encode_thumbnail(annotated)
        return result

    # ── MediaPipe path ────────────────────────────────────────────────────────
    def _analyse_mediapipe(self, frame: np.ndarray, annotated: np.ndarray, result: DetectionResult) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_result = self._face_mesh.process(rgb)

        if not mp_result.multi_face_landmarks:
            result.face_count = 0
            result.alerts.append(
                {"type": "no_face", "confidence": 0.95, "message": "No face detected in frame."}
            )
            return

        result.face_count = len(mp_result.multi_face_landmarks)

        if result.face_count > 1:
            result.alerts.append(
                {
                    "type": "multiple_faces",
                    "confidence": 0.90,
                    "message": f"{result.face_count} faces detected.",
                }
            )

        # Draw landmarks on annotated frame
        for face_lms in mp_result.multi_face_landmarks:
            _mp_drawing.draw_landmarks(
                annotated,
                face_lms,
                _mp_face_mesh.FACEMESH_CONTOURS,
                landmark_drawing_spec=_mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1),
                connection_drawing_spec=_mp_drawing.DrawingSpec(color=(0, 200, 0), thickness=1),
            )

        # Head-pose / gaze estimation on the *first* face
        first_face = mp_result.multi_face_landmarks[0]
        h, w = frame.shape[:2]

        image_pts = np.array(
            [
                (first_face.landmark[i].x * w, first_face.landmark[i].y * h)
                for i in self._LANDMARK_INDICES
            ],
            dtype=np.float64,
        )

        # 3-D reference model points (generic head)
        model_pts = np.array(
            [
                [0.0, 0.0, 0.0],          # Nose tip
                [-225.0, 170.0, -135.0],  # Left eye outer
                [225.0, 170.0, -135.0],   # Right eye outer
                [0.0, -330.0, -65.0],     # Chin
                [0.0, 330.0, -65.0],      # Forehead
            ],
            dtype=np.float64,
        )

        focal = w
        camera_matrix = np.array(
            [[focal, 0, w / 2], [0, focal, h / 2], [0, 0, 1]], dtype=np.float64
        )
        dist_coeffs = np.zeros((4, 1))

        success, rvec, _ = cv2.solvePnP(
            model_pts, image_pts, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_SQPNP
        )
        if not success:
            return

        rmat, _ = cv2.Rodrigues(rvec)
        proj_matrix = np.hstack((rmat, np.zeros((3, 1))))
        _, _, _, _, _, _, euler = cv2.decomposeProjectionMatrix(proj_matrix)
        pitch, yaw, roll = (float(euler[i]) for i in range(3))

        # Thresholds (degrees)
        YAW_THRESHOLD = 25
        PITCH_THRESHOLD = 20

        if abs(yaw) > YAW_THRESHOLD or abs(pitch) > PITCH_THRESHOLD:
            result.looking_away = True
            result.alerts.append(
                {
                    "type": "looking_away",
                    "confidence": round(min(1.0, (max(abs(yaw), abs(pitch))) / 45), 2),
                    "message": f"Head turned away (yaw={yaw:.1f}°, pitch={pitch:.1f}°).",
                }
            )

        # Overlay text
        cv2.putText(
            annotated,
            f"Faces: {result.face_count}  Yaw:{yaw:.1f} Pitch:{pitch:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

    # ── Haar Cascade fallback ─────────────────────────────────────────────────
    def _analyse_haar(self, frame: np.ndarray, annotated: np.ndarray, result: DetectionResult) -> None:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = _face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )

        result.face_count = len(faces)

        if result.face_count == 0:
            result.alerts.append(
                {"type": "no_face", "confidence": 0.90, "message": "No face detected in frame."}
            )
        elif result.face_count > 1:
            result.alerts.append(
                {
                    "type": "multiple_faces",
                    "confidence": 0.85,
                    "message": f"{result.face_count} faces detected.",
                }
            )

        for x, y, fw, fh in faces:
            cv2.rectangle(annotated, (x, y), (x + fw, y + fh), (0, 255, 0), 2)

        h, w = frame.shape[:2]
        for x, y, fw, fh in faces:
            face_cx = x + fw // 2
            face_cy = y + fh // 2
            # Simple center-of-frame gaze proxy
            off_x = abs(face_cx - w // 2) / (w // 2)
            off_y = abs(face_cy - h // 2) / (h // 2)
            if off_x > 0.4 or off_y > 0.4:
                result.looking_away = True
                result.alerts.append(
                    {
                        "type": "looking_away",
                        "confidence": round((off_x + off_y) / 2, 2),
                        "message": "Student appears to be looking away from screen.",
                    }
                )
                break

        cv2.putText(
            annotated,
            f"Faces: {result.face_count}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _encode_thumbnail(frame: np.ndarray, max_size: int = 160) -> str:
        """Return a tiny base64 JPEG of *frame*."""
        h, w = frame.shape[:2]
        scale = max_size / max(h, w)
        small = cv2.resize(frame, (int(w * scale), int(h * scale)))
        _, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 60])
        return base64.b64encode(buf).decode()

    def close(self) -> None:
        if self._face_mesh:
            self._face_mesh.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
