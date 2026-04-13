/* ── Jonche Platform — Main JS ───────────────────────────────────────────────── */

function resolveApiBase() {
  const hostname = window.location.hostname;
  const isLocal =
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname === '::1';

  if (!isLocal) return '/api';

  // Preserve hostname so cookies (domain) match when using 127.0.0.1 vs localhost.
  const hostForUrl = hostname.includes(':') ? `[${hostname}]` : hostname;
  return `http://${hostForUrl}:5001/api`;
}

const API_BASE = resolveApiBase();

/* ── Fetch helper ────────────────────────────────────────────────────────────── */
async function apiFetch(path, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      credentials: 'include',
      ...options,
      headers: {
        ...(options.headers || {}),
      },
    });
    if (!res.ok) throw new Error(`API error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('API fetch failed:', err);
    return null;
  }
}

/* ── Nav active state ────────────────────────────────────────────────────────── */
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    item.classList.add('active');
  });
});

/* ── Countdown timer ─────────────────────────────────────────────────────────── */
function startCountdown(targetId, targetDate) {
  const els = {
    days:  document.getElementById(`${targetId}-days`),
    hours: document.getElementById(`${targetId}-hours`),
    mins:  document.getElementById(`${targetId}-mins`),
    secs:  document.getElementById(`${targetId}-secs`),
  };
  if (!els.days) return;

  function pad(n) { return n < 10 ? '0' + n : String(n); }

  function tick() {
    const diff = new Date(targetDate) - new Date();
    if (diff <= 0) {
      Object.values(els).forEach(el => { if (el) el.textContent = '00'; });
      return;
    }
    if (els.days)  els.days.textContent  = pad(Math.floor(diff / 86400000));
    if (els.hours) els.hours.textContent = pad(Math.floor((diff % 86400000) / 3600000));
    if (els.mins)  els.mins.textContent  = pad(Math.floor((diff % 3600000) / 60000));
    if (els.secs)  els.secs.textContent  = pad(Math.floor((diff % 60000) / 1000));
  }

  tick();
  setInterval(tick, 1000);
}

/* ── Animate hype bars ───────────────────────────────────────────────────────── */
function animateHypeBars() {
  document.querySelectorAll('.hype-fill').forEach(bar => {
    const target = bar.dataset.target || bar.style.width;
    bar.style.width = '0%';
    setTimeout(() => { bar.style.width = target; }, 400);
  });
}

document.addEventListener('DOMContentLoaded', animateHypeBars);
