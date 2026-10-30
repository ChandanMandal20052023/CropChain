// Shared API helper (blueprint §6.3): adds auth, handles JSON, HTTP errors and network failures.
export const CONFIG = { API_BASE: '/api/v1', DEMO_MODE: true }; // set DEMO_MODE=false once Django is running

const DEMO = {
  me: { name: 'Demo Farmer', role: 'Farmer / Grower', organization: 'Demo Farm Co-op' },
  batches: [
    { batch_code: 'CC-2026-00123', crop_name: 'Basmati Rice', quantity: 450, unit: 'kg', current_stage: 'Warehouse', status: 'CONFIRMED' },
    { batch_code: 'CC-2026-00124', crop_name: 'Wheat', quantity: 800, unit: 'kg', current_stage: 'Collection Center', status: 'PENDING' },
    { batch_code: 'CC-2026-00125', crop_name: 'Mustard', quantity: 300, unit: 'kg', current_stage: 'Farm', status: 'FAILED' }
  ],
  passport: {
    batch_code: 'CC-2026-00123', product: 'Basmati Rice', origin: 'Farm, Punjab', verification: 'CONFIRMED',
    events: [
      { event_type: 'Harvested', actor_org: 'Demo Farm Co-op', event_time: '2026-10-10T08:00:00+05:30', status: 'CONFIRMED', tx_id: 'demo-tx-001' },
      { event_type: 'Collection Center Intake', actor_org: 'Demo Collection Center', event_time: '2026-10-12T11:15:00+05:30', status: 'CONFIRMED', tx_id: 'demo-tx-002' },
      { event_type: 'Warehouse Received', actor_org: 'Demo Warehouse', event_time: '2026-10-17T10:30:00+05:30', status: 'PENDING', tx_id: null }
    ]
  }
};

export class ApiError extends Error { constructor(msg, status, body) { super(msg); this.status = status; this.body = body; } }

export async function api(path, { method = 'GET', body, auth = true } = {}) {
  if (CONFIG.DEMO_MODE) return demo(path, method);
  const headers = { 'Content-Type': 'application/json' };
  const token = sessionStorage.getItem('cc_token');
  if (auth && token) headers.Authorization = `Bearer ${token}`;
  let res;
  try { res = await fetch(CONFIG.API_BASE + path, { method, headers, body: body ? JSON.stringify(body) : undefined }); }
  catch { throw new ApiError('Cannot reach the server. Check your connection and try again.', 0); }
  let data = null; try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) throw new ApiError(data?.detail || data?.message || `Request failed (${res.status})`, res.status, data);
  return data;
}

function demo(path) {
  return new Promise((resolve, reject) => setTimeout(() => {
    if (path.startsWith('/auth/login')) return resolve({ token: 'demo-token' });
    if (path === '/me/') return resolve(DEMO.me);
    if (path === '/batches/') return resolve(DEMO.batches);
    if (path.startsWith('/public/track/')) {
      const code = decodeURIComponent(path.split('/')[3] || '').toUpperCase();
      return code === DEMO.passport.batch_code ? resolve(DEMO.passport) : reject(new ApiError('Batch not found.', 404));
    }
    resolve({});
  }, 350));
}

export const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const LABEL = { CONFIRMED: ['confirmed', 'Confirmed'], PENDING: ['pending', 'Pending'], FAILED: ['failed', 'Failed'], ATTENTION: ['attention', 'Needs Attention'] };
export const badge = s => { const [c, t] = LABEL[s] || LABEL.ATTENTION; return `<span class="badge ${c}">${t}</span>`; };
export const fmtDate = iso => new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
