"""
Configuration settings for the Proctoring System
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///proctoring_system.db")

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
JWT_EXPIRATION_HOURS = 24

# Proctoring Settings
FACE_DETECTION_THRESHOLD = 0.5
MULTIPLE_FACES_ALERT = True
FACE_VISIBILITY_THRESHOLD = 0.8
ALERT_COOLDOWN_SECONDS = 5

# Video Settings
VIDEO_FRAME_RATE = 30
VIDEO_RESOLUTION = (640, 480)
MAX_RECORDING_TIME_MINUTES = 180

# Alert Sensitivity
ALERT_SENSITIVITY = {
    "FACE_NOT_VISIBLE": "MEDIUM",
    "MULTIPLE_FACES": "HIGH",
    "UNUSUAL_BEHAVIOR": "MEDIUM",
    "NOISE_DETECTION": "LOW"
}

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "proctoring_system.log"

# Streamlit Configuration
STREAMLIT_CONFIG = {
    "theme": {
        "primaryColor": "#1f77b4",
        "backgroundColor": "#ffffff",
        "secondaryBackgroundColor": "#f0f2f6",
        "textColor": "#262730",
        "font": "sans serif"
    }
}

# Exam Configuration
EXAM_CONFIG = {
    "MAX_EXAM_DURATION": 180,  # minutes
    "QUESTION_TIME_LIMIT": 2,  # minutes
    "AUTO_SUBMIT_ON_TIME_END": True,
    "ALLOW_REVIEW": False,
    "PASSING_SCORE": 60  # percentage
}

# Monitoring
MONITORING_CONFIG = {
    "ENABLE_EYE_TRACKING": True,
    "ENABLE_HEAD_POSE_DETECTION": True,
    "ENABLE_AUDIO_MONITORING": False,
    "ENABLE_SCREEN_SHARE_CHECK": True,
    "CHECK_INTERVAL_SECONDS": 2
}
