import { api, badge, esc } from './api.js';
import './app.js';
const body = document.getElementById('rows'), stats = document.getElementById('stats');
try {
  const [me, batches] = await Promise.all([api('/me/'), api('/batches/')]);
  document.getElementById('who').textContent = `${me.name} · ${me.role} · ${me.organization}`;
  const n = s => batches.filter(b => b.status === s).length;
  stats.innerHTML = [['Total batches', batches.length], ['Confirmed', n('CONFIRMED')], ['Pending', n('PENDING')], ['Failed / needs attention', n('FAILED') + n('ATTENTION')]]
    .map(([l, v]) => `<div class="stat"><b>${v}</b><div>${l}</div></div>`).join('');
  body.innerHTML = batches.length ? batches.map(b => `<tr><td><a href="track.html?batch=${encodeURIComponent(b.batch_code)}"><b>${esc(b.batch_code)}</b></a></td>
    <td>${esc(b.crop_name)}</td><td>${esc(b.quantity)} ${esc(b.unit)}</td><td>${esc(b.current_stage)}</td><td>${badge(b.status)}</td></tr>`).join('')
    : '<tr><td colspan="5" class="state">No batches yet. Create your first batch.</td></tr>';
} catch (e) {
  if (e.status === 401) location.href = 'login.html';
  body.innerHTML = `<tr><td colspan="5"><div class="err" role="alert">${esc(e.message)}</div></td></tr>`;
}
document.getElementById('batchForm').addEventListener('submit', async ev => {
  ev.preventDefault(); const f = ev.target, msg = document.getElementById('msg');
  const qty = Number(f.quantity.value);
  if (!(qty > 0)) { msg.innerHTML = '<div class="err">Quantity must be greater than zero.</div>'; return; }
  try {
    await api('/batches/', { method: 'POST', body: { crop_name: f.crop.value, quantity: qty, unit: 'kg', harvest_date: f.harvest.value, origin: f.origin.value } });
    msg.innerHTML = '<span class="badge pending">Pending</span> Submitted. It shows as Confirmed only after the backend confirms the ledger transaction.';
  } catch (x) { msg.innerHTML = `<div class="err" role="alert">${esc(x.message)}</div>`; }
});
