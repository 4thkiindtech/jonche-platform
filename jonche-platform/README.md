# JONCHE Platform — Monorepo

> Unified luxury sneaker brand command center (admin dashboard + store + retailer portal).

## Status (as of Apr 2026)

- ✅ Two Flask apps: `apps/web` (HTML UI) + `apps/api` (REST API)
- ✅ Admin dashboard: drops, retailers, VIP, analytics, certificates, store admin
- ✅ Public pages: store (`/store`), partner programs (`/partners`), preorder capture (`/preorder`), certificate verify (`/verify/<token>`)
- ✅ Retailer portal: retailer login + allocations + store orders
- ✅ Stripe payments + webhooks:
  - Drop checkout PaymentIntents (`/api/payments/drop-intent`)
  - Preorder deposits (`/api/payments/preorder-intent`)
  - Retailer store-order payments (`/api/store-orders/<id>/payment-intent`) — see `PHASE5_COMPLETE.md`

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

- Web UI: `http://localhost:5000`
- API: `http://localhost:5001/api/health`

### Key pages

- Admin: `/login` → `/` (dashboard), `/drops`, `/vip`, `/analytics`, `/certificates`, `/admin`, `/admin/store`
- Retailer: `/retailer/login` → `/retailer`
- Public: `/store`, `/partners`, `/preorder`, `/verify/<token>`

## Apps (dev)

| App | Port | Description |
|-----|------|-------------|
| `web` | 5000 | Web UI (admin + public + retailer) |
| `api` | 5001 | REST API (JSON) |

## Environment variables

Start with `.env.example`, then add what you need:

- Required: `SECRET_KEY`, `API_KEY`, `DATABASE_URL`
- Apliiq (optional, fulfillment): `APLIIQ_APP_KEY`, `APLIIQ_SHARED_SECRET`
- Stripe (optional, payments): `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- Other: `API_BASE_URL` (web → api override), `WEB_ORIGIN` (CORS), `WHOLESALE_MULTIPLIER`

## Deploy

- PythonAnywhere guide: `DEPLOY.md`

## Phases

- [x] Phase 1 — Drops + checkout lock + raffle
- [x] Phase 1.5 — Preorder intent capture
- [x] Phase 2 — Retailer portal + allocations + store orders
- [x] Phase 3 — VIP membership (accounts + tiers)
- [x] Phase 5 — Analytics + certificates + Stripe payments (incl. store orders)
- 🔄 **Phase 4 — Commission Payout Processing** (Design Complete ✅)
  - See docs: `PHASE4_PAYOUT_PROCESSING.md`, `PHASE4_QUICK_REFERENCE.md`, `PHASE4_IMPLEMENTATION_CODE.md`
  - Implements: Commission schedules, payout batches, payment processing (Stripe/ACH), compliance
  - Partners: Affiliates, Referral, Retail, Executives

## References
- Store setup guide: `docs/STORE_SETUP.md`
- Store-order payments (Phase 5): `PHASE5_COMPLETE.md`, `docs/PHASE5_API.md`
