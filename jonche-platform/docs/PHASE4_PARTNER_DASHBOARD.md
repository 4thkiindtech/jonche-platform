# Phase 4 Lite - Partner Earnings Dashboard

## Partner-Facing Earnings Display

### Key Metric: Projected Earnings

Partners need transparency into:
- **Pending**: Earnings awaiting admin approval
- **Approved**: Approved payouts ready to go
- **Projected**: Next payout amount
- **Next Payout Date**: When they'll receive payment

---

## Affiliate Dashboard Widget

```html
<div class="earnings-widget affiliate">
  <h3>📊 Your Earnings</h3>

  <div class="earnings-grid">
    <!-- Pending Earnings -->
    <div class="metric-card pending">
      <div class="metric-label">Pending Approval</div>
      <div class="metric-value" id="pending-amount">$0.00</div>
      <div class="metric-detail">
        From <span id="pending-count">0</span> orders
      </div>
    </div>

    <!-- Approved (Ready to Pay) -->
    <div class="metric-card approved">
      <div class="metric-label">Approved for Payment</div>
      <div class="metric-value" id="approved-amount">$0.00</div>
      <div class="metric-detail">
        <!-- Show if there's money approvals waiting -->
      </div>
    </div>

    <!-- Projected Next Payout -->
    <div class="metric-card projected">
      <div class="metric-label">💰 Next Payout</div>
      <div class="metric-value" id="projected-amount">$0.00</div>
      <div class="metric-detail">
        On <span id="payout-date">—</span>
      </div>
    </div>

    <!-- Payout Status -->
    <div class="metric-card status">
      <div class="metric-label">Status</div>
      <div class="status-badge" id="payout-status">Below Minimum</div>
      <div class="metric-detail" id="status-message">
        Need $10 more to trigger payout
      </div>
    </div>
  </div>

  <!-- Minimum Threshold Progress Bar -->
  <div class="threshold-section">
    <div class="threshold-label">
      <span>Monthly Minimum: $100.00</span>
      <span id="progress-pct">0%</span>
    </div>
    <div class="progress-bar">
      <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
    </div>
    <div class="threshold-info">
      You earn monthly payouts once you reach $100. Currently at <span id="current-pct">$0</span>.
    </div>
  </div>

  <!-- Recent Earnings List -->
  <div class="recent-earnings">
    <h4>Recent Earnings</h4>
    <div id="earningsList">
      <!-- Populated by JS -->
    </div>
  </div>

  <!-- Payout History -->
  <div class="payout-history">
    <h4>Previous Payouts</h4>
    <div id="payoutHistory">
      <!-- Populated by JS -->
    </div>
  </div>
</div>

<style>
.earnings-widget {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  border: 1px solid #e5e7eb;
  max-width: 600px;
}

.earnings-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin-bottom: 2rem;
}

.metric-card {
  padding: 1.5rem;
  border-radius: 8px;
  background: #f9fafb;
  border-left: 4px solid #d1d5db;
}

.metric-card.pending {
  border-left-color: #f59e0b;
  background: #fef3c7;
}

.metric-card.approved {
  border-left-color: #10b981;
  background: #d1fae5;
}

.metric-card.projected {
  border-left-color: #3b82f6;
  background: #dbeafe;
  grid-column: 1 / -1;
}

.metric-card.status {
  grid-column: auto;
}

.metric-label {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.metric-value {
  font-size: 1.75rem;
  font-weight: bold;
  color: #1f2937;
}

.metric-detail {
  font-size: 0.875rem;
  color: #999;
  margin-top: 0.5rem;
}

.status-badge {
  display: inline-block;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
  background: #fef3c7;
  color: #92400e;
}

.status-badge.ready {
  background: #d1fae5;
  color: #065f46;
}

.threshold-section {
  background: #f3f4f6;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.threshold-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #10b981);
  transition: width 0.3s ease;
}

.threshold-info {
  font-size: 0.75rem;
  color: #666;
  margin-top: 0.5rem;
}

.recent-earnings,
.payout-history {
  margin-top: 2rem;
}

.recent-earnings h4,
.payout-history h4 {
  font-size: 1rem;
  margin-bottom: 1rem;
  color: #1f2937;
}

.earning-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 0;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.875rem;
}

.earning-item:last-child {
  border-bottom: none;
}

.earning-date {
  color: #666;
}

.earning-amount {
  font-weight: 600;
  color: #3b82f6;
}

.earning-status {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  background: #e0e7ff;
  color: #3730a3;
}
</style>

<script>
const PARTNER_TYPE = 'affiliate'; // Set based on logged-in partner
const PARTNER_ID = getCurrentPartnerId(); // Get from session/JWT

async function loadEarnings() {
  try {
    const response = await fetch(
      `/api/partners/${PARTNER_TYPE}/${PARTNER_ID}/earnings`,
      {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('partner_token')}`
        }
      }
    );

    const earnings = await response.json();

    // Update metrics
    updateMetrics(earnings);
    updateProgressBar(earnings);
    loadRecentEarnings();
    loadPayoutHistory();

  } catch (error) {
    console.error('Failed to load earnings:', error);
  }
}

function updateMetrics(earnings) {
  // Pending amount
  document.getElementById('pending-amount').textContent = 
    `$${earnings.pending_dollars.toFixed(2)}`;
  
  document.getElementById('pending-count').textContent = 
    Math.ceil(earnings.pending_dollars / 15); // Estimate orders

  // Approved amount
  document.getElementById('approved-amount').textContent = 
    `$${earnings.approved_dollars.toFixed(2)}`;

  // Projected payout
  document.getElementById('projected-amount').textContent = 
    `$${earnings.projected_dollars.toFixed(2)}`;

  // Payout date
  if (earnings.next_payout_date) {
    const date = new Date(earnings.next_payout_date);
    document.getElementById('payout-date').textContent = 
      date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  // Status
  const statusBadge = document.getElementById('payout-status');
  const statusMsg = document.getElementById('status-message');

  if (earnings.meets_minimum) {
    statusBadge.textContent = '✅ Ready for Payout';
    statusBadge.className = 'status-badge ready';
    statusMsg.textContent = 'Your payout is approved and will be processed by end of month.';
  } else {
    const needed = earnings.minimum_threshold_dollars - earnings.pending_dollars;
    statusBadge.textContent = '⏳ Below Minimum';
    statusMsg.textContent = `Need $${needed.toFixed(2)} more to trigger payout.`;
  }
}

function updateProgressBar(earnings) {
  const minimum = earnings.minimum_threshold_cents;
  const current = earnings.pending_cents;
  const percentage = Math.min((current / minimum) * 100, 100);

  document.getElementById('progress-fill').style.width = `${percentage}%`;
  document.getElementById('progress-pct').textContent = `${Math.round(percentage)}%`;
  document.getElementById('current-pct').textContent = 
    `$${earnings.pending_dollars.toFixed(2)}`;
}

async function loadRecentEarnings() {
  try {
    // Fetch recent affiliate earnings (last 30 days)
    const response = await fetch(
      `/api/partners/${PARTNER_TYPE}/${PARTNER_ID}/recent-earnings?days=30`,
      {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('partner_token')}`
        }
      }
    );

    const earnings = await response.json();

    const list = document.getElementById('earningsList');
    if (!earnings || earnings.length === 0) {
      list.innerHTML = '<p style="color: #999; font-size: 0.875rem;">No recent earnings</p>';
      return;
    }

    list.innerHTML = earnings.map(e => `
      <div class="earning-item">
        <div>
          <div class="earning-date">${formatDate(e.created_at)}</div>
          <div style="font-size: 0.75rem; color: #999;">Order #${e.order_id}</div>
        </div>
        <div class="earning-amount">+$${(e.commission_cents/100).toFixed(2)}</div>
        <span class="earning-status">${e.status}</span>
      </div>
    `).join('');

  } catch (error) {
    console.error('Failed to load recent earnings:', error);
  }
}

async function loadPayoutHistory() {
  try {
    // Fetch paid payouts (last 6 months)
    const response = await fetch(
      `/api/partners/${PARTNER_TYPE}/${PARTNER_ID}/paid-payouts?months=6`,
      {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('partner_token')}`
        }
      }
    );

    const payouts = await response.json();

    const list = document.getElementById('payoutHistory');
    if (!payouts || payouts.length === 0) {
      list.innerHTML = '<p style="color: #999; font-size: 0.875rem;">No previous payouts</p>';
      return;
    }

    list.innerHTML = payouts.map(p => `
      <div class="earning-item">
        <div>
          <div class="earning-date">${formatDate(p.paid_at)}</div>
          <div style="font-size: 0.75rem; color: #999;">${p.payment_method}</div>
        </div>
        <div class="earning-amount">$${(p.net_amount_cents/100).toFixed(2)}</div>
        <span style="color: #10b981;">✓ Paid</span>
      </div>
    `).join('');

  } catch (error) {
    console.error('Failed to load payout history:', error);
  }
}

function formatDate(isoDate) {
  const date = new Date(isoDate);
  return date.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric',
    year: 'numeric'
  });
}

function getCurrentPartnerId() {
  // Get from JWT or session
  try {
    const token = localStorage.getItem('partner_token');
    if (!token) return null;
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.partner_id;
  } catch {
    return null;
  }
}

// Load on page init
loadEarnings();

// Refresh every 5 minutes
setInterval(loadEarnings, 5 * 60 * 1000);
</script>
```

---

## Referral Partner Dashboard Widget

```html
<div class="earnings-widget referral">
  <h3>💼 Deal Commission Tracker</h3>

  <div class="earnings-grid">
    <!-- Pending (Invoiced, awaiting payment) -->
    <div class="metric-card pending">
      <div class="metric-label">Invoiced Deals</div>
      <div class="metric-value" id="pending-amount-ref">$0.00</div>
      <div class="metric-detail">
        <span id="pending-count-ref">0</span> deals awaiting payment
      </div>
    </div>

    <!-- Approved-->
    <div class="metric-card approved">
      <div class="metric-label">Approved for Payment</div>
      <div class="metric-value" id="approved-amount-ref">$0.00</div>
    </div>

    <!-- Next Payout -->
    <div class="metric-card projected">
      <div class="metric-label">💰 Next Payout</div>
      <div class="metric-value" id="projected-amount-ref">$0.00</div>
      <div class="metric-detail">
        On <span id="payout-date-ref">—</span> (Bi-weekly)
      </div>
    </div>
  </div>

  <!-- Bi-weekly Schedule -->
  <div class="schedule-card">
    <h4>📅 Payout Schedule</h4>
    <div class="schedule-info">
      <strong>Bi-weekly payouts</strong> on the 1st and 15th of each month
    </div>
    <div class="threshold-info">
      <strong>Minimum:</strong> $500 per payout
    </div>
  </div>

  <!-- Active Deals -->
  <div class="active-deals">
    <h4>Active Deals</h4>
    <table class="deals-table">
      <thead>
        <tr>
          <th>Deal</th>
          <th>Value</th>
          <th>Commission</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody id="dealsList">
        <!-- Populated by JS -->
      </tbody>
    </table>
  </div>
</div>

<script>
// Similar structure to affiliate, but for referral partners
// Fetch from /api/partners/referral_partner/{id}/earnings

const PARTNER_TYPE = 'referral_partner';

async function loadReferralEarnings() {
  const response = await fetch(
    `/api/partners/${PARTNER_TYPE}/${PARTNER_ID}/earnings`,
    { headers: { 'Authorization': `Bearer ${localStorage.getItem('partner_token')}` } }
  );
  const earnings = await response.json();

  document.getElementById('pending-amount-ref').textContent = 
    `$${earnings.pending_dollars.toFixed(2)}`;
  document.getElementById('pending-count-ref').textContent = earnings.pending_count;
  document.getElementById('approved-amount-ref').textContent = 
    `$${earnings.approved_dollars.toFixed(2)}`;
  document.getElementById('projected-amount-ref').textContent = 
    `$${earnings.projected_dollars.toFixed(2)}`;

  if (earnings.next_payout_date) {
    document.getElementById('payout-date-ref').textContent = 
      new Date(earnings.next_payout_date).toLocaleDateString();
  }

  loadActiveDealss();
}

async function loadActiveDealss() {
  // Load referral's active deals
  const response = await fetch(
    `/api/partners/referral_partner/${PARTNER_ID}/deals?status=invoiced`,
    { headers: { 'Authorization': `Bearer ${localStorage.getItem('partner_token')}` } }
  );
  const deals = await response.json();

  const tbody = document.getElementById('dealsList');
  tbody.innerHTML = deals.map(deal => `
    <tr>
      <td>${deal.title}</td>
      <td>$${(deal.actual_value_cents/100).toFixed(2)}</td>
      <td>$${(deal.commission_cents/100).toFixed(2)}</td>
      <td><span class="status-badge">${deal.status}</span></td>
    </tr>
  `).join('');
}

loadReferralEarnings();
</script>
```

---

## Executive Dashboard Widget

```html
<div class="earnings-widget executive">
  <h3>🎯 Territory Commission Tracker</h3>

  <div class="earnings-grid">
    <!-- Pending Deals -->
    <div class="metric-card pending">
      <div class="metric-label">Pending Deals</div>
      <div class="metric-value" id="pending-amount-exec">$0.00</div>
    </div>

    <!-- Weekly Payout -->
    <div class="metric-card projected">
      <div class="metric-label">💰 Weekly Payout</div>
      <div class="metric-value" id="weekly-amount-exec">$0.00</div>
      <div class="metric-detail">
        Next Monday
      </div>
    </div>
  </div>

  <!-- Territory Info -->
  <div class="territory-card">
    <h4>📍 Your Territory</h4>
    <div id="territory-info">
      <!-- Populated by JS -->
    </div>
  </div>

  <!-- Deals This Month -->
  <div class="monthly-deals">
    <h4>This Month's Deals</h4>
    <div class="deals-summary">
      <div class="deal-stat">
        <div class="deal-stat-value" id="deals-count">0</div>
        <div class="deal-stat-label">Deals Closed</div>
      </div>
      <div class="deal-stat">
        <div class="deal-stat-value" id="total-value">$0</div>
        <div class="deal-stat-label">Total Value</div>
      </div>
      <div class="deal-stat">
        <div class="deal-stat-value" id="total-commission">$0</div>
        <div class="deal-stat-label">Your Commission</div>
      </div>
    </div>
  </div>
</div>

<script>
const PARTNER_TYPE = 'executive';

async function loadExecutiveEarnings() {
  const response = await fetch(
    `/api/partners/${PARTNER_TYPE}/${PARTNER_ID}/earnings`,
    { headers: { 'Authorization': `Bearer ${localStorage.getItem('partner_token')}` } }
  );
  const earnings = await response.json();

  document.getElementById('pending-amount-exec').textContent = 
    `$${earnings.pending_dollars.toFixed(2)}`;
  document.getElementById('weekly-amount-exec').textContent = 
    `$${earnings.projected_dollars.toFixed(2)}`;

  // Load territory  & monthly deals
  loadTerritoryInfo();
  loadMonthlySummary();
}

loadExecutiveEarnings();
</script>
```

---

## Component Integration Points

### For Affiliate Dashboard
Add to: `templates/affiliate_dashboard.html`
```html
<!-- Existing sections... -->
<section class="tab-pane" id="earnings">
  {% include 'components/affiliate_earnings_widget.html' %}
</section>
```

### For Referral Partner Dashboard
Add to: `templates/referral_dashboard.html`
```html
<section class="tab-pane" id="commissions">
  {% include 'components/referral_earnings_widget.html' %}
</section>
```

### For Executive Dashboard
Add to: `templates/executive_dashboard.html`
```html
<section class="tab-pane" id="territory">
  {% include 'components/executive_earnings_widget.html' %}
</section>
```

---

## API Endpoints Required for Partner Dashboard

These endpoints should be added to support partner earnings display:

```
GET /api/partners/affiliate/{id}/earnings
GET /api/partners/affiliate/{id}/recent-earnings?days=30
GET /api/partners/affiliate/{id}/paid-payouts?months=6

GET /api/partners/referral_partner/{id}/earnings
GET /api/partners/referral_partner/{id}/deals?status=invoiced
GET /api/partners/referral_partner/{id}/paid-payouts

GET /api/partners/executive/{id}/earnings
GET /api/partners/executive/{id}/territory-info
GET /api/partners/executive/{id}/monthly-summary
```

These map to the existing partner earnings endpoint plus new specialized queries.
