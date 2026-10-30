import { api, badge, esc, fmtDate } from './api.js';
import './app.js';
const out = document.getElementById('result');
const code = new URLSearchParams(location.search).get('batch');
const input = document.getElementById('code'); if (code) input.value = code;
document.getElementById('trackForm').addEventListener('submit', e => { e.preventDefault(); load(input.value.trim()); });
async function load(c) {
  if (!c) { out.innerHTML = '<div class="state">Enter a batch ID to view its product passport.</div>'; return; }
  out.innerHTML = '<div class="state">Loading…</div>';
  try {
    const p = await api(`/public/track/${encodeURIComponent(c)}/`, { auth: false });
    out.innerHTML = `<div class="card"><div class="eyebrow">Product passport</div><h2>${esc(p.product)}</h2>
      <p>Batch ID: <b>${esc(p.batch_code)}</b> · Origin: ${esc(p.origin)}</p>${badge(p.verification)}
      <ol class="timeline">${p.events.map(ev => `<li class="${ev.status.toLowerCase()}"><b>${esc(ev.event_type)}</b> ${badge(ev.status)}
        <small>${esc(ev.actor_org)} · ${fmtDate(ev.event_time)}</small>
        <small>${ev.tx_id ? 'Tx: ' + esc(ev.tx_id) : 'Awaiting ledger confirmation'}</small></li>`).join('')}</ol></div>`;
  } catch (err) {
    out.innerHTML = `<div class="err" role="alert">${esc(err.message)}</div>`;
  }
}
load(code);
