# 🎓 ProctorAI — AI-Powered Smart Online Exam Proctoring System

[![CI](https://github.com/Sufyan338/Proctoring-System/actions/workflows/ci.yml/badge.svg)](https://github.com/Sufyan338/Proctoring-System/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/flask-3.0-green)](https://flask.palletsprojects.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **complete, production-ready** AI proctoring system that monitors students via webcam
during online exams, detects cheating using computer vision, and provides a real-time
admin dashboard.

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 🔐 JWT Authentication | Secure login for students and admins |
| 📷 Live Webcam Monitoring | Browser-based webcam capture (no plugins needed) |
| 🧠 AI Face Detection | OpenCV Haar Cascade + optional MediaPipe Face Mesh |
| 👁 Gaze / Head-Pose Tracking | Detects when student looks away from screen |
| 👥 Multiple Face Detection | Flags when more than one person is visible |
| 🚨 Real-time Alerts | Instant alerts with timestamps stored in the database |
| 🔄 Tab-switch Detection | Browser `visibilitychange` + `blur` event monitoring |
| �� Admin Dashboard | Live stats, session monitoring, alert breakdown charts |
| 🗃 Exam Management | Create, assign, and manage exams from the dashboard |
| 🚀 Render/Railway Ready | One-click deployment with `render.yaml` |
| ✅ 35 Automated Tests | Full pytest suite covering auth, exams, and proctoring |

---

## 📁 Project Structure

```
Proctoring-System/
├── backend/                    # Flask API
│   ├── app.py                  # Application factory
│   ├── config.py               # Environment-based configuration
│   ├── models.py               # SQLAlchemy ORM (User, Exam, Session, Alert)
│   ├── auth.py                 # /api/auth/* endpoints
│   ├── exam.py                 # /api/exams/* endpoints
│   ├── proctoring.py           # /api/proctor/* endpoints
│   └── ai/
│       └── face_detector.py    # OpenCV + MediaPipe face/gaze detection
├── frontend/                   # Vanilla HTML/CSS/JS SPA
│   ├── index.html              # Login / Register
│   ├── exam.html               # Student exam screen
│   ├── dashboard.html          # Admin monitoring dashboard
│   ├── css/style.css           # Dark-mode stylesheet
│   └── js/
│       ├── auth.js             # Login/register logic
│       ├── exam.js             # Webcam capture + alert display
│       └── dashboard.js        # Admin dashboard logic
├── tests/                      # pytest test suite (35 tests)
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_exam.py
│   └── test_proctoring.py
├── .github/workflows/ci.yml    # GitHub Actions CI pipeline
├── render.yaml                 # Render deployment config
├── requirements.txt
└── .env.example
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- pip
- A modern browser with webcam support

### 1. Clone and install

```bash
git clone https://github.com/Sufyan338/Proctoring-System.git
cd Proctoring-System
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set SECRET_KEY, JWT_SECRET_KEY etc.
```

### 3. Run the server

```bash
flask --app backend.app run --debug
# Or:
python -m backend.app
```

The server starts at **http://localhost:5000**.

Flask automatically serves the `frontend/` directory as static files:

| URL | Page |
|-----|------|
| http://localhost:5000/ | Login / Register |
| http://localhost:5000/exam.html | Student exam screen |
| http://localhost:5000/dashboard.html | Admin dashboard |

### 4. Default admin credentials

| Email | Password |
|-------|----------|
| `admin@proctor.local` | `Admin@12345` |

---

## 🧠 AI Detection Logic

The `FaceDetector` class in `backend/ai/face_detector.py` analyses each webcam frame:

```
Frame (JPEG/PNG) from browser
        │
        ▼
  Decode with OpenCV
        │
        ├─ MediaPipe FaceMesh (if installed)
        │       ├─ Count faces  ──► no_face / multiple_faces alert
        │       └─ Head-pose via solvePnP  ──► looking_away alert
        │
        └─ Haar Cascade fallback (always available)
                ├─ Count faces
                └─ Face-center offset proxy for gaze
```

**Alert Types**

| Type | Trigger |
|------|---------|
| `no_face` | No face detected for a frame |
| `multiple_faces` | More than 1 face visible |
| `looking_away` | Head yaw > 25° or pitch > 20° |
| `tab_switch` | Student switches tab / window loses focus |
| `suspicious_movement` | Copy-paste keyboard shortcuts detected |

---

## 🔗 API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register user |
| POST | `/api/auth/login` | Login, returns JWT |
| GET | `/api/auth/me` | Current user info |
| GET | `/api/auth/users` | List all users (admin) |

### Exams
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/exams/` | List active exams |
| POST | `/api/exams/` | Create exam (admin) |
| POST | `/api/exams/<id>/start` | Student starts session |
| POST | `/api/exams/sessions/<sid>/end` | End session |
| GET | `/api/exams/sessions/` | List sessions |

### Proctoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/proctor/analyse` | Analyse webcam frame |
| POST | `/api/proctor/alert` | Log browser-side event |
| GET | `/api/proctor/alerts` | Get alerts |
| GET | `/api/proctor/stats` | Dashboard statistics |

---

## 🧪 Running Tests

```bash
pytest tests/ -v --cov=backend --cov-report=term-missing
```

All 35 tests should pass:
```
35 passed in ~3s
```

---

## 🚀 Deployment

### Option A – Render (Recommended)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repository
4. Render auto-detects `render.yaml` and configures everything
5. Set environment variables in the Render dashboard:
   - `SECRET_KEY` (generate a random 32-char string)
   - `JWT_SECRET_KEY` (generate another random string)
   - `ADMIN_PASSWORD` (choose a strong password)
   - `CORS_ORIGINS` (your frontend URL if separate)

### Option B – Railway

```bash
railway login
railway init
railway up
```

Set the same environment variables in Railway dashboard.

### Frontend on Vercel / Netlify

If you want to host the frontend separately:
1. Set `window.API_BASE` in your HTML to the Render backend URL:
   ```html
   <script>window.API_BASE = 'https://proctor-ai-backend.onrender.com/api';</script>
   ```
2. Deploy `frontend/` folder to Vercel or Netlify

---

## 🔐 Security Notes

- JWT tokens expire after 8 hours (configurable)
- Passwords hashed with `werkzeug.security` (PBKDF2-SHA256)
- CORS restricted to configured origins in production
- Frame size limited to 1 MB to prevent abuse
- Tab-switch and keyboard shortcuts logged as alerts

---

## 📸 Screenshots

### Login Page
A clean dark-mode auth screen with login and register tabs.

### Student Exam Screen
Split layout: exam content (left) + live webcam panel with real-time alerts (right).

### Admin Dashboard
Overview stats, alert breakdown chart, session table with detail modal.

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python · Flask 3 · SQLAlchemy |
| AI | OpenCV · MediaPipe (optional) |
| Database | SQLite (dev) · PostgreSQL (prod) |
| Auth | JWT via flask-jwt-extended |
| Frontend | Vanilla HTML5 / CSS3 / ES6 JS |
| CI/CD | GitHub Actions |
| Deployment | Render · Railway · Vercel |

---

## 📄 License

MIT License — free to use for educational purposes.
