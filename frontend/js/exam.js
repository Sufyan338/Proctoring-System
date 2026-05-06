/**
 * exam.js  -- Student exam screen
 */

const API = window.API_BASE || '/api';

// Auth guard
const token = localStorage.getItem('token');
const user  = JSON.parse(localStorage.getItem('user') || 'null');
if (!token || !user || user.role !== 'student') {
  window.location.href = 'index.html';
}

// State
let sessionId      = null;
let examDuration   = 60;
let timerSeconds   = 0;
let timerInterval  = null;
let captureInterval = null;
let alertCount     = 0;
let stream         = null;

const FRAME_INTERVAL_MS = 3000;

// DOM refs
const webcamEl       = document.getElementById('webcam');
const overlayEl      = document.getElementById('overlay');
const ctx            = overlayEl.getContext('2d');
const timerDisplay   = document.getElementById('timerDisplay');
const faceStatus     = document.getElementById('faceStatus');
const alertList      = document.getElementById('alertList');
const alertCountEl   = document.getElementById('alertCount');
const warningOverlay = document.getElementById('warningOverlay');
const warningTitle   = document.getElementById('warningTitle');
const warningMsg     = document.getElementById('warningMsg');
const noExamMsg      = document.getElementById('noExamMsg');
const examContent    = document.getElementById('examContent');

// Logout
document.getElementById('logoutBtn').addEventListener('click', () => {
  cleanupAndLeave('index.html');
});

// Join exam
document.getElementById('joinExamBtn').addEventListener('click', joinExam);
document.getElementById('examIdInput').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') joinExam();
});

async function joinExam() {
  const examId = parseInt(document.getElementById('examIdInput').value);
  const errEl  = document.getElementById('joinError');
  errEl.classList.add('hidden');

  if (!examId) {
    errEl.textContent = 'Please enter a valid exam ID.';
    errEl.classList.remove('hidden');
    return;
  }

  try {
    const examRes = await apiFetch('/exams/' + examId);
    if (!examRes.ok) throw new Error((await examRes.json()).error || 'Exam not found.');
    const exam = await examRes.json();

    const sessRes = await apiFetch('/exams/' + examId + '/start', { method: 'POST' });
    if (!sessRes.ok) throw new Error((await sessRes.json()).error || 'Could not start session.');
    const sess = await sessRes.json();

    sessionId = sess.id;
    examDuration = exam.duration_minutes;
    timerSeconds = examDuration * 60;

    document.getElementById('examTitle').textContent = exam.title;
    document.getElementById('examName').textContent   = exam.title;
    document.getElementById('examDesc').textContent   = exam.description || '';
    document.getElementById('examDuration').textContent = 'Duration: ' + examDuration + ' minutes';
    noExamMsg.classList.add('hidden');
    examContent.classList.remove('hidden');

    await startWebcam();
    startTimer();
    startFrameCapture();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
}

async function startWebcam() {
  const camErr = document.getElementById('camError');
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: 'user' },
      audio: false,
    });
    webcamEl.srcObject = stream;
    await new Promise(r => webcamEl.addEventListener('loadedmetadata', r, { once: true }));
    overlayEl.width  = webcamEl.videoWidth  || 640;
    overlayEl.height = webcamEl.videoHeight || 480;
  } catch (err) {
    camErr.textContent = 'Camera error: ' + err.message;
    camErr.classList.remove('hidden');
  }
}

function startFrameCapture() {
  captureInterval = setInterval(captureAndAnalyse, FRAME_INTERVAL_MS);
}

async function captureAndAnalyse() {
  if (!sessionId || !stream) return;

  const canvas = document.createElement('canvas');
  canvas.width  = 320;
  canvas.height = 240;
  const c = canvas.getContext('2d');
  c.drawImage(webcamEl, 0, 0, 320, 240);
  const frame = canvas.toDataURL('image/jpeg', 0.7);

  try {
    const res = await apiFetch('/proctor/analyse', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, frame }),
    });
    if (!res.ok) return;
    const data = await res.json();
    handleAnalysisResult(data);
  } catch (_) {}
}

function handleAnalysisResult(data) {
  const face_count     = data.face_count;
  const looking_away   = data.looking_away;
  const alerts         = data.alerts;
  const annotated_frame = data.annotated_frame;

  if (face_count === 0) {
    setFaceBadge('NO FACE', 'danger');
  } else if (face_count > 1) {
    setFaceBadge(face_count + ' FACES', 'warn');
  } else if (looking_away) {
    setFaceBadge('LOOKING AWAY', 'warn');
  } else {
    setFaceBadge('OK', 'ok');
  }

  if (annotated_frame) {
    const img = new Image();
    img.onload = () => {
      ctx.clearRect(0, 0, overlayEl.width, overlayEl.height);
      ctx.drawImage(img, 0, 0, overlayEl.width, overlayEl.height);
    };
    img.src = 'data:image/jpeg;base64,' + annotated_frame;
  }

  alerts.forEach(a => addAlertItem(a));

  if (alerts.length > 0) {
    const serious = alerts.find(a => ['no_face', 'multiple_faces'].includes(a.type));
    if (serious) {
      showWarning(serious.type, serious.message);
    }
  }
}

function setFaceBadge(text, cls) {
  faceStatus.textContent = text;
  faceStatus.className = 'face-badge ' + cls;
}

function addAlertItem(alert) {
  alertCount++;
  alertCountEl.textContent = alertCount;

  const li = document.createElement('li');
  li.className = 'alert-item';
  const typeTxt = alert.type.replace(/_/g, ' ').toUpperCase();
  li.innerHTML =
    '<span class="alert-type">' + typeTxt + '</span>' +
    '<span class="alert-msg"> -- ' + escapeHtml(alert.message) + '</span>' +
    '<div class="alert-time">' + new Date().toLocaleTimeString() + '</div>';
  alertList.insertBefore(li, alertList.firstChild);

  while (alertList.children.length > 50) {
    alertList.removeChild(alertList.lastChild);
  }
}

function startTimer() {
  timerInterval = setInterval(() => {
    if (timerSeconds <= 0) {
      clearInterval(timerInterval);
      endExam();
      return;
    }
    timerSeconds--;
    const m = String(Math.floor(timerSeconds / 60)).padStart(2, '0');
    const s = String(timerSeconds % 60).padStart(2, '0');
    timerDisplay.textContent = m + ':' + s;
    if (timerSeconds <= 300) {
      timerDisplay.style.color = '#ef4444';
    }
  }, 1000);
}

document.getElementById('endExamBtn').addEventListener('click', () => {
  if (confirm('Are you sure you want to submit your exam?')) {
    endExam();
  }
});

async function endExam() {
  clearInterval(timerInterval);
  clearInterval(captureInterval);
  if (sessionId) {
    try {
      await apiFetch('/exams/sessions/' + sessionId + '/end', { method: 'POST' });
    } catch (_) {}
  }
  cleanupAndLeave('index.html');
}

function cleanupAndLeave(url) {
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    stream = null;
  }
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.href = url;
}

// Tab-switch detection
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden' && sessionId) {
    logManualAlert('tab_switch', 'Student switched tab or minimised window.');
    showWarning('tab_switch', 'Tab switch detected! This has been logged.');
  }
});

window.addEventListener('blur', () => {
  if (sessionId) {
    logManualAlert('tab_switch', 'Window lost focus.');
  }
});

document.addEventListener('contextmenu', e => e.preventDefault());
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && ['c','v','a','p'].includes(e.key.toLowerCase())) {
    e.preventDefault();
    if (sessionId) logManualAlert('suspicious_movement', 'Keyboard shortcut attempt: Ctrl+' + e.key);
  }
});

async function logManualAlert(type, message) {
  if (!sessionId) return;
  try {
    await apiFetch('/proctor/alert', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, alert_type: type, message }),
    });
    addAlertItem({ type, message });
  } catch (_) {}
}

function showWarning(type, message) {
  const titles = {
    no_face:        'No Face Detected',
    multiple_faces: 'Multiple Faces Detected',
    looking_away:   'Looking Away',
    tab_switch:     'Tab Switch Detected',
  };
  warningTitle.textContent = titles[type] || 'Warning';
  warningMsg.textContent   = message;
  warningOverlay.classList.remove('hidden');
}

document.getElementById('warningDismiss').addEventListener('click', () => {
  warningOverlay.classList.add('hidden');
});

function apiFetch(path, opts) {
  opts = opts || {};
  return fetch(API + path, Object.assign({
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token,
    },
  }, opts));
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"]/g, function(c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
  });
}
