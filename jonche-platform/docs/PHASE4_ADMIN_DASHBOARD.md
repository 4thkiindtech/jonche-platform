# Phase 4 Lite - Admin Dashboard Implementation

## Overview

This guide shows how to build the admin UI for managing payouts, approving batches, and recording payments.

---

## Admin Dashboard - Key Sections

### 1. Payout Summary (Quick Stats)

```html
<div class="payout-summary">
  <div class="stat-card">
    <h3>Pending Payouts</h3>
    <div class="amount" id="pending-amount">$0.00</div>
    <div class="count">to <span id="pending-count">0</span> partners</div>
    <button onclick="createPendingBatch()">Create Batch</button>
  </div>

  <div class="stat-card">
    <h3>Next Scheduled</h3>
    <div class="date" id="next-payout-date">—</div>
    <div class="schedule" id="next-payout-type">—</div>
  </div>

  <div class="stat-card">
    <h3>Approved (Unpaid)</h3>
    <div class="amount" id="approved-amount">$0.00</div>
    <div class="action">
      <button onclick="loadApprovedPayouts()">Process Payments</button>
    </div>
  </div>

  <div class="stat-card">
    <h3>Monthly Volume</h3>
    <div class="amount" id="monthly-volume">$0.00</div>
    <div class="subtitle">Average monthly payout</div>
  </div>
</div>

<script>
// Load summary on page init
async function loadSummary() {
  const response = await fetch('/api/admin/payouts/batches', {
    headers: { 'X-Admin-ID': currentAdminId }
  });
  const data = await response.json();
  
  // Calculate totals
  const pending = data.batches.filter(b => b.status === 'pending');
  const approved = data.batches.filter(b => b.status === 'approved');
  
  const pendingTotal = pending.reduce((sum, b) => sum + b.total_amount_cents, 0);
  const approvedTotal = approved.reduce((sum, b) => sum + b.total_amount_cents, 0);
  
  document.getElementById('pending-amount').textContent = `$${(pendingTotal/100).toFixed(2)}`;
  document.getElementById('pending-count').textContent = pending.length;
  document.getElementById('approved-amount').textContent = `$${(approvedTotal/100).toFixed(2)}`;
}

loadSummary();
</script>
```

---

### 2. Payout Batch Manager

```html
<div class="batch-manager">
  <h2>Payout Batches</h2>

  <div class="filters">
    <select id="statusFilter" onchange="filterBatches()">
      <option value="">All Statuses</option>
      <option value="pending">Pending (Awaiting Approval)</option>
      <option value="approved">Approved (Awaiting Payment)</option>
      <option value="paid">Paid</option>
      <option value="rejected">Rejected</option>
    </select>

    <select id="typeFilter" onchange="filterBatches()">
      <option value="">All Partner Types</option>
      <option value="affiliate">Affiliates</option>
      <option value="referral_partner">Referral Partners</option>
      <option value="executive">Executives</option>
    </select>
  </div>

  <table id="batchTable" class="data-table">
    <thead>
      <tr>
        <th>Batch #</th>
        <th>Type</th>
        <th>Created</th>
        <th>Partners</th>
        <th>Amount</th>
        <th>Status</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody id="batchBody">
      <!-- Loaded by JS -->
    </tbody>
  </table>
</div>

<script>
async function filterBatches() {
  const status = document.getElementById('statusFilter').value;
  const type = document.getElementById('typeFilter').value;

  let url = '/api/admin/payouts/batches';
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (type) params.append('partner_type', type);
  if (params.toString()) url += '?' + params.toString();

  const response = await fetch(url, {
    headers: { 'X-Admin-ID': currentAdminId }
  });
  const data = await response.json();

  const tbody = document.getElementById('batchBody');
  tbody.innerHTML = data.batches.map(batch => `
    <tr class="status-${batch.status}">
      <td><code>${batch.batch_number}</code></td>
      <td>${batch.partner_type.replace('_', ' ')}</td>
      <td>${new Date(batch.created_at).toLocaleDateString()}</td>
      <td>${batch.payout_count}</td>
      <td>$${(batch.total_amount_cents/100).toFixed(2)}</td>
      <td><span class="badge badge-${batch.status}">${batch.status}</span></td>
      <td>
        ${batch.status === 'pending' ? `
          <button onclick="approveBatch(${batch.id})" class="btn-approve">Approve</button>
          <button onclick="rejectBatch(${batch.id})" class="btn-reject">Reject</button>
        ` : ''}
        ${batch.status === 'approved' ? `
          <button onclick="openPaymentDialog(${batch.id})" class="btn-pay">Record Payment</button>
        ` : ''}
        <button onclick="viewBatchDetail(${batch.id})">Details</button>
      </td>
    </tr>
  `).join('');
}

async function approveBatch(batchId) {
  if (!confirm('Approve this batch? This moves payouts to payment stage.')) return;

  const response = await fetch(`/api/admin/payouts/batch/${batchId}/approve`, {
    method: 'POST',
    headers: {
      'X-Admin-ID': currentAdminId,
      'Content-Type': 'application/json'
    }
  });

  if (response.ok) {
    showNotification('Batch approved!', 'success');
    filterBatches();
  } else {
    showNotification('Failed to approve batch', 'error');
  }
}

filterBatches();
</script>
```

---

### 3. Payment Recorder Dialog

```html
<div id="paymentDialog" class="modal hidden">
  <div class="modal-content">
    <h3>Record Payment</h3>

    <div class="form-group">
      <label>Batch</label>
      <input id="paymentBatchId" type="hidden" />
      <div id="batchInfo" style="background: #f5f5f5; padding: 10px; border-radius: 4px;">
        <!-- Populated by JS -->
      </div>
    </div>

    <div class="form-group">
      <label>Payment Method *</label>
      <select id="paymentMethod">
        <option value="">-- Select --</option>
        <option value="ach">ACH Transfer</option>
        <option value="zelle">Zelle</option>
        <option value="wire">Wire Transfer</option>
        <option value="check">Check</option>
        <option value="stripe">Stripe Connect</option>
      </select>
    </div>

    <div class="form-group">
      <label id="refLabel">ACH Reference # *</label>
      <input id="paymentReference" 
             type="text" 
             placeholder="e.g., ACH-20260413-12345"
             required />
      <small>Check your bank's payment confirmation for this number</small>
    </div>

    <div class="form-actions">
      <button onclick="cancelPaymentDialog()" class="btn-secondary">Cancel</button>
      <button onclick="recordPayment()" class="btn-primary">Record Payment</button>
    </div>
  </div>
</div>

<script>
async function openPaymentDialog(batchId) {
  // Load batch info
  const response = await fetch(`/api/admin/payouts/batches`, {
    headers: { 'X-Admin-ID': currentAdminId }
  });
  const data = await response.json();
  const batch = data.batches.find(b => b.id === batchId);

  if (!batch) return;

  // Show info
  document.getElementById('batchInfo').innerHTML = `
    <div><strong>Batch:</strong> ${batch.batch_number}</div>
    <div><strong>Partners:</strong> ${batch.payout_count}</div>
    <div><strong>Amount:</strong> $${(batch.total_amount_cents/100).toFixed(2)}</div>
    <div><strong>Type:</strong> ${batch.partner_type}</div>
  `;

  document.getElementById('paymentBatchId').value = batchId;
  document.getElementById('paymentDialog').classList.remove('hidden');
}

async function recordPayment() {
  const batchId = document.getElementById('paymentBatchId').value;
  const method = document.getElementById('paymentMethod').value;
  const reference = document.getElementById('paymentReference').value;

  if (!method || !reference) {
    showNotification('Payment method and reference required', 'error');
    return;
  }

  // Get all payouts in batch and record payment for each
  const response = await fetch(`/api/admin/payouts/pending?batch_id=${batchId}`, {
    headers: { 'X-Admin-ID': currentAdminId }
  });
  const data = await response.json();

  let paid = 0;
  for (const payout of data.payouts) {
    const payResponse = await fetch(
      `/api/admin/payouts/${payout.id}/payment`,
      {
        method: 'POST',
        headers: {
          'X-Admin-ID': currentAdminId,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          payment_method: method,
          payment_reference: reference
        })
      }
    );

    if (payResponse.ok) paid++;
  }

  showNotification(`${paid} payments recorded!`, 'success');
  cancelPaymentDialog();
  filterBatches();
}

function cancelPaymentDialog() {
  document.getElementById('paymentDialog').classList.add('hidden');
}

// Update label based on payment method
document.getElementById('paymentMethod').addEventListener('change', (e) => {
  const labels = {
    'ach': 'ACH Reference #',
    'zelle': 'Zelle Confirmation #',
    'wire': 'Wire Reference #',
    'check': 'Check Number',
    'stripe': 'Stripe Transaction ID'
  };
  document.getElementById('refLabel').textContent = (labels[e.target.value] || 'Reference') + ' *';
});
</script>
```

---

### 4. Partner Earnings Viewer

```html
<div class="partner-earnings">
  <h2>Partner Earnings</h2>

  <div class="search-box">
    <input id="search" type="text" placeholder="Search by email or name..." />
    <select id="typeFilter">
      <option value="">All Types</option>
      <option value="affiliate">Affiliates</option>
      <option value="referral_partner">Referral Partners</option>
      <option value="executive">Executives</option>
    </select>
  </div>

  <table class="data-table">
    <thead>
      <tr>
        <th>Partner</th>
        <th>Type</th>
        <th>Pending</th>
        <th>Approved</th>
        <th>Projected</th>
        <th>Minimum</th>
        <th>Status</th>
        <th>Next Payout</th>
      </tr>
    </thead>
    <tbody id="earningsBody">
      <!-- Loaded by JS -->
    </tbody>
  </table>
</div>

<script>
async function loadPartnerEarnings() {
  // Load all affiliates
  const affiliates = await fetch('/api/partners/affiliates', {
    headers: { 'X-Admin-ID': currentAdminId }
  }).then(r => r.json());

  // Load all referral partners
  const referrals = await fetch('/api/partners/referrals', {
    headers: { 'X-Admin-ID': currentAdminId }
  }).then(r => r.json());

  // Load all executives
  const execs = await fetch('/api/partners/executives', {
    headers: { 'X-Admin-ID': currentAdminId }
  }).then(r => r.json());

  const tbody = document.getElementById('earningsBody');
  const rows = [];

  // Process affiliates
  for (const aff of (affiliates.accounts || [])) {
    const earnings = await fetch(
      `/api/partners/affiliate/${aff.id}/earnings`,
      { headers: { 'X-Admin-ID': currentAdminId } }
    ).then(r => r.json());

    rows.push({
      name: aff.display_name,
      email: aff.email,
      type: 'affiliate',
      ...earnings
    });
  }

  // Process referral partners
  for (const ref of (referrals.accounts || [])) {
    const earnings = await fetch(
      `/api/partners/referral_partner/${ref.id}/earnings`,
      { headers: { 'X-Admin-ID': currentAdminId } }
    ).then(r => r.json());

    rows.push({
      name: ref.contact_name,
      email: ref.email,
      type: 'referral_partner',
      ...earnings
    });
  }

  // Process executives
  for (const exec of (execs.accounts || [])) {
    const earnings = await fetch(
      `/api/partners/executive/${exec.id}/earnings`,
      { headers: { 'X-Admin-ID': currentAdminId } }
    ).then(r => r.json());

    rows.push({
      name: exec.executive_name,
      email: exec.email,
      type: 'executive',
      ...earnings
    });
  }

  tbody.innerHTML = rows.map(r => `
    <tr class="earnings-row ${r.meets_minimum ? 'ready-for-payout' : ''}">
      <td>
        <div class="partner-name">${r.name}</div>
        <div class="partner-email">${r.email}</div>
      </td>
      <td>${r.type.replace('_', ' ')}</td>
      <td class="amount">$${(r.pending_dollars).toFixed(2)}</td>
      <td class="amount">$${(r.approved_dollars).toFixed(2)}</td>
      <td class="amount projected">$${(r.projected_dollars).toFixed(2)}</td>
      <td>$${(r.minimum_threshold_dollars).toFixed(2)}</td>
      <td>
        ${r.meets_minimum 
          ? '<span class="badge badge-success">Ready</span>' 
          : '<span class="badge badge-info">Below Min</span>'}
      </td>
      <td>${r.next_payout_date ? new Date(r.next_payout_date).toLocaleDateString() : '—'}</td>
    </tr>
  `).join('');
}

loadPartnerEarnings();
</script>
```

---

### 5. Audit Log Viewer

```html
<div class="audit-log">
  <h2>Payout Audit Log</h2>

  <div class="filters">
    <input type="date" id="dateFrom" />
    <input type="date" id="dateTo" />
    <select id="actionFilter">
      <option value="">All Actions</option>
      <option value="batch_created">Batch Created</option>
      <option value="batch_approved">Batch Approved</option>
      <option value="payment_recorded">Payment Recorded</option>
    </select>
    <button onclick="filterLogs()">Filter</button>
  </div>

  <table class="log-table">
    <thead>
      <tr>
        <th>Date & Time</th>
        <th>Action</th>
        <th>Batch/Payout ID</th>
        <th>Actor</th>
        <th>Details</th>
      </tr>
    </thead>
    <tbody id="logBody">
      <!-- Loaded by JS -->
    </tbody>
  </table>
</div>

<script>
async function filterLogs() {
  const dateFrom = document.getElementById('dateFrom').value;
  const dateTo = document.getElementById('dateTo').value;
  const action = document.getElementById('actionFilter').value;

  let url = '/api/admin/payout-logs';
  const params = new URLSearchParams();
  if (dateFrom) params.append('date_from', dateFrom);
  if (dateTo) params.append('date_to', dateTo);
  if (action) params.append('action', action);

  if (params.toString()) url += '?' + params.toString();

  const response = await fetch(url, {
    headers: { 'X-Admin-ID': currentAdminId }
  });
  const data = await response.json();

  const tbody = document.getElementById('logBody');
  tbody.innerHTML = (data.logs || []).map(log => `
    <tr>
      <td>${new Date(log.created_at).toLocaleString()}</td>
      <td><code>${log.action}</code></td>
      <td>
        ${log.batch_id ? `Batch #${log.batch_id}` : ''}
        ${log.payout_id ? `Payout #${log.payout_id}` : ''}
      </td>
      <td>${log.actor_type === 'admin' ? '👤 Admin #' + log.actor_id : '⚙️ System'}</td>
      <td><small>${JSON.stringify(log.details || {})}</small></td>
    </tr>
  `).join('');
}

filterLogs();
</script>
```

---

## CSS Styling (Base)

```css
.payout-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  border-left: 4px solid #2563eb;
}

.stat-card h3 {
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
  color: #666;
  text-transform: uppercase;
}

.stat-card .amount {
  font-size: 1.875rem;
  font-weight: bold;
  color: #1f2937;
  margin: 0.5rem 0;
}

.stat-card .count {
  font-size: 0.875rem;
  color: #999;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.data-table thead {
  background: #f3f4f6;
  font-weight: 600;
  font-size: 0.875rem;
}

.data-table th,
.data-table td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.data-table tbody tr:hover {
  background: #f9fafb;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-pending {
  background: #fef3c7;
  color: #92400e;
}

.badge-approved {
  background: #dbeafe;
  color: #0c4a6e;
}

.badge-paid {
  background: #dcfce7;
  color: #166534;
}

.badge-success {
  background: #dcfce7;
  color: #166534;
}

.badge-info {
  background: #e0e7ff;
  color: #3730a3;
}

.btn-approve, .btn-pay {
  background: #10b981;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.btn-reject {
  background: #ef4444;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.modal {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal.hidden {
  display: none;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
}

.earnings-row.ready-for-payout {
  background: #f0fdf4;
}

.amount.projected {
  font-weight: bold;
  color: #2563eb;
}
```

---

## Integration Checklist

- [ ] Add Payout tab to admin sidebar
- [ ] Create `/admin/payouts` route in web app
- [ ] Embed sections 1-5 above into page
- [ ] Connect to API endpoints
- [ ] Add email notifications on payout
- [ ] Create monthly scheduler task
- [ ] Test approve → record payment flow
- [ ] Add partner earnings widget to partner dashboard

