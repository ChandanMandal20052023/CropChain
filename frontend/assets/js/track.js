import { api, badge, esc, fmtDate } from './api.js';
import './app.js';

const resultContainer = document.getElementById('result');
const codeInput = document.getElementById('code');
const form = document.getElementById('trackForm');

const initialBatchCode = new URLSearchParams(window.location.search).get('batch');
if (initialBatchCode && codeInput) {
  codeInput.value = initialBatchCode;
  fetchAndRenderPassport(initialBatchCode);
}

if (form) {
  form.addEventListener('submit', event => {
    event.preventDefault();
    const code = codeInput?.value.trim();
    if (!code) return;
    const newUrl = `${window.location.pathname}?batch=${encodeURIComponent(code)}`;
    window.history.pushState({ path: newUrl }, '', newUrl);
    fetchAndRenderPassport(code);
  });
}

async function fetchAndRenderPassport(batchCode) {
  if (!batchCode) {
    resultContainer.innerHTML = '<div class="state">Please enter a valid batch code.</div>';
    return;
  }

  resultContainer.innerHTML = `<div class="state">Verifying records for <b>${esc(batchCode)}</b>…</div>`;
  try {
    const passport = await api(`/public/track/${encodeURIComponent(batchCode)}/`, { auth: false });
    const events = passport.public_events || passport.events || [];
    const eventsList = events.map(event => {
      const eventStatus = event.blockchain_status || event.status || 'pending';
      const txId = event.blockchain_tx_id || event.tx_id;
      return `
        <li class="${esc(eventStatus.toLowerCase())}">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
            <b>${esc(event.event_type_label || event.event_type || 'Supply-chain event')}</b>
            ${badge(eventStatus)}
          </div>
          <small>${esc(event.actor_org || 'Supply-chain participant')} · ${fmtDate(event.occurred_at || event.event_time)}</small>
          ${txId ? `<small style="font-family:monospace;color:var(--forest);margin-top:4px">Tx: ${esc(txId)}</small>` : ''}
        </li>`;
    }).join('');
    const product = passport.product || `${passport.crop_name || 'Product'}${passport.variety ? ` (${passport.variety})` : ''}`;
    const origin = passport.origin || [passport.farm?.name, passport.farm?.district, passport.farm?.region].filter(Boolean).join(', ') || 'Origin details unavailable';
    const verification = passport.verification || passport.status_label || (passport.verified ? 'CONFIRMED' : passport.status);

    resultContainer.innerHTML = `
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:8px">
          <div><div class="eyebrow">Product Passport</div><h2 style="font-size:26px;margin:4px 0 0;color:var(--forest)">${esc(product)}</h2></div>
          ${badge(verification)}
        </div>
        <p style="color:var(--mute);margin:8px 0 20px;font-size:15px">
          Batch ID: <b style="color:var(--ink)">${esc(passport.batch_code)}</b> ·
          Origin: <b style="color:var(--ink)">${esc(origin)}</b>
        </p>
        <hr style="border:0;border-top:1px solid var(--line);margin:20px 0">
        <h3 style="font-size:17px;margin:0 0 16px;color:var(--forest)">Supply Chain History &amp; Audit Trail</h3>
        ${eventsList ? `<ol class="timeline">${eventsList}</ol>` : '<p class="state">No public supply-chain events have been recorded yet.</p>'}
        <div style="background:#fbf9f4;border:1px dashed var(--line);border-radius:12px;padding:14px 18px;margin-top:24px;font-size:13px;color:var(--mute)">
          <b>Verification:</b> Passport status is based on the batch record. Ledger transaction details appear when available.
        </div>
      </div>`;
  } catch (err) {
    resultContainer.innerHTML = `<div class="err" role="alert"><strong>Batch lookup error:</strong> ${esc(err.message)}</div>`;
  }
}
