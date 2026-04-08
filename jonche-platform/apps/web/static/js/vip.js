/* ── VIP Page JS ───────────────────────────────────────────────────────────── */

async function loadVip() {
  const countsEl = document.getElementById('vip-counts');
  const recentEl = document.getElementById('vip-recent');
  if (!countsEl || !recentEl) return;

  const counts = await apiFetch('/members/count');
  const members = await apiFetch('/members/');

  if (!counts) {
    countsEl.innerHTML = `<div class="muted">Unable to load member counts.</div>`;
  } else {
    countsEl.innerHTML = `
      <div class="kv-row"><div class="kv-k">Total</div><div class="kv-v mono">${counts.total}</div></div>
      <div class="kv-row"><div class="kv-k">Gold</div><div class="kv-v mono">${counts.gold}</div></div>
      <div class="kv-row"><div class="kv-k">Silver</div><div class="kv-v mono">${counts.silver}</div></div>
      <div class="kv-row"><div class="kv-k">Bronze</div><div class="kv-v mono">${counts.bronze}</div></div>
    `;
  }

  if (!members) {
    recentEl.innerHTML = `<div class="muted">Unable to load members.</div>`;
    return;
  }

  const top = members.slice(0, 10);
  recentEl.innerHTML = `
    <div class="table-head" style="grid-template-columns: 2fr 0.6fr 0.8fr 0.6fr;">
      <div>Member</div><div>Tier</div><div>Spend</div><div>Drops</div>
    </div>
    ${top.map(m => `
      <div class="table-row" style="grid-template-columns: 2fr 0.6fr 0.8fr 0.6fr;">
        <div>
          <div class="row-title">${m.name}</div>
          <div class="row-sub mono">${m.email}</div>
        </div>
        <div class="mono">${m.tier}</div>
        <div class="mono">$${Number(m.lifetime_spend).toLocaleString()}</div>
        <div class="mono">${m.drops}</div>
      </div>
    `).join('')}
  `;
}

document.addEventListener('DOMContentLoaded', loadVip);
