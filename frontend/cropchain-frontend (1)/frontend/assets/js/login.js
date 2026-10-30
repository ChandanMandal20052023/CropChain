import { api, CONFIG } from './api.js';
import './app.js';
const f = document.getElementById('loginForm'), err = document.getElementById('err');
f.addEventListener('submit', async e => {
  e.preventDefault(); err.classList.add('hidden');
  const btn = f.querySelector('button'); btn.disabled = true; btn.textContent = 'Signing in…';
  try {
    const r = await api('/auth/login/', { method: 'POST', auth: false, body: { email: f.email.value, password: f.password.value } });
    sessionStorage.setItem('cc_token', r.token); // use secure cookies/JWT per backend decision
    location.href = 'dashboard.html';
  } catch (ex) { err.textContent = ex.message; err.classList.remove('hidden'); btn.disabled = false; btn.textContent = 'Sign in'; }
});
