# JONCHE Platform — Monorepo

> Unified luxury sneaker brand command center (admin dashboard + store + retailer portal).

## Status (as of Apr 2026)

- ✅ Two Flask apps: `apps/web` (HTML UI) + `apps/api` (REST API)
- ✅ Admin dashboard: drops, retailers, VIP, analytics, certificates, store admin
- ✅ Public pages: store (`/store`), partner programs (`/partners`), preorder capture (`/preorder`), certificate verify (`/verify/<token>`)
- ✅ Retailer portal: retailer login + allocations + store orders
- ✅ PayPal payments + webhooks (source of truth):
  - Drop checkout Orders (`/api/paypal/drop-order`, `/api/paypal/drop-capture`, `/api/paypal/webhook`)
  - Preorder deposits (`/api/paypal/preorder-order`, `/api/paypal/preorder-capture`, `/api/paypal/webhook`)
  - Event tickets (`/api/paypal/event-order`, `/api/paypal/event-capture`, `/api/paypal/webhook`)
  - Retailer store-order payments (`/api/paypal/store-order`, `/api/paypal/store-capture`, `/api/paypal/webhook`)
  - Stripe routes can be hard-disabled with `STRIPE_ENABLED=false`

```
jonche-platform/
├── apps/
│   ├── web/          # Flask web UI (admin + public + retailer)
│   └── api/          # Flask REST API (DB-backed)
├── packages/
│   ├── ui/           # Shared HTML/CSS components
│   ├── config/       # Shared config (env, constants)
│   └── types/        # Shared Python type definitions
├── .github/
│   └── workflows/    # CI/CD pipelines
├── Makefile          # Dev shortcuts
└── pyproject.toml    # Root project config
```

## Quickstart

```bash
# Create your env file
cp .env.example .env

# Install all dependencies
make install

# Run everything locally
make dev

# Run tests
make test

# Lint/format (optional)
make lint
make format
```

### Local URLs

- Web UI: `http://localhost:5000` (Linux/Mac) or `http://localhost:9000` (Windows default)
- API: `http://localhost:5001/api/health`

### Key pages

- Admin: `/login` → `/` (dashboard), `/drops`, `/vip`, `/analytics`, `/certificates`, `/admin`, `/admin/store`
- Retailer: `/retailer/login` → `/retailer`
- Public: `/store`, `/partners`, `/preorder`, `/verify/<token>`

## Apps (dev)

| App | Port | Description |
|-----|------|-------------|
| `web` | 9000 | Web UI (admin + public + retailer) |
| `api` | 5001 | REST API (JSON) |

## Environment variables

Start with `.env.example`, then add what you need:

- Required: `SECRET_KEY`, `API_KEY`, `DATABASE_URL`
- Production required:
  - Postgres: set `DATABASE_URL` (API refuses to start in production with SQLite)
  - Durable storage: set `STORAGE_BACKEND=r2` and `R2_*` vars for Cloudflare R2
- Apliiq (optional, fulfillment): `APLIIQ_APP_KEY`, `APLIIQ_SHARED_SECRET`
- Payments:
  - Provider flags: `PAYMENTS_PROVIDER_DEFAULT`, `PAYPAL_ENABLED`, `STRIPE_ENABLED`
  - PayPal: `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`
  - Stripe (optional): `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- Alviere webhooks (optional): `ALVIERE_WEBHOOK_SECRET`
- Sentry (optional, recommended): `SENTRY_DSN`, `SENTRY_ENV`, `SENTRY_TRACES_SAMPLE_RATE`
- Other: `API_BASE_URL` (web → api override), `WEB_ORIGIN` (CORS), `WHOLESALE_MULTIPLIER`

## Scheduler (production)

Run the drop scheduler out-of-band (cron/worker), not inside API requests:

`apps/api/scripts/run_drop_scheduler.py`

The scheduler writes:
- `job_runs` (job success/failure visibility)
- `audit_logs` (system action trail)

## Deploy

- PythonAnywhere guide: `DEPLOY.md`

## Phases

- [x] Phase 1 — Drops + checkout lock + raffle
- [x] Phase 1.5 — Preorder intent capture
- [x] Phase 2 — Retailer portal + allocations + store orders
- [x] Phase 3 — VIP membership (accounts + tiers)
- [x] Phase 4 — Commission Payout Processing ✅ (Deployed April 13, 2026)
  - Manual payout approval system (Phase 4 Lite)
  - Implements: Commission schedules, payout batches, payment processing (Stripe/ACH), compliance
  - Partners: Affiliates (monthly), Referral (bi-weekly), Retail (on-demand), Executives (weekly)
  - See docs: `PHASE4_LITE_GUIDE.md`, `PHASE4_LITE_SUMMARY.md`, `PHASE4_DEPLOYMENT.md`, `PHASE4_ADMIN_DASHBOARD.md`
- [x] Phase 5 — Analytics + certificates + Stripe payments (incl. store orders)

## References
- Store setup guide: `docs/STORE_SETUP.md`
- Store-order payments (Phase 5): `PHASE5_COMPLETE.md`, `docs/PHASE5_API.md`
- RLS planning (Supabase): `docs/RLS_STRATEGY.md`
