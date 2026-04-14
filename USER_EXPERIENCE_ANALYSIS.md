# 🎯 User Experience & Access Flow Analysis – Jonche Platform

**Date:** April 14, 2026  
**Focus:** Three user personas with distinct access patterns and tracking

---

## 📌 Executive Summary

The Jonche Platform serves **three distinct user types** with fundamentally different access patterns:

| User Type | Auth Type | Primary Goal | Tracking | Entry Point |
|-----------|-----------|-------------|---------|------------|
| **Shoppers** | Guest (Session-based) | Browse & Purchase | None (Session only) | `/store` → `/cart` → `/checkout` |
| **Members** | Account-based (JWT) | Browse, Purchase, Track | Early access drops, Tier ranking | `/store` → Account login → VIP benefits |
| **Admins** | Admin account (JWT) | Manage platform | Full system oversight | `/admin` → Dashboard control center |

---

## 🛍️ USER 1: SHOPPERS (Guest Checkout)

### Profile
- **No registration required** – Browse and purchase as guest
- **Session-based cart** – Persistent via `jonche_cart_session` cookie (30-day expiry)
- **One-time checkout** – No account creation needed
- **Payment is required** – Full purchase at checkout

### Access Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ SHOPPER ENTRY POINT: /store (Public Landing)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. DISCOVERY & BROWSING                                        │
│     └─ Commercials carousel (auto-playing ads)                 │
│     └─ Category navigation                                     │
│     └─ Featured products grid (8 items)                        │
│     └─ Search & filter by category/price                      │
│                                                                  │
│  2. PRODUCT PAGES                                              │
│     └─ /store/products?category_id=X (Browse all)             │
│     └─ /store/product/{id} (Detail page + images)             │
│     └─ No login required                                       │
│                                                                  │
│  3. ADD TO CART (Session-based)                               │
│     └─ POST /api/store/cart/items                              │
│     └─ Creates Cart with session_token (if not member)        │
│     └─ Sets jonche_cart_session cookie (30 days)              │
│     └─ Cart persists across sessions                          │
│                                                                  │
│  4. SHOPPING CART REVIEW                                       │
│     └─ /store/cart (Public page)                              │
│     └─ View items, adjust quantities, remove items            │
│     └─ Order summary: subtotal + tax (8%) + shipping          │
│     └─ Free shipping over $50; $9.99 otherwise                │
│     └─ GET /api/store/cart (session-based lookup)            │
│                                                                  │
│  5. CHECKOUT (REQUIRES LOGIN)                                  │
│     └─ /store/checkout → REDIRECT to /account/login           │
│     └─ Must create account or guest won't reach payment      │
│     └─ Shipping form: name, address, email                    │
│     └─ Collect payment via Stripe-ready endpoint              │
│                                                                  │
│  6. ORDER COMPLETION                                           │
│     └─ POST /store/order (requires @require_member)           │
│     └─ Stripe payment verification (future: webhook)          │
│     └─ Cart marked as "completed"                             │
│     └─ Order confirmation email sent                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Features
- ✅ **No friction** – Browse entire store without account
- ✅ **Session persistence** – Cart saved in browser cookies
- ✅ **Guest checkout** – Pay immediately at checkout
- ⚠️ **One-time buyer** – No account to track order history
- ⚠️ **No VIP benefits** – Never sees early drops or raffle access

### Technical Stack
```
Frontend: base_public.html (public navbar + footer)
  └─ Unauthenticated routes
  └─ Session cookies for cart

API:
  ├─ GET /api/products/ (public, paginated)
  ├─ GET /api/products/{id} (public)
  ├─ POST /api/store/cart/items (session-based)
  ├─ GET /api/store/cart (session token lookup)
  ├─ POST /api/store/checkout (@require_member → redirects to login)

Database:
  └─ Cart (session_token-based, member_id=null)
  └─ CartItem (linked to cart)
  └─ Products (public visibility)
```

### Current Gaps & Issues
🔴 **Checkout Forces Account Creation**
   - Shoppers must create account at checkout (friction)
   - No true "guest checkout" – cart is invalidated on redirect to login
   - **Better UX:** Allow guest email + password opt-in or SSO

🔴 **No Order Tracking**
   - After purchase, shopper can't verify order status
   - Receipt/confirmation only via email
   - **Better UX:** Provide one-time order lookup by email + order number

🔴 **Session Cart Quality**
   - 30-day expiry may be too long (abandoned carts)
   - No nudge/reminder for abandoned carts
   - **Better UX:** Add cart recovery email after 3 days

---

## 👥 USER 2: MEMBERS (Tracked & VIP Benefits)

### Profile
- **Registration required** – Create account with email + password
- **Multi-tier system** – Bronze → Silver (spend $2,500) → Gold (spend $8,000)
- **Persistent tracking** – All purchases linked to member account
- **VIP features** – Early drop access, raffle participation, QR tracking
- **Optional mobile number** – For notifications/SMS alerts

### Access Flow

```
┌────────────────────────────────────────────────────────────────────┐
│ MEMBER ENTRY POINT: /store → /account/login or /account/register  │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  1. ACCOUNT CREATION                                              │
│     └─ /account/register (POST /api/auth/register)               │
│     └─ Fields: email, password, name, phone (optional)           │
│     └─ Email must be unique                                      │
│     └─ Returns JWT token + sets jonche_member_token cookie      │
│     └─ Redirects to /store (persisted login)                     │
│                                                                    │
│  2. LOGIN (PERSISTENT SESSION)                                    │
│     └─ /account/login (POST /api/auth/login)                    │
│     └─ Email + password → JWT token                             │
│     └─ Cookie: jonche_member_token (24-hour expiry)             │
│     └─ next parameter handles redirect post-login               │
│     └─ GET /members/me returns profile (requires @require_member)│
│                                                                    │
│  3. MEMBER DASHBOARD (Future/Planned)                            │
│     └─ Account page (view profile, edit, preferences)           │
│     └─ Order history + tracking                                 │
│     └─ VIP tier status + benefits                               │
│     └─ Reward points / loyalty dashboard                        │
│     ⚠️ Currently: Limited UI → mostly API-only endpoints        │
│                                                                    │
│  4. ENHANCED STORE ACCESS                                        │
│     └─ Same /store/products & /store/cart as guest              │
│     └─ BUT: Add to cart automatically links to member account   │
│     └─ Cart no longer session-based: member_id linked          │
│     └─ Cart survives logout/login cycles                        │
│                                                                    │
│  5. EXCLUSIVE DROPS & RAFFLE ACCESS                              │
│     └─ Member-only drops (status="live", use_raffle=true)       │
│     └─ Join waitlist: POST /api/drops/{id}/waitlist             │
│     └─ Random draw from WaitlistEntry (eligible members)        │
│     └─ Selected members get checkout window (e.g., 15 min)      │
│     └─ Can purchase up to max_per_member (default=1)            │
│                                                                    │
│  6. TIER PROGRESSION TRACKING                                     │
│     └─ Member.lifetime_spend auto-calculated                    │
│     └─ Tier auto-computed: bronze/silver/gold                  │
│     └─ GET /members/me shows current tier                       │
│     └─ Tier unlocks perks (future: discounts, early access)    │
│     └─ SQL: lifetime_spend >= $8k → gold; $2.5k → silver      │
│                                                                    │
│  7. QR CAMPAIGN TRACKING (Optional)                              │
│     └─ Receive unique QR code via email/SMS                      │
│     └─ Track scans: GET /api/qr/{campaign_id}/scans             │
│     └─ Conversion tracking: POST /qr/{id}/convert (on purchase) │
│     └─ Analytics: See personal referral/tracking stats          │
│                                                                    │
│  8. CERTIFICATE VERIFICATION (Authenticity)                      │
│     └─ Each drop purchase → uniquely numbered certificate       │
│     └─ Member views: /certificates (admin-only UI, future)      │
│     └─ Public verify: /verify/{token} (no login)               │
│                                                                    │
│  9. CHECKOUT + ORDER TRACKING                                    │
│     └─ /store/checkout (requires @require_member)               │
│     └─ POST /api/store/checkout → PaymentIntent setup          │
│     └─ POST /api/store/order → Create Order + confirm payment  │
│     └─ GET /orders/{order_number} (member-only, access check)  │
│     └─ Order.shipped_at, tracking_number populated by admin     │
│                                                                    │
│  10. NOTIFICATIONS & COMMUNICATIONS                              │
│      └─ Email notifications: drops, tier upgrades, shipments   │
│      └─ SMS alerts (if opted-in, future enhancement)           │
│      └─ GET /api/notifications (in-app notification feed)      │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Key Features
- ✅ **Persistent identity** – All purchases tied to account
- ✅ **VIP tier ladder** – Automatic progression (Bronze → Silver → Gold)
- ✅ **Raffle drops** – Early access & lottery for limited releases
- ✅ **Order tracking** – Full purchase history + shipping status
- ✅ **Multi-channel notifications** – Email + SMS (future)
- ✅ **QR referral tracking** – Unique codes for affiliate/promo tracking
- ✅ **Certificate ownership** – Authenticity proof per purchase

### Technical Stack
```
Frontend: base_public.html (navbar now shows account icon)
  └─ member_login.html
  └─ member_register.html
  └─ (dashboard/profile pages: TBD/in progress)

API:
  ├─ POST /api/auth/login (email + password → JWT)
  ├─ POST /api/auth/register (create account)
  ├─ GET /members/me (@require_member)
  ├─ GET /members/{id} (@require_admin)
  ├─ POST /drops/{id}/waitlist (@require_member, raffle entry)
  ├─ GET /orders/{order_number} (@require_member, with access check)
  ├─ POST /store/cart/items (now member_id linked)
  ├─ GET /certificates/{token} (public verify)
  └─ GET /qr/{campaign_id}/convert (conversion tracking)

Database:
  ├─ Member (email, password_hash, tier, lifetime_spend)
  ├─ Order (member_id, drop_id, status, tracking_number)
  ├─ WaitlistEntry (member_id, drop_id, status: selected/not_selected/purchased)
  ├─ Certificate (member_id, drop_id, unique token)
  ├─ QRCampaign (member-specific or general)
  └─ Cart (now member_id primary, survives logout)
```

### Current Member Experience Gaps
🟡 **Limited Dashboard UI**
   - Profile editing → API-only (no UI page visible)
   - Order history → API endpoint exists, but no visual dashboard
   - Tier benefits → Not clearly displayed
   - **Better UX:** Build `/account` dashboard with order timeline

🟡 **Notification Quality**
   - Notifications table exists, queue-based
   - No in-app notification feed (API exists, UI missing)
   - SMS opt-in flow not implemented
   - **Better UX:** Add push notifications + SMS reminder for drops

🟡 **Cart Persistence Clarity**
   - Members' carts survive logout, but unclear to user
   - No "saved for later" feature (wishlist)
   - **Better UX:** Show "Items saved" badge, offer quick checkout from dashboard

🟡 **Raffle UX**
   - Entry page unclear (when drawn, how many win)
   - No countdown timer on draw date
   - No email notification of drawn winners (unless manual)
   - **Better UX:** Add prominent "You're in the raffle!" status + countdown

---

## 🛡️ USER 3: ADMINS (Full Platform Management)

### Profile
- **Admin account** – Email + password (seeded or manually created)
- **Superadmin role** – Optional `is_superadmin` flag for elevated permissions
- **Command center** – Central dashboard for all operations
- **Full system oversight** – Can create, edit, delete any resource
- **Last login tracking** – Audit trail

### Access Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│ ADMIN ENTRY POINT: /login → /dashboard (Admin Command Center)        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. ADMIN LOGIN                                                     │
│     └─ /login (POST /api/auth/admin/login)                         │
│     └─ Email + password → JWT token (24-hour expiry)              │
│     └─ Cookie: jonche_admin_token (httponly, samesite=Lax)        │
│     └─ Redirects to /dashboard (default after login)              │
│     └─ Legacy support: checks jonche_token cookie                 │
│                                                                      │
│  2. ADMIN DASHBOARD (/dashboard)                                    │
│     └─ @require_admin_web decorator (protected route)             │
│     └─ Central command center for all operations                  │
│     └─ Key sections:                                              │
│        ├─ Real-time stats widget (sales, conversions, etc.)       │
│        ├─ Recent orders feed                                      │
│        ├─ Active drops countdown                                  │
│        ├─ Top members (by spend, tier)                           │
│        ├─ Quick-links to admin sections                          │
│        └─ System health indicators                                │
│                                                                      │
│  3. DROPS MANAGEMENT (/drops)                                       │
│     └─ List all drops (draft, upcoming, live, sold_out, ended)    │
│     └─ Create new drop:                                           │
│        ├─ Name, colorway, size range (e.g., "7-14")               │
│        ├─ Price (in cents)                                        │
│        ├─ Total units + retailer allocations                      │
│        ├─ Raffle mode (yes/no) + max per member                   │
│        └─ Apliiq fulfillment mapping (optional)                   │
│     └─ Edit/publish drops (set drop_at → goes live)              │
│     └─ Monitor inventory in real-time                             │
│        ├─ Units sold, locked (checkout), available               │
│        ├─ Hype % (sold/sellable * 100)                           │
│     └─ End drops manually or auto-expire                          │
│     └─ Generate certificates per drop                             │
│                                                                      │
│  4. VIP MEMBERS MANAGEMENT (/vip)                                   │
│     └─ List all members (filter by tier: gold/silver/bronze)      │
│     └─ Member details view:                                       │
│        ├─ Purchase history (lifetime_spend)                       │
│        ├─ Current tier + auto-calculated next tier threshold     │
│        ├─ Last login + account created date                       │
│        ├─ Blacklist status                                        │
│     └─ Manual tier override (if needed)                           │
│     └─ Blacklist member: POST /members/{id}/blacklist             │
│        └─ Prevents from joining drops + shows "Account suspended" │
│     └─ Unblacklist: POST /members/{id}/unblacklist               │
│     └─ Email member (future: bulk email campaigns)                │
│                                                                      │
│  5. RETAILERS & PARTNERSHIP PORTAL (/retailers)                     │
│     └─ Manage wholesale partners (separate from members)          │
│     └─ Retailer list (status: review, pending, active, suspended)│
│     └─ Allocations per drop:                                      │
│        ├─ Assign quantities to each retailer                      │
│        ├─ Tier-based limits (basic: 10, select: 20, premier: 50) │
│        ├─ Query: RetailerAllocation table                         │
│     └─ Retailer tier management (basic/select/premier)           │
│     └─ API key regeneration + access logs                         │
│     └─ Edit retailer info (contact, phone, city, tier)           │
│                                                                      │
│  6. ANALYTICS & REPORTING (/analytics)                              │
│     └─ Dashboard-style metrics:                                   │
│        ├─ Total revenue (orders.status="completed")              │
│        ├─ Orders by drop + by member tier                        │
│        ├─ Conversion funnel (browsers → cart → purchase)         │
│        ├─ Top products + top members                             │
│        ├─ QR campaign performance (scans → conversions)          │
│        ├─ Raffle statistics (entries → winners)                  │
│        └─ Member acquisition trends                              │
│     └─ Export data (CSV/JSON) for BI tools                        │
│                                                                      │
│  7. CERTIFICATES & AUTHENTICITY (/certificates)                     │
│     └─ Batch generate certificates per drop                       │
│     └─ Each cert gets unique: ID, serial, signature (future)     │
│     └─ List certificates by drop                                  │
│     └─ Revoke if needed (fraud, recall)                           │
│     └─ Public verify page: /verify/{token} (no login needed)      │
│                                                                      │
│  8. STORE MANAGEMENT (/admin/store)                                 │
│     └─ Products (from Apliiq):                                    │
│        ├─ Add/remove products                                     │
│        ├─ Edit descriptions, pricing, images                      │
│        ├─ Manage categories & featured section                    │
│        ├─ Commercials carousel (videos/ads)                       │
│     └─ Store design settings (future):                            │
│        ├─ Banner text, promo codes                                │
│        ├─ Shipping rates override                                 │
│                                                                      │
│  9. PARTNER PROGRAMS ADMIN (/admin/partners)                        │
│     └─ View partner applications (intake submissions)             │
│     └─ Statuses: applied, under_review, approved, rejected       │
│     └─ Manual review + approval workflow                          │
│     └─ Assign tier (basic/select/premier for retailers)           │
│     └─ Track commissions + payouts per partner                    │
│     └─ Programs: Retail Alliance, Affiliates, Referral, Executive│
│                                                                      │
│  10. ADMIN UTILITIES (/admin)                                       │
│      └─ Bulk exports (members, orders, drops)                     │
│      └─ Data overrides:                                           │
│         ├─ Manually adjust tier                                   │
│         ├─ Force member into drop                                 │
│         ├─ Cancel order (future: refund flow)                     │
│         └─ Modify pricing/inventory                               │
│      └─ System settings:                                          │
│         ├─ Payout schedules                                       │
│         ├─ Notification templates                                 │
│         ├─ Stripe/Apliiq integrations                             │
│         └─ QR campaign defaults                                   │
│                                                                      │
│  11. LOGOUT                                                        │
│      └─ POST /logout                                              │
│      └─ Deletes jonche_admin_token cookie                         │
│      └─ Redirects to /login                                       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Key Features
- ✅ **Full CRUD ops** – Create/read/update/delete all resources
- ✅ **Real-time inventory** – Track available units across drops
- ✅ **Member management** – Tier override, blacklisting, communication
- ✅ **Retailer allocations** – Wholesale partner assignments per drop
- ✅ **Analytics suite** – Revenue, conversion, member trends
- ✅ **QR tracking** – Campaign performance + conversion measurement
- ✅ **Bulk operations** – Export data, bulk edits (planned)
- ✅ **Audit trail** – Last login tracking + action timestamps

### Technical Stack
```
Frontend: base.html (admin-only navbar + protected sidebar)
  ├─ dashboard.html (command center)
  ├─ drops.html (drop management)
  ├─ vip.html (member management)
  ├─ retailers.html (partner portal)
  ├─ analytics.html (metrics & reporting)
  ├─ certificates.html (certificate management)
  ├─ admin.html (utilities & overrides)
  ├─ admin_partners.html (partner app review)
  └─ admin_store.html (product & store setup)

API:
  ├─ POST /api/auth/admin/login
  ├─ GET /api/admin/stats (dashboard summary)
  ├─ CRUD /api/drops/ (@require_admin)
  ├─ CRUD /api/members/ (@require_admin)
  ├─ CRUD /api/retailers/ (@require_admin)
  ├─ POST /api/retailers/{id}/allocations (@require_admin)
  ├─ GET /api/analytics/ (reports)
  ├─ CRUD /api/certificates/ (@require_admin)
  ├─ CRUD /api/qr/ (campaigns)
  ├─ CRUD /api/products/ (@require_admin)
  └─ GET /api/partners/applications (@require_admin)

Database:
  ├─ Admin (email, password_hash, is_superadmin, last_login)
  ├─ Drop (all fields for drop mgmt)
  ├─ Member (all tier + blacklist fields)
  ├─ Retailer (allocations, tier, status)
  ├─ Order (tracking numbers added by admin)
  ├─ Certificate (per purchase, unique tokens)
  ├─ QRCampaign & QRScan (tracking data)
  └─ Product (store inventory)
```

### Admin Experience Gaps
🟡 **Dashboard Depth**
   - Basic stats page exists, but limited interactivity
   - No drill-down from metric → detailed view
   - No custom date range filtering
   - **Better UX:** Add date-range picker, real-time refresh, drill-down capability

🟡 **Bulk Operations**
   - Export works but import/bulk-edit missing
   - No batch member tier recalculation
   - No bulk communication feature
   - **Better UX:** Add bulk CSV import, email campaigns, member tier reset

🟡 **Audit Logging**
   - Admin actions not fully logged
   - No "who changed what when" trail
   - Can't revert accidental changes
   - **Better UX:** Add comprehensive audit log + undo capability

🟡 **Webhook Integration**
   - Stripe payment webhooks: stub only
   - Apliiq fulfillment webhooks: incomplete
   - No automatic status updates on shipment
   - **Better UX:** Implement full webhook handlers

---

## 🔐 Authentication & Authorization Matrix

| Role | Login | Auth Method | Token Expiry | Features |
|------|-------|-------------|-------------|----------|
| **Shopper (Guest)** | None | Session cookie | 30 days | Browse, add to cart, guest checkout |
| **Member** | Required | JWT + Cookie | 24 hours | Exclusive drops, tier tracking, order history |
| **Admin** | Required | JWT + Cookie | 24 hours | Full system management, analytics, overrides |

### Decorator Usage
```python
# Public routes (no decorator)
@app.route("/store")
def store_homepage(): ...

# Guest + Member access
@require_member
def checkout(): ...

# Admin only
@require_admin
def admin_dashboard(): ...
@require_admin_web  # Web-specific auth check
def admin_page(): ...
```

---

## 🚨 Critical UX Issues by Persona

### 🛍️ Shoppers
| Issue | Severity | Impact | Recommendation |
|-------|----------|--------|-----------------|
| Checkout forces account creation | 🔴 High | Abandon rate ↑ on payment | Implement true guest checkout (email only) |
| No order tracking post-purchase | 🔴 High | Support inquiries ↑ | Add order lookup by email+number |
| Abandoned cart no reminder | 🟡 Medium | Lost recovery revenue | Email nudge after 3 days idle |
| Session expiry unclear | 🟡 Medium | Lost work on mobile | Show "Cart expires in X days" badge |

### 👥 Members
| Issue | Severity | Impact | Recommendation |
|-------|----------|--------|-----------------|
| Dashboard UI incomplete | 🔴 High | Don't see value of account | Build `/account` page with order timeline |
| Raffle entry unclear | 🟡 Medium | Confusion on how to win | Show "You're in the drawing! Draw date: X" |
| Tier unlock benefits hidden | 🟡 Medium | No motivation to spend | Highlight "Spend $2.5k more for Silver perks" |
| No wishlist / save for later | 🟡 Medium | Can't bookmark products | Add heart icon → wishlist |

### 🛡️ Admins
| Issue | Severity | Impact | Recommendation |
|-------|----------|--------|-----------------|
| Analytics lacks drill-down | 🟡 Medium | Limited actionable insights | Add date filters + metric drill-down |
| No audit trail | 🟡 Medium | Can't track data changes | Log all CRUD ops with user + timestamp |
| Bulk email missing | 🟡 Medium | Manual outreach tedious | Add email template system + bulk send |
| Webhook stubs incomplete | 🔴 High | Manual workflows needed | Complete Stripe + Apliiq integrations |

---

## 🎯 Recommended Priority Fixes

### Phase 1: Critical (Affects Revenue)
1. **Implement true guest checkout** (Shoppers stay in funnel)
2. **Build member dashboard** (Show value of registration)
3. **Complete payment webhooks** (Automate order creation)

### Phase 2: High (Improves Retention)
1. **Add order lookup by email** (Guest support + confidence)
2. **Build raffle countdown UX** (Member engagement)
3. **Implement tier unlock messaging** (Incentivize spending)

### Phase 3: Medium (Quality of Life)
1. **Add audit logging** (Admin oversight)
2. **Implement cart recovery emails** (Abandoned cart recovery)
3. **Build admin date-range filters** (Better analytics)

---

## 📊 Summary: Access Control Pyramid

```
                    ┌─────────────────┐
                    │   ADMINS (JWT)  │  ← Full system access
                    │   24-hr token   │     All CRUD, analytics
                    ├─────────────────┤
                    │  MEMBERS (JWT)  │  ← Account-based
                    │  24-hr token    │     Drops, tracking, profile
                    ├─────────────────┤
                    │ SHOPPERS (Sess) │  ← Guest session
                    │ 30-day cookie   │     Browse, cart, guest checkout
                    └─────────────────┘
```

---

## ✅ Tracking Summary by User

| User Type | What's Tracked | Where | Duration | Use Case |
|-----------|-----------------|-------|----------|----------|
| **Shopper** | Cart contents, session ID | Browser cookie | 30 days | Persistence across visits |
| **Member** | All purchases, tier, login history | Database | Lifetime | VIP status, order history, tier unlock |
| **Admin** | All actions, logins | Database + audit log | Permanent | Compliance, forensics, security |
| **QR Ref** | Scans + conversions | QRScan table | Campaign life | Affiliate tracking, performance |

---

## 🔗 Key Database Entities by Persona

### Shoppers
- `Cart` (session_token-based, no member_id)
- `CartItem` (product link)
- `Product` (public visibility)

### Members
- `Member` (tier, lifetime_spend, is_blacklisted)
- `Cart` (member_id-based, survives logout)
- `Order` (order_number, status, tracking_number)
- `WaitlistEntry` (drop participation)
- `Certificate` (authenticity proof)
- `QRScan` (tracking if opted-in)

### Admins (Full View)
- All tables + audit logs
- Real-time stats cache
- Partner applications queue

---

**End of Analysis**  
For detailed endpoint documentation, see [PHASE5_API.md](docs/PHASE5_API.md)
