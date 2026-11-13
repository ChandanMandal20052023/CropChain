import { api, badge, esc } from './api.js';
import './app.js';

const rowsBody = document.getElementById('rows');
const statsContainer = document.getElementById('stats');
const whoLabel = document.getElementById('who');
const logoutBtn = document.getElementById('logoutBtn');
const farmSelect = document.getElementById('farmId');
const farmPanel = document.getElementById('farmPanel');

// Handle Sign Out
if (logoutBtn) {
  logoutBtn.addEventListener('click', event => {
    event.preventDefault();
    sessionStorage.removeItem('cc_token');
    sessionStorage.removeItem('cc_user');
    window.location.href = 'login.html';
  });
}

/**
 * Initialize Dashboard Data
 */
async function loadDashboard() {
  try {
    // Attempt profile & batch retrieval
    const [me, batchesData, farmsData] = await Promise.all([
      api('/auth/me/').catch(() => api('/me/')),
      api('/batches/?mine=true'),
      api('/farms/?mine=true').catch(() => [])
    ]);

    // Handle both DRF paginated ({ results: [...] }) and flat array responses
    const batches = Array.isArray(batchesData) ? batchesData : batchesData.results || [];
    const farms = Array.isArray(farmsData) ? farmsData : farmsData.results || [];
    if (farmSelect) {
      farmSelect.innerHTML = farms.length
        ? farms.map(farm => `<option value="${farm.id}">${esc(farm.name)} (${esc(farm.farm_code)})${farm.is_verified ? '' : ' — awaiting verification'}</option>`).join('')
        : '<option value="">Register a farm before creating a batch</option>';
      farmSelect.disabled = farms.length === 0;
    }

    // Render User Identity
    const displayName = me.full_name || me.name || me.email;
    const displayRole = me.role_label || me.role || 'Participant';
    const displayOrg = me.organization || 'Independent Operator';
    whoLabel.textContent = `${displayName} · ${displayRole} · ${displayOrg}`;
    if (farmPanel) farmPanel.hidden = me.role !== 'farmer';

    // Render Stats
    const totalCount = batches.length;
    const confirmedCount = batches.filter(b => (b.status || '').toUpperCase() === 'CONFIRMED' || (b.status || '').toUpperCase() === 'SOLD').length;
    const pendingCount = batches.filter(b => ['DRAFT', 'HARVESTED', 'IN_TRANSIT', 'PROCESSING', 'PACKED'].includes((b.status || '').toUpperCase())).length;
    const attentionCount = batches.filter(b => (b.status || '').toUpperCase() === 'RECALLED').length;

    statsContainer.innerHTML = [
      ['Total Batches', totalCount, 'var(--forest)'],
      ['Confirmed on Ledger', confirmedCount, 'var(--green)'],
      ['Pending Milestones', pendingCount, 'var(--info)'],
      ['Attention Required', attentionCount, 'var(--bad)']
    ]
      .map(
        ([title, count, color]) => `
          <div class="stat">
            <b style="color: ${color};">${count}</b>
            <div>${title}</div>
          </div>
        `
      )
      .join('');

    // Render Table Rows
    if (batches.length > 0) {
      rowsBody.innerHTML = batches
        .map(batch => {
          const code = batch.batch_code || `BATCH-${batch.id}`;
          const cropDisplay = batch.variety ? `${esc(batch.crop_name)} (${esc(batch.variety)})` : esc(batch.crop_name);
          const stageDisplay = esc(batch.current_stage || batch.status_label || batch.status);
          const quantityDisplay = `${esc(batch.quantity)} ${esc(batch.unit || 'kg')}`;

          return `
            <tr>
              <td>
                <a href="track.html?batch=${encodeURIComponent(code)}" style="color: var(--forest); font-weight: 600;">
                  ${esc(code)} &rarr;
                </a>
              </td>
              <td>${cropDisplay}</td>
              <td>${quantityDisplay}</td>
              <td>${stageDisplay}</td>
              <td>${badge(batch.status)}</td>
            </tr>
          `;
        })
        .join('');
    } else {
      rowsBody.innerHTML = `
        <tr>
          <td colspan="5" class="state">No batches recorded yet. Submit your first harvest batch below.</td>
        </tr>
      `;
    }
  } catch (err) {
    if (err.status === 401) {
      window.location.href = 'login.html';
      return;
    }
    rowsBody.innerHTML = `
      <tr>
        <td colspan="5">
          <div class="err" role="alert">${esc(err.message)}</div>
        </td>
      </tr>
    `;
  }
}

/**
 * Handle Batch Creation
 */
const batchForm = document.getElementById('batchForm');
if (batchForm) {
  batchForm.addEventListener('submit', async event => {
    event.preventDefault();
    const msgBox = document.getElementById('msg');
    msgBox.innerHTML = '';

    const qty = parseFloat(batchForm.quantity.value);
    if (!(qty > 0)) {
      msgBox.innerHTML = '<div class="err">Quantity must be greater than zero.</div>';
      return;
    }

    const payload = {
      farm: Number(batchForm.farmId.value),
      crop_name: batchForm.crop.value.trim(),
      variety: batchForm.variety.value.trim(),
      quantity: qty,
      unit: 'kg',
      harvest_date: batchForm.harvest.value,
      description: batchForm.description.value.trim(),
      is_public: true
    };

    if (!payload.farm) {
      msgBox.innerHTML = '<div class="err">Register a farm before creating a batch.</div>';
      return;
    }

    try {
      const result = await api('/batches/', {
        method: 'POST',
        body: payload
      });

      const newCode = result.batch_code || 'newly created batch';
      msgBox.innerHTML = `
        <div style="background: var(--mint); color: var(--green); padding: 12px 16px; border-radius: 10px; font-weight: 500;">
          ✓ Successfully registered <b>${esc(newCode)}</b>. Status is Draft.
        </div>
      `;
      batchForm.reset();
      loadDashboard();
    } catch (err) {
      msgBox.innerHTML = `<div class="err" role="alert">${esc(err.message)}</div>`;
    }
  });
}

const farmForm = document.getElementById('farmForm');
if (farmForm) {
  farmForm.addEventListener('submit', async event => {
    event.preventDefault();
    const farmMsg = document.getElementById('farmMsg');
    const size = farmForm.size_hectares.value;
    const payload = {
      name: farmForm.elements.namedItem('name').value.trim(),
      region: farmForm.region.value.trim(),
      district: farmForm.district.value.trim(),
      village: farmForm.village.value.trim(),
      country: farmForm.country.value.trim(),
      ...(size ? { size_hectares: Number(size) } : {})
    };
    farmMsg.innerHTML = '';
    try {
      const farm = await api('/farms/', { method: 'POST', body: payload });
      farmMsg.innerHTML = `<div style="color:var(--green)">Farm ${esc(farm.farm_code)} saved.</div>`;
      farmForm.reset();
      farmForm.country.value = 'India';
      await loadDashboard();
    } catch (err) {
      farmMsg.innerHTML = `<div class="err" role="alert">${esc(err.message)}</div>`;
    }
  });
}

// Initial invocation
loadDashboard();

