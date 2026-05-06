/**
 * dashboard.js -- Admin monitoring dashboard
 */

const API = window.API_BASE || '/api';

// Auth guard
const token = localStorage.getItem('token');
const user  = JSON.parse(localStorage.getItem('user') || 'null');
if (!token || !user || user.role !== 'admin') {
  window.location.href = 'index.html';
}

document.getElementById('adminName').textContent = user.name || 'Admin';

// ---- Logout ------------------------------------------------------------------
document.getElementById('logoutBtn').addEventListener('click', () => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.href = 'index.html';
});

// ---- Navigation --------------------------------------------------------------
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    const section = link.dataset.section;
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    document.querySelectorAll('.dash-section').forEach(s => s.classList.remove('active'));
    link.classList.add('active');
    document.getElementById('section-' + section).classList.add('active');
    loadSection(section);
  });
});

function loadSection(name) {
  switch (name) {
    case 'overview': loadOverview(); break;
    case 'sessions': loadSessions(); break;
    case 'alerts':   loadAlerts();   break;
    case 'exams':    loadExams();    break;
    case 'users':    loadUsers();    break;
  }
}

// Load overview on start
loadOverview();

// Auto-refresh every 30 seconds when overview is active
setInterval(() => {
  const activeSection = document.querySelector('.nav-link.active');
  if (activeSection && activeSection.dataset.section === 'overview') {
    loadOverview();
  }
}, 30000);

// ---- Overview ----------------------------------------------------------------
async function loadOverview() {
  try {
    const res  = await apiFetch('/proctor/stats');
    const data = await res.json();

    document.getElementById('stat-total').textContent   = data.total_sessions;
    document.getElementById('stat-active').textContent  = data.active_sessions;
    document.getElementById('stat-flagged').textContent = data.flagged_sessions;
    document.getElementById('stat-alerts').textContent  = data.total_alerts;

    renderBarChart(data.alert_breakdown || {});
    loadRecentActivity();
  } catch (err) {
    console.error('Overview error:', err);
  }
}

function renderBarChart(breakdown) {
  const el = document.getElementById('alertBreakdown');
  el.innerHTML = '';
  const entries = Object.entries(breakdown).sort((a, b) => b[1] - a[1]);
  const max = entries.length ? entries[0][1] : 1;

  entries.forEach(([label, count]) => {
    const pct = Math.round((count / max) * 100);
    const row = document.createElement('div');
    row.className = 'bar-row';
    row.innerHTML =
      '<span class="bar-label">' + escapeHtml(label.replace(/_/g, ' ')) + '</span>' +
      '<div class="bar-track"><div class="bar-fill" style="width:' + pct + '%"></div></div>' +
      '<span class="bar-count">' + count + '</span>';
    el.appendChild(row);
  });

  if (!entries.length) {
    el.innerHTML = '<p style="color:var(--text-muted);font-size:.875rem">No alerts yet.</p>';
  }
}

async function loadRecentActivity() {
  const el = document.getElementById('recentActivity');
  try {
    const res    = await apiFetch('/proctor/alerts');
    const alerts = (await res.json()).slice(0, 8);
    el.innerHTML = '';

    if (!alerts.length) {
      el.innerHTML = '<p style="color:var(--text-muted);font-size:.875rem">No recent activity.</p>';
      return;
    }

    alerts.forEach(a => {
      const item = document.createElement('div');
      item.className = 'activity-item';
      const isDanger = ['no_face','multiple_faces'].includes(a.alert_type);
      item.innerHTML =
        '<div class="activity-dot' + (isDanger ? ' danger' : '') + '"></div>' +
        '<div class="activity-text">' + escapeHtml(a.alert_type.replace(/_/g,' ')) +
        ' — Session #' + a.session_id + '</div>' +
        '<div class="activity-time">' + formatTime(a.timestamp) + '</div>';
      el.appendChild(item);
    });
  } catch (err) {
    el.innerHTML = '<p style="color:var(--text-muted)">Could not load activity.</p>';
  }
}

// ---- Sessions ----------------------------------------------------------------
document.getElementById('refreshSessions').addEventListener('click', loadSessions);
document.getElementById('sessionSearch').addEventListener('input', filterSessions);
document.getElementById('statusFilter').addEventListener('change', filterSessions);

let _sessions = [];

async function loadSessions() {
  try {
    const res = await apiFetch('/exams/sessions/');
    _sessions = await res.json();
    renderSessions(_sessions);
  } catch (err) {
    console.error('Sessions error:', err);
  }
}

function filterSessions() {
  const q      = document.getElementById('sessionSearch').value.toLowerCase();
  const status = document.getElementById('statusFilter').value;
  const filtered = _sessions.filter(s => {
    const nameMatch = (s.student_name || '').toLowerCase().includes(q);
    const statusMatch = !status || s.status === status;
    return nameMatch && statusMatch;
  });
  renderSessions(filtered);
}

function renderSessions(sessions) {
  const tbody = document.getElementById('sessionsBody');
  tbody.innerHTML = '';
  if (!sessions.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted)">No sessions found.</td></tr>';
    return;
  }
  sessions.forEach(s => {
    const tr = document.createElement('tr');
    tr.innerHTML =
      '<td>' + s.id + '</td>' +
      '<td>' + escapeHtml(s.student_name || '-') + '</td>' +
      '<td>' + escapeHtml(s.exam_title || '-') + '</td>' +
      '<td>' + formatTime(s.started_at) + '</td>' +
      '<td><span class="status-badge status-' + s.status + '">' + s.status + '</span></td>' +
      '<td>' + (s.alert_count || 0) + '</td>' +
      '<td><button class="btn-sm" onclick="openSessionDetail(' + s.id + ')">View</button></td>';
    tbody.appendChild(tr);
  });
}

async function openSessionDetail(sessionId) {
  const modal = document.getElementById('sessionDetailModal');
  const content = document.getElementById('sessionDetailContent');
  content.innerHTML = '<p style="color:var(--text-muted)">Loading...</p>';
  modal.classList.remove('hidden');

  try {
    const res  = await apiFetch('/exams/sessions/' + sessionId);
    const data = await res.json();

    let alertRows = '';
    (data.alerts || []).forEach(a => {
      alertRows +=
        '<tr>' +
        '<td><span class="atype atype-' + a.alert_type + '">' + escapeHtml(a.alert_type.replace(/_/g,' ')) + '</span></td>' +
        '<td>' + (a.confidence * 100).toFixed(0) + '%</td>' +
        '<td>' + escapeHtml(a.message) + '</td>' +
        '<td>' + formatTime(a.timestamp) + '</td>' +
        '</tr>';
    });

    content.innerHTML =
      '<p><strong>Student:</strong> ' + escapeHtml(data.student_name || '-') + '</p>' +
      '<p><strong>Exam:</strong> ' + escapeHtml(data.exam_title || '-') + '</p>' +
      '<p><strong>Status:</strong> <span class="status-badge status-' + data.status + '">' + data.status + '</span></p>' +
      '<p><strong>Started:</strong> ' + formatTime(data.started_at) + '</p>' +
      '<p><strong>Alert count:</strong> ' + (data.alert_count || 0) + '</p>' +
      '<hr style="margin:16px 0;border-color:var(--border)">' +
      '<h4 style="margin-bottom:12px">Alerts</h4>' +
      '<div class="table-wrap"><table class="data-table">' +
      '<thead><tr><th>Type</th><th>Confidence</th><th>Message</th><th>Time</th></tr></thead>' +
      '<tbody>' + (alertRows || '<tr><td colspan="4" style="color:var(--text-muted)">No alerts.</td></tr>') + '</tbody>' +
      '</table></div>';
  } catch (err) {
    content.innerHTML = '<p style="color:var(--danger)">Failed to load session.</p>';
  }
}

document.getElementById('closeSessionModal').addEventListener('click', () => {
  document.getElementById('sessionDetailModal').classList.add('hidden');
});

// ---- Alerts ------------------------------------------------------------------
document.getElementById('refreshAlerts').addEventListener('click', loadAlerts);

async function loadAlerts() {
  const tbody = document.getElementById('alertsBody');
  try {
    const res    = await apiFetch('/proctor/alerts');
    const alerts = await res.json();
    tbody.innerHTML = '';
    if (!alerts.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">No alerts.</td></tr>';
      return;
    }
    alerts.forEach((a, i) => {
      const tr = document.createElement('tr');
      tr.innerHTML =
        '<td>' + (i + 1) + '</td>' +
        '<td>' + a.session_id + '</td>' +
        '<td><span class="atype atype-' + a.alert_type + '">' + escapeHtml(a.alert_type.replace(/_/g,' ')) + '</span></td>' +
        '<td>' + (a.confidence * 100).toFixed(0) + '%</td>' +
        '<td>' + escapeHtml(a.message) + '</td>' +
        '<td>' + formatTime(a.timestamp) + '</td>';
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="6" style="color:var(--danger)">Failed to load alerts.</td></tr>';
  }
}

// ---- Exams -------------------------------------------------------------------
document.getElementById('openCreateExam').addEventListener('click', () => {
  document.getElementById('createExamModal').classList.remove('hidden');
});
document.getElementById('closeModal').addEventListener('click', () => {
  document.getElementById('createExamModal').classList.add('hidden');
});
document.getElementById('createExamForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const errEl = document.getElementById('createExamError');
  errEl.classList.add('hidden');

  try {
    const res = await apiFetch('/exams/', {
      method: 'POST',
      body: JSON.stringify({
        title:            document.getElementById('examTitleInput').value.trim(),
        description:      document.getElementById('examDescInput').value.trim(),
        duration_minutes: parseInt(document.getElementById('examDurInput').value),
      }),
    });
    if (!res.ok) throw new Error((await res.json()).error || 'Failed to create exam.');
    document.getElementById('createExamModal').classList.add('hidden');
    document.getElementById('createExamForm').reset();
    loadExams();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
});

async function loadExams() {
  const tbody = document.getElementById('examsBody');
  try {
    const res   = await apiFetch('/exams/');
    const exams = await res.json();
    tbody.innerHTML = '';
    if (!exams.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">No exams yet.</td></tr>';
      return;
    }
    exams.forEach(ex => {
      const tr = document.createElement('tr');
      tr.innerHTML =
        '<td>' + ex.id + '</td>' +
        '<td>' + escapeHtml(ex.title) + '</td>' +
        '<td>' + ex.duration_minutes + ' min</td>' +
        '<td>' + formatTime(ex.created_at) + '</td>' +
        '<td><button class="btn-sm btn-danger-sm" onclick="deleteExam(' + ex.id + ')">Delete</button></td>';
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="5" style="color:var(--danger)">Failed to load exams.</td></tr>';
  }
}

async function deleteExam(examId) {
  if (!confirm('Deactivate this exam?')) return;
  try {
    await apiFetch('/exams/' + examId, { method: 'DELETE' });
    loadExams();
  } catch (err) {
    alert('Failed to delete exam.');
  }
}

// ---- Users -------------------------------------------------------------------
async function loadUsers() {
  const tbody = document.getElementById('usersBody');
  try {
    const res   = await apiFetch('/auth/users');
    const users = await res.json();
    tbody.innerHTML = '';
    users.forEach((u, i) => {
      const tr = document.createElement('tr');
      tr.innerHTML =
        '<td>' + (i + 1) + '</td>' +
        '<td>' + escapeHtml(u.name) + '</td>' +
        '<td>' + escapeHtml(u.email) + '</td>' +
        '<td>' + u.role + '</td>' +
        '<td>' + formatTime(u.created_at) + '</td>';
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="5" style="color:var(--danger)">Failed to load users.</td></tr>';
  }
}

// ---- Helpers -----------------------------------------------------------------
function apiFetch(path, opts) {
  opts = opts || {};
  return fetch(API + path, Object.assign({
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token,
    },
  }, opts));
}

function formatTime(iso) {
  if (!iso) return '-';
  try {
    return new Date(iso).toLocaleString();
  } catch (_) {
    return iso;
  }
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"]/g, function(c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
  });
}
