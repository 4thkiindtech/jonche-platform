/* ── Admin Tools JS ─────────────────────────────────────────────────────────- */

async function postJson(path, body) {
  return apiFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

document.addEventListener('DOMContentLoaded', () => {
  const sendBtn = document.getElementById('send-notifs');
  const notifResult = document.getElementById('notif-result');

  if (sendBtn) {
    sendBtn.addEventListener('click', async () => {
      notifResult.textContent = 'Sending…';
      const r = await postJson('/notifications/send', { limit: 25 });
      notifResult.textContent = r ? JSON.stringify(r) : 'Failed to send.';
    });
  }

  const dropForm = document.getElementById('drop-override');
  const dropResult = document.getElementById('drop-override-result');
  if (dropForm) {
    dropForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(dropForm);
      const slug = fd.get('slug');
      const status = fd.get('status');
      dropResult.textContent = 'Applying…';

      const r = await apiFetch(`/drops/${slug}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      dropResult.textContent = r ? `Updated: ${r.slug} → ${r.status}` : 'Failed.';
    });
  }

  const allocForm = document.getElementById('alloc-set');
  const allocResult = document.getElementById('alloc-set-result');
  if (allocForm) {
    allocForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(allocForm);
      const body = {
        retailer_id: Number(fd.get('retailer_id')),
        drop_id: Number(fd.get('drop_id')),
        allocated_units: Number(fd.get('allocated_units')),
      };
      allocResult.textContent = 'Saving…';
      const r = await postJson('/admin/allocations/set', body);
      allocResult.textContent = r ? `OK: allocation #${r.allocation.id} (${r.allocation.allocated_units} units)` : 'Failed.';
    });
  }
});

