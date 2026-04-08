/* ── Dashboard JS ────────────────────────────────────────────────────────────── */

async function loadDashboard() {
  const stats = await apiFetch('/stats/overview');
  if (!stats) return;

  document.getElementById('stats-row').innerHTML = `
    <div class="stat-card">
      <div class="stat-label">Total Revenue</div>
      <div class="stat-value"><span>$</span>${stats.revenue.toLocaleString()}</div>
      <div class="stat-change up">↑ ${stats.revenue_growth}% this month</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Units Dropped</div>
      <div class="stat-value">${stats.units_dropped.toLocaleString()}</div>
      <div class="stat-change up">↑ ${stats.drops_completed} drops completed</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Sell-Through Rate</div>
      <div class="stat-value"><span>${stats.sell_through}%</span></div>
      <div class="stat-change up">↑ Supply controlled</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">VIP Members</div>
      <div class="stat-value"><span>${stats.vip_members}</span></div>
      <div class="stat-change up">↑ ${stats.new_vip_this_week} new this week</div>
    </div>
  `;
}

document.addEventListener('DOMContentLoaded', loadDashboard);
