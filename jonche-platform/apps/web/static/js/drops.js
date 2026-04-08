/* ── Drops Page JS ─────────────────────────────────────────────────────────── */

function statusClass(status) {
  if (status === 'live') return 'status-live';
  if (status === 'upcoming') return 'status-soon';
  if (status === 'sold_out' || status === 'ended') return 'status-sold';
  return 'status-draft';
}

async function loadDrops() {
  const root = document.getElementById('drops-root');
  if (!root) return;

  const drops = await apiFetch('/drops/');
  if (!drops) {
    root.innerHTML = `<div class="muted">Unable to load drops.</div>`;
    return;
  }

  root.innerHTML = `
    <div class="table-head" style="grid-template-columns: 2fr 0.8fr 0.7fr 0.7fr 0.6fr 1fr;">
      <div>Name</div><div>Status</div><div>Price</div><div>Units</div><div>Hype</div><div>Drop At</div>
    </div>
    ${drops.map(d => `
      <div class="table-row" style="grid-template-columns: 2fr 0.8fr 0.7fr 0.7fr 0.6fr 1fr;">
        <div>
          <div class="row-title">${d.name}</div>
          <div class="row-sub mono">${d.slug} • ${d.colorway}</div>
        </div>
        <div><span class="drop-status ${statusClass(d.status)}">${d.status}</span></div>
        <div class="mono">$${Number(d.price_dollars).toLocaleString()}</div>
        <div class="mono">${d.units_sold}/${d.total_units}</div>
        <div class="mono">${d.hype_pct}%</div>
        <div class="mono">${d.drop_at ? new Date(d.drop_at).toLocaleString() : '—'}</div>
      </div>
    `).join('')}
  `;
}

document.addEventListener('DOMContentLoaded', loadDrops);
