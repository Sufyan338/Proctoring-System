/**
 * auth.js  –  Login / Register page logic
 *
 * Reads API_BASE from the global window.API_BASE (set by the server or
 * falls back to /api so the frontend works when served by Flask directly).
 */

const API = window.API_BASE || '/api';

// ── Tab switching ─────────────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(`${tab.dataset.tab}Form`).classList.add('active');
  });
});

// ── Redirect if already logged in ────────────────────────────────────────────
(function checkAuth() {
  const token = localStorage.getItem('token');
  const user  = JSON.parse(localStorage.getItem('user') || 'null');
  if (token && user) {
    redirectUser(user);
  }
})();

function redirectUser(user) {
  if (user.role === 'admin') {
    window.location.href = 'dashboard.html';
  } else {
    window.location.href = 'exam.html';
  }
}

// ── Login ─────────────────────────────────────────────────────────────────────
document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('loginBtn');
  const errEl = document.getElementById('loginError');
  errEl.classList.add('hidden');
  setLoading(btn, true);

  try {
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email:    document.getElementById('loginEmail').value.trim(),
        password: document.getElementById('loginPassword').value,
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || 'Login failed.');
    }

    localStorage.setItem('token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    redirectUser(data.user);
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  } finally {
    setLoading(btn, false);
  }
});

// ── Register ──────────────────────────────────────────────────────────────────
document.getElementById('registerForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('registerBtn');
  const errEl = document.getElementById('registerError');
  errEl.classList.add('hidden');
  setLoading(btn, true);

  try {
    const res = await fetch(`${API}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name:     document.getElementById('regName').value.trim(),
        email:    document.getElementById('regEmail').value.trim(),
        password: document.getElementById('regPassword').value,
        role:     document.getElementById('regRole').value,
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || 'Registration failed.');
    }

    localStorage.setItem('token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    redirectUser(data.user);
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  } finally {
    setLoading(btn, false);
  }
});

// ── Helpers ───────────────────────────────────────────────────────────────────
function setLoading(btn, loading) {
  btn.disabled = loading;
  btn.querySelector('.btn-text').classList.toggle('hidden', loading);
  btn.querySelector('.spinner').classList.toggle('hidden', !loading);
}
