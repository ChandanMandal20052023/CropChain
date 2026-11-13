import { api, badge, esc, fmtDate } from './api.js';
import './app.js';

const resultContainer = document.getElementById('result');
const codeInput = document.getElementById('code');
const form = document.getElementById('trackForm');

// Parse initial URL query parameter
const urlParams = new URLSearchParams(window.location.search);
const initialBatchCode = urlParams.get('batch');

if (initialBatchCode && codeInput) {
  codeInput.value = initialBatchCode;
  fetchAndRenderPassport(initialBatchCode);
}

if (form) {
  form.addEventListener('submit', event => {
    event.preventDefault();
    const code = codeInput ? codeInput.value.trim() : '';
    if (code) {
      // Update browser URL without reloading
      const newUrl = `${window.location.pathname}?batch=${encodeURIComponent(code)}`;
      window.history.pushState({ path: newUrl }, '', newUrl);
      fetchAndRenderPassport(code);
    }
  });
}

/**
 * Fetch and render product passport
 */
async function fetchAndRenderPassport(batchCode) {
  if (!batchCode) {
    resultContainer.innerHTML = '<div class="state">Please enter a valid batch code.</div>';
    return;
  }

  resultContainer.innerHTML = `
    <div class="state">
      <div style="font-size: 24px; margin-bottom: 8px;">🔄</div>
      Verifying ledger records for <b>${esc(batchCode)}</b>…
    </div>
  `;

  try {
    const passport = await api(`/public/track/${encodeURIComponent(batchCode)}/`, {
      auth: false
    });

    const eventsList = (passport.events || []).map(event => {
      const statusClass = (event.status || 'pending').toLowerCase();
      const txInfo = event.tx_id
        ? `<small style="font-family: monospace; color: var(--forest); margin-top: 4px;">Tx: ${esc(event.tx_id)}</small>`
        : '<small style="color: var(--mute); margin-top: 4px;">Awaiting consensus confirmation</small>';

      return `
        <li class="${statusClass}">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
            <b>${esc(event.event_type)}</b>
            ${badge(event.status)}
          </div>
          <small>${esc(event.actor_org)} · ${fmtDate(event.event_time)}</small>
          ${txInfo}
        </li>
      `;
    }).join('');

    resultContainer.innerHTML = `
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 8px;">
          <div>
            <div class="eyebrow">Verified Product Passport</div>
            <h2 style="font-size: 26px; margin: 4px 0 0; color: var(--forest);">${esc(passport.product)}</h2>
          </div>
          ${badge(passport.verification)}
        </div>

        <p style="color: var(--mute); margin: 8px 0 20px; font-size: 15px;">
          Batch ID: <b style="color: var(--ink);">${esc(passport.batch_code)}</b> · 
          Origin: <b style="color: var(--ink);">${esc(passport.origin)}</b>
        </p>

        <hr style="border: 0; border-top: 1px solid var(--line); margin: 20px 0;">

        <h3 style="font-size: 17px; margin: 0 0 16px; color: var(--forest);">Supply Chain History & Audit Trail</h3>
        <ol class="timeline">
          ${eventsList}
        </ol>

        <div style="background: #fbf9f4; border: 1px dashed var(--line); border-radius: 12px; padding: 14px 18px; margin-top: 24px; font-size: 13px; color: var(--mute);">
          🛡️ <b>Cryptographic Verification:</b> All confirmed milestones are recorded on Hyperledger Fabric with immutable consensus.
        </div>
      </div>
    `;
  } catch (err) {
    resultContainer.innerHTML = `
      <div class="err" role="alert">
        <strong>Batch lookup error:</strong> ${esc(err.message)}
      </div>
    `;
  }
}

