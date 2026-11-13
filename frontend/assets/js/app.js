import { CONFIG } from './api.js';

// Banner display in demo mode
if (CONFIG.DEMO_MODE) {
  const banner = document.createElement('div');
  banner.className = 'demo-banner';
  banner.innerHTML = `
    <strong>Demo Mode Active:</strong> Displaying simulated supply-chain data.
    To connect to the live Django backend, set <code>DEMO_MODE = false</code> in <code>assets/js/api.js</code>.
  `;
  document.body.prepend(banner);
}

// Global quick tracking form handler
const trackForm = document.getElementById('trackForm');
if (trackForm && !window.location.pathname.endsWith('/pages/track.html')) {
  trackForm.addEventListener('submit', event => {
    event.preventDefault();
    const input = trackForm.querySelector('#code');
    const code = input ? input.value.trim() : '';
    if (code) {
      // Handle both root index.html and pages/* pathing
      const targetUrl = window.location.pathname.includes('/pages/')
        ? `track.html?batch=${encodeURIComponent(code)}`
        : `pages/track.html?batch=${encodeURIComponent(code)}`;
      window.location.href = targetUrl;
    }
  });
}

