Here's how the Jonche Platform monorepo fits together:

---

**The Big Picture**

You have one codebase split into two running apps and three shared packages. Everything lives under `jonche-platform/` so you version, deploy, and manage it as a single unit instead of juggling separate repos.

---

**`apps/web` — The Dashboard**

This is the Flask app your browser talks to. It serves the HTML dashboard you see — the command center with drops, stats, hype meters, countdowns. It has no business logic of its own; it just renders templates and calls the API to get live data. When you deploy to PythonAnywhere, this is what gets the public URL.

**`apps/api` — The Brain**

A separate Flask app that handles all the data. Every feature is its own "blueprint" (Flask's way of organizing routes):

- `routes/drops.py` — create, list, publish drops
- `routes/members.py` — VIP club management and tier logic
- `routes/retailers.py` — wholesale portal and allocations
- `routes/analytics.py` — revenue charts, hype scores, QR campaign data
- `routes/certificates.py` — issue and verify authenticity certs
- `routes/stats.py` — the overview numbers on the dashboard
- `routes/orders.py` — checkout locks + orders (pending → confirmed)
- `routes/payments.py` — Stripe PaymentIntents + webhook confirmation
- `routes/waitlist.py` — raffle/waitlist engine
- `routes/preorders.py` — preorder intent capture
- `routes/notifications.py` — email queue admin endpoints
- `routes/admin.py` — exports + allocation tools

Data is persisted via SQLAlchemy (SQLite by default). You can migrate to Postgres later by changing `DATABASE_URL` without rewriting routes.

---

**`packages/` — Shared Code**

Three packages that both apps can import so you never repeat yourself:

- `config/settings.py` — all your environment variables and business rules in one place (tier thresholds, max drop sizes, port numbers)
- `types/jonche_types.py` — Python TypedDicts that define what a Drop, Member, Retailer, or Certificate actually looks like — acts as a contract between apps
- `ui/` — reserved for shared HTML components as the platform grows

---

**The Tooling**

- `Makefile` — shortcuts so `make dev` starts both apps, `make test` runs all tests, `make deploy` reminds you of the steps
- `.github/workflows/ci.yml` — every push to GitHub automatically runs your 18 tests and linting so broken code never reaches production
- `DEPLOY.md` — the exact steps to get it live on PythonAnywhere, including how to mount both apps under one free-tier web app

---

**The Flow When Someone Visits Your Platform**

1. Browser hits `yourusername.pythonanywhere.com`
2. `apps/web/app.py` serves the dashboard HTML
3. The page's JavaScript calls `/api/stats/overview`, `/api/drops/`, etc.
4. `apps/api/app.py` handles those requests and returns JSON
5. The dashboard renders the data live

---

**What's Next (Your 5 Phases)**

The structure is already built to grow. Each new phase is just adding routes to the API and a new template to the web app — the scaffolding never needs to change. Phase 2 (Retailer Portal) routes already exist. Phases 3–5 follow the same pattern.
