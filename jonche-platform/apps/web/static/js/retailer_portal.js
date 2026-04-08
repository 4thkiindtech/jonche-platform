/* ── Retailer Portal JS ─────────────────────────────────────────────────────- */

async function postJson(path, body) {
  return apiFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function allocRow(a) {
  const remaining = a.remaining_units ?? (a.allocated_units - a.purchased_units);
  const shipped = a.status === 'shipped';
  const invLink = a.invoice_number
    ? `<a class="link mono" href="/api/retailers/allocations/${a.id}/invoice" target="_blank">${a.invoice_number}</a>`
    : `<a class="link mono" href="/api/retailers/allocations/${a.id}/invoice" target="_blank">Generate</a>`;

  return `
    <div class="table-row" style="grid-template-columns: 1fr 0.7fr 0.7fr 0.6fr 1fr 1fr;">
      <div>
        <div class="row-title">${a.drop_name || `Drop #${a.drop_id}`}</div>
        <div class="row-sub mono">Allocation #${a.id} • ${a.purchase_order_number || 'No PO'}</div>
      </div>
      <div class="mono">${a.allocated_units}</div>
      <div class="mono">${a.purchased_units}</div>
      <div class="mono">${remaining}</div>
      <div class="mono">${a.status}${a.tracking_number ? ` • ${a.tracking_number}` : ''}</div>
      <div style="display:flex;gap:10px;align-items:center;justify-content:flex-end;flex-wrap:wrap">
        <input class="input po-input" type="number" min="1" max="${remaining}" value="${Math.min(remaining, 1)}" data-po-qty="${a.id}" ${remaining <= 0 || shipped ? 'disabled' : ''}>
        <button class="btn-primary po-btn" data-po-btn="${a.id}" ${remaining <= 0 || shipped ? 'disabled' : ''}>SUBMIT PO</button>
        ${invLink}
      </div>
    </div>
  `;
}

async function loadAllocations() {
  const root = document.getElementById('retailer-allocations');
  const msg = document.getElementById('retailer-msg');
  if (!root || !msg) return;

  msg.textContent = 'Loading…';
  const allocs = await apiFetch('/retailers/me/allocations');
  if (!allocs) {
    msg.textContent = 'Unable to load allocations. Please re-login.';
    return;
  }

  root.innerHTML = `
    <div class="table-head" style="grid-template-columns: 1fr 0.7fr 0.7fr 0.6fr 1fr 1fr;">
      <div>Drop</div><div>Allocated</div><div>Purchased</div><div>Remaining</div><div>Status</div><div>Actions</div>
    </div>
    ${allocs.map(allocRow).join('')}
  `;
  msg.textContent = '';

  root.querySelectorAll('[data-po-btn]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-po-btn');
      const qtyEl = root.querySelector(`[data-po-qty="${id}"]`);
      const qty = Number(qtyEl ? qtyEl.value : 0);
      msg.textContent = `Submitting PO for allocation #${id}…`;
      const res = await postJson(`/retailers/allocations/${id}/purchase-order`, { quantity: qty });
      if (!res) {
        msg.textContent = 'Purchase order failed.';
        return;
      }
      msg.textContent = `PO received. Invoice: ${res.allocation.invoice_number || '—'}`;
      await loadAllocations();
    });
  });
}

document.addEventListener('DOMContentLoaded', loadAllocations);
