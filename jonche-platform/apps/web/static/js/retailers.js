/* ── Retailers Page JS ─────────────────────────────────────────────────────── */

async function loadRetailers() {
  const root = document.getElementById('retailers-root');
  if (!root) return;

  const retailers = await apiFetch('/retailers/');
  if (!retailers) {
    root.innerHTML = `<div class="muted">Unable to load retailers (admin login required).</div>`;
    return;
  }

  root.innerHTML = `
    <div class="table-head" style="grid-template-columns: 2fr 0.8fr 0.6fr 0.8fr 0.8fr;">
      <div>Retailer</div><div>Status</div><div>Tier</div><div>City</div><div>Created</div>
    </div>
    ${retailers.map(r => `
      <div class="table-row" style="grid-template-columns: 2fr 0.8fr 0.6fr 0.8fr 0.8fr;">
        <div>
          <div class="row-title">${r.name}</div>
          <div class="row-sub mono">${r.email}</div>
        </div>
        <div class="mono">${r.status}</div>
        <div class="mono">${r.tier}</div>
        <div class="mono">${r.city || '—'}</div>
        <div class="mono">${r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'}</div>
      </div>
    `).join('')}
  `;
}

document.addEventListener('DOMContentLoaded', loadRetailers);
