/**
 * CropChain API Client & State Helper
 * Supports live Django REST Framework API communication and zero-config demo mode.
 */

export const CONFIG = {
  // Override in the page before loading this module when using another host.
  API_BASE: (window.CROPCHAIN_API_BASE || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, ''),
  DEMO_MODE: window.CROPCHAIN_DEMO_MODE === true
};

// Built-in demonstration mock state
const DEMO = {
  me: {
    id: 1,
    name: 'Demo Farmer',
    email: 'farmer@example.com',
    role: 'farmer',
    role_label: 'Farmer / Grower',
    organization: 'Green Valley Organic Co-op'
  },
  batches: [
    {
      id: 1,
      batch_code: 'CC-2026-00123',
      crop_name: 'Basmati Rice',
      variety: 'Pusa 1121',
      quantity: 450,
      unit: 'kg',
      current_stage: 'Warehouse',
      status: 'CONFIRMED',
      status_label: 'Confirmed',
      created_at: '2026-10-10T08:00:00Z'
    },
    {
      id: 2,
      batch_code: 'CC-2026-00124',
      crop_name: 'Wheat',
      variety: 'Sharbati Gold',
      quantity: 800,
      unit: 'kg',
      current_stage: 'Collection Center',
      status: 'PENDING',
      status_label: 'Pending',
      created_at: '2026-10-14T09:30:00Z'
    },
    {
      id: 3,
      batch_code: 'CC-2026-00125',
      crop_name: 'Mustard Seeds',
      variety: 'Brassica Pusa',
      quantity: 300,
      unit: 'kg',
      current_stage: 'Farm',
      status: 'FAILED',
      status_label: 'Needs Attention',
      created_at: '2026-10-18T11:15:00Z'
    }
  ],
  farms: [{ id: 1, farm_code: 'FARM-DEMO01', name: 'Green Valley Organic Farm', is_verified: true }],
  passport: {
    batch_code: 'CC-2026-00123',
    product: 'Basmati Rice (Pusa 1121)',
    origin: 'Green Valley Organic Farm, Majitha, Punjab',
    verification: 'CONFIRMED',
    quantity: '450 kg',
    events: [
      {
        event_type: 'Harvested & Anchored',
        actor_org: 'Green Valley Organic Co-op',
        event_time: '2026-10-10T08:00:00+05:30',
        status: 'CONFIRMED',
        tx_id: 'tx_0x9f18a24c8e71b'
      },
      {
        event_type: 'Collection Center Intake & Grading',
        actor_org: 'Majitha Regional Aggregator',
        event_time: '2026-10-12T11:15:00+05:30',
        status: 'CONFIRMED',
        tx_id: 'tx_0x4b72e19d3f56a'
      },
      {
        event_type: 'Cold Storage Vault Received',
        actor_org: 'Amritsar Central Agro-Logistics',
        event_time: '2026-10-17T10:30:00+05:30',
        status: 'CONFIRMED',
        tx_id: 'tx_0x82c14f09a12e8'
      },
      {
        event_type: 'Quality Inspection & Moisture Testing',
        actor_org: 'AgroQACert Labs (Moisture: 12.1%, Grade A)',
        event_time: '2026-10-20T14:00:00+05:30',
        status: 'CONFIRMED',
        tx_id: 'tx_0x61a8f902c4b7d'
      },
      {
        event_type: 'Retail Supermarket Distribution',
        actor_org: 'NatureBasket Supermarkets, New Delhi',
        event_time: '2026-10-25T09:00:00+05:30',
        status: 'PENDING',
        tx_id: null
      }
    ]
  }
};

export class ApiError extends Error {
  constructor(message, status = 0, body = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

/**
 * Universal API Request Handler
 */
export async function api(path, { method = 'GET', body, auth = true } = {}) {
  // Ensure path starts with a slash
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;

  // Use simulation in demo mode
  if (CONFIG.DEMO_MODE) {
    return simulateDemo(normalizedPath, method, body);
  }

  const headers = { 'Content-Type': 'application/json' };
  const token = sessionStorage.getItem('cc_token');

  if (auth && token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let res;
  try {
    res = await fetch(`${CONFIG.API_BASE}${normalizedPath}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined
    });
  } catch (err) {
    throw new ApiError('Cannot connect to backend server. Please verify Django is running.', 0);
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    // Empty body response (e.g. 204 No Content)
  }

  if (!res.ok) {
    const errorMsg =
      data?.detail ||
      data?.message ||
      (typeof data === 'object' ? JSON.stringify(data) : `Request failed with status ${res.status}`);
    throw new ApiError(errorMsg, res.status, data);
  }

  return data;
}

/**
 * Demo Mode API Mock Handler
 */
function simulateDemo(path, method, body) {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      // Authentication
      if (path.startsWith('/auth/login')) {
        return resolve({
          access: 'demo-jwt-access-token',
          token: 'demo-jwt-access-token',
          user: DEMO.me
        });
      }

      // User profile
      if (path.startsWith('/auth/me') || path === '/me/') {
        return resolve(DEMO.me);
      }

      // Batch listing
      if (path.startsWith('/batches/') || path === '/batches') {
        if (method === 'POST') {
          const newBatch = {
            id: DEMO.batches.length + 1,
            batch_code: `CC-${new Date().getFullYear()}-${String(DEMO.batches.length + 1).padStart(5, '0')}`,
            crop_name: body.crop_name || 'Crop',
            quantity: body.quantity || 100,
            unit: body.unit || 'kg',
            current_stage: 'Farm',
            status: 'PENDING',
            status_label: 'Pending'
          };
          DEMO.batches.unshift(newBatch);
          return resolve(newBatch);
        }
        return resolve(DEMO.batches);
      }

      if (path.startsWith('/farms/')) {
        if (method === 'POST') {
          const farm = { id: DEMO.farms.length + 1, farm_code: `FARM-DEMO${String(DEMO.farms.length + 1).padStart(2, '0')}`, name: body.name, is_verified: false };
          DEMO.farms.push(farm);
          return resolve(farm);
        }
        return resolve(DEMO.farms);
      }

      // Public track
      if (path.startsWith('/public/track/')) {
        const parts = path.split('/');
        const code = decodeURIComponent(parts[3] || '').trim().toUpperCase();
        if (code === DEMO.passport.batch_code || code === 'CC-2026-00123') {
        return resolve({
          ...DEMO.passport,
          crop_name: 'Basmati Rice',
          variety: 'Pusa 1121',
          farm: { name: 'Green Valley Organic Farm', region: 'Punjab', district: 'Majitha' },
          verified: true,
          public_events: DEMO.passport.events.map(event => ({
            event_type_label: event.event_type,
            occurred_at: event.event_time,
            blockchain_status: event.status.toLowerCase(),
            blockchain_tx_id: event.tx_id
          }))
        });
        }
        return reject(new ApiError(`Batch with code "${code}" not found. Try demo code "CC-2026-00123".`, 404));
      }

      resolve({});
    }, 250);
  });
}

/**
 * Utility Helpers
 */
export const esc = s =>
  String(s ?? '').replace(
    /[&<>"']/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
  );

const STATUS_MAP = {
  CONFIRMED: ['confirmed', 'Confirmed on Ledger'],
  PENDING: ['pending', 'Pending Confirmation'],
  FAILED: ['failed', 'Verification Failed'],
  ATTENTION: ['attention', 'Needs Attention'],
  HARVESTED: ['confirmed', 'Harvested'],
  IN_TRANSIT: ['pending', 'In Transit'],
  PACKED: ['confirmed', 'Packed'],
  DRAFT: ['pending', 'Draft'],
  PROCESSING: ['pending', 'Processing'],
  DELIVERED: ['confirmed', 'Delivered'],
  SOLD: ['confirmed', 'Sold'],
  RECALLED: ['failed', 'Recalled']
};

export const badge = s => {
  const [cssClass, label] = STATUS_MAP[String(s).toUpperCase()] || ['attention', s || 'Unknown'];
  return `<span class="badge ${cssClass}">${esc(label)}</span>`;
};

export const fmtDate = iso => {
  if (!iso) return 'Date unspecified';
  try {
    return new Date(iso).toLocaleString('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short'
    });
  } catch {
    return iso;
  }
};

