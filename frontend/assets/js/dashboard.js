import { api, badge, esc } from './api.js';
import './app.js';

const rowsBody = document.getElementById('rows');
const statsContainer = document.getElementById('stats');
const whoLabel = document.getElementById('who');
const logoutBtn = document.getElementById('logoutBtn');

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
    const [me, batchesData] = await Promise.all([
      api('/auth/me/').catch(() => api('/me/')),
      api('/batches/')
    ]);

    // Handle both DRF paginated ({ results: [...] }) and flat array responses
    const batches = Array.isArray(batchesData) ? batchesData : batchesData.results || [];

    // Render User Identity
    const displayName = me.full_name || me.name || me.email;
    const displayRole = me.role_label || me.role || 'Participant';
    const displayOrg = me.organization || 'Independent Operator';
    whoLabel.textContent = `${displayName} · ${displayRole} · ${displayOrg}`;

    // Render Stats
    const totalCount = batches.length;
    const confirmedCount = batches.filter(b => (b.status || '').toUpperCase() === 'CONFIRMED' || (b.status || '').toUpperCase() === 'SOLD').length;
    const pendingCount = batches.filter(b => (b.status || '').toUpperCase() === 'PENDING' || (b.status || '').toUpperCase() === 'DRAFT' || (b.status || '').toUpperCase() === 'IN_TRANSIT').length;
    const attentionCount = batches.filter(b => (b.status || '').toUpperCase() === 'FAILED' || (b.status || '').toUpperCase() === 'RECALLED').length;

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
      farm: parseInt(batchForm.farmId.value, 10) || 1,
      crop_name: batchForm.crop.value.trim(),
      variety: batchForm.variety.value.trim(),
      quantity: qty,
      unit: 'kg',
      harvest_date: batchForm.harvest.value,
      description: batchForm.description.value.trim(),
      is_public: true
    };

    try {
      const result = await api('/batches/', {
        method: 'POST',
        body: payload
      });

      const newCode = result.batch_code || 'newly created batch';
      msgBox.innerHTML = `
        <div style="background: var(--mint); color: var(--green); padding: 12px 16px; border-radius: 10px; font-weight: 500;">
          ✓ Successfully registered <b>${esc(newCode)}</b>. Status is pending confirmation.
        </div>
      `;
      batchForm.reset();
      loadDashboard();
    } catch (err) {
      msgBox.innerHTML = `<div class="err" role="alert">${esc(err.message)}</div>`;
    }
  });
}

// Initial invocation
loadDashboard();

