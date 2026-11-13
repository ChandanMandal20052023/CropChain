import { api } from './api.js';
import './app.js';

const form = document.getElementById('loginForm');
const errBox = document.getElementById('err');

if (form) {
  form.addEventListener('submit', async event => {
    event.preventDefault();
    errBox.classList.add('hidden');
    errBox.textContent = '';

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Signing in…';

    try {
      const response = await api('/auth/login/', {
        method: 'POST',
        auth: false,
        body: {
          email: form.email.value.trim(),
          password: form.password.value
        }
      });

      // Support both Django SimpleJWT ('access') and demo token ('token')
      const token = response.access || response.token;
      if (token) {
        sessionStorage.setItem('cc_token', token);
      }
      
      // Store user summary if provided
      if (response.user) {
        sessionStorage.setItem('cc_user', JSON.stringify(response.user));
      }

      window.location.href = 'dashboard.html';
    } catch (err) {
      errBox.textContent = err.message || 'Authentication failed. Please verify your credentials.';
      errBox.classList.remove('hidden');
      submitBtn.disabled = false;
      submitBtn.textContent = originalText;
    }
  });
}

