/* ── Certificates Page JS ──────────────────────────────────────────────────── */

async function loadCertificates() {
  const root = document.getElementById('certs-root');
  if (!root) return;

  const certs = await apiFetch('/certificates/');
  if (!certs) {
    root.innerHTML = `<div class="muted">Unable to load certificates.</div>`;
    return;
  }

  const rows = certs.slice(0, 200);
  root.innerHTML = `
    <div class="table-head" style="grid-template-columns: 1fr 1.6fr 0.5fr 1fr 1.4fr;">
      <div>Certificate</div><div>Drop</div><div>Size</div><div>Issued</div><div>Verify</div>
    </div>
    ${rows.map(c => `
      <div class="table-row" style="grid-template-columns: 1fr 1.6fr 0.5fr 1fr 1.4fr;">
        <div class="mono">${c.cert_number}</div>
        <div>${c.drop_name || '—'}</div>
        <div class="mono">${c.size}</div>
        <div class="mono">${c.issued_at ? new Date(c.issued_at).toLocaleString() : '—'}</div>
        <div class="mono"><a class="link" href="/verify/${c.verify_token}" target="_blank">/verify/${c.verify_token}</a></div>
      </div>
    `).join('')}
  `;
}

document.addEventListener('DOMContentLoaded', loadCertificates);
