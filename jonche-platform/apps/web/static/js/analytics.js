/* ── Analytics Page JS ─────────────────────────────────────────────────────── */

async function loadAnalytics() {
  const revenueEl = document.getElementById('analytics-revenue');
  const hypeEl = document.getElementById('analytics-hype');
  if (!revenueEl || !hypeEl) return;

  const revenue = await apiFetch('/analytics/revenue');
  const hype = await apiFetch('/analytics/hype');

  if (!revenue) {
    revenueEl.innerHTML = `<div class="muted">Unable to load revenue analytics.</div>`;
  } else {
    revenueEl.innerHTML = `
      <div class="table-head" style="grid-template-columns: 2fr 0.8fr 0.6fr;">
        <div>Drop</div><div>Revenue</div><div>Orders</div>
      </div>
      ${revenue.map(r => `
        <div class="table-row" style="grid-template-columns: 2fr 0.8fr 0.6fr;">
          <div class="row-title">${r.drop}</div>
          <div class="mono">$${Number(r.revenue).toLocaleString()}</div>
          <div class="mono">${r.orders}</div>
        </div>
      `).join('')}
    `;
  }

  if (!hype) {
    hypeEl.innerHTML = `<div class="muted">Unable to load hype analytics.</div>`;
  } else {
    hypeEl.innerHTML = `
      <div class="table-head" style="grid-template-columns: 2fr 0.8fr 0.9fr;">
        <div>Drop</div><div>Hype</div><div>Units Available</div>
      </div>
      ${hype.map(h => `
        <div class="table-row" style="grid-template-columns: 2fr 0.8fr 0.9fr;">
          <div class="row-title">${h.name}</div>
          <div class="mono">${h.hype_pct}%</div>
          <div class="mono">${h.units_available}</div>
        </div>
      `).join('')}
    `;
  }
}

document.addEventListener('DOMContentLoaded', loadAnalytics);
