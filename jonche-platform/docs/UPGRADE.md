This doc tracks the “what’s missing / what’s next” list for Jonche, but as of **April 8, 2026** a lot of the original gaps are now implemented.

---

## Implemented

- **Database:** SQLAlchemy-backed persistence (SQLite by default via `DATABASE_URL`)
- **Auth & roles:** JWT auth for admin/member/retailer + retailer API keys (see `apps/api/middleware/auth.py`)
- **Drop engine core:** per-member purchase limits + **8-minute checkout lock**
- **Raffle / waitlist:** enter + draw endpoints
- **Retailers:** invite/approve + allocations endpoint
- **Analytics:** DB-backed revenue + hype endpoints (dashboard still includes a few placeholder ratios)
- **Certificates:** issuance + public verification API endpoint
- **Web admin:** dashboard pages exist + admin login flow (cookie-based) to access protected pages
- **Public verification page:** branded `/verify/<token>` page in the web app
- **Preorders (phase starter):** public intent capture (`/preorder` + `/api/preorders/`)

---

## Still missing / next upgrades

### Payments (Stripe)
- Create Stripe PaymentIntents for drop purchases and preorder deposits
- Move `orders.py` from “instant completed” to “pending → webhook-confirmed”
- Add refunds + wholesale invoicing flows

### Email & notifications (SendGrid/Mailgun)
- Wire the `notifications` queue table to a real sender
- Trigger emails for: preorder received, raffle result, order confirmation + cert, retailer allocation updates

### Retailer portal (UI + workflows)
- Retailer-facing login page + session/cookie flow for retailers
- Purchase order submission + shipment status + invoice downloads

### Admin controls (UI)
- Override drop status, allocation adjustments, CSV export tools

---

## Recommended priority from here

1. Stripe payments + webhooks
2. Email notifications sender + triggers
3. Retailer portal UI + purchase-order flow
4. Admin panel tools (exports / overrides)
