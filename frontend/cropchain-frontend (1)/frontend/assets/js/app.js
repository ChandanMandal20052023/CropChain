import { CONFIG } from './api.js';
if (CONFIG.DEMO_MODE) {
  const b = document.createElement('div'); b.className = 'demo-banner';
  b.textContent = 'Demo mode: sample data only. Not connected to the CropChain backend or Hyperledger Fabric.';
  document.body.prepend(b);
}
const form = document.getElementById('trackForm');
if (form) form.addEventListener('submit', e => {
  e.preventDefault();
  const code = form.code.value.trim();
  if (code) location.href = `pages/track.html?batch=${encodeURIComponent(code)}`;
});
