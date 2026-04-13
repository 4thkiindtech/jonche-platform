# Role-Based Partner Dashboard System

## Overview

The JONCHE Platform now includes a **comprehensive role-based dashboard system** for four types of revenue-generating partners:

1. **Affiliate Creators** — Social media promoters earning commission on referrals
2. **Strategic Referral Partners** — High-ticket deal sourcers (funding, bulk orders, partnerships)
3. **Retail Alliance Partners** — Boutique distributions centers managing allocations
4. **Executives** — Top-tier strategic partners with territory-based opportunities

Each dashboard is **purpose-built** for the partner's role, featuring earnings tracking, performance metrics, messaging, and announcements.

---

## 🏗️ Architecture

### Database Models (apps/api/db/models.py)

#### Partner Account Models
- **AffiliateAccount** — Social media creators with referral links
- **ReferralPartnerAccount** — High-value deal partners
- **RetailPartnerAccount** — Retail boutique partner accounts
- **ExecutiveAccount** — Top-tier strategic executives

#### Supporting Models
- **AffiliateEarning** — Tracks individual affiliate commissions from orders
- **PartnerReferral** — Submitted deals/funding opportunities
- **PartnerMessage** — Inbox system for partner communication
- **PartnerAnnouncement** — Broadcast announcements to partner groups

### API Endpoints (apps/api/routes/partner_dashboards.py)

All endpoints are under `/api/dashboards/` prefix.

#### Affiliate Creator Endpoints
```
POST   /affiliate/register              # Create new affiliate account
POST   /affiliate/login                 # Affiliate login
POST   /affiliate/logout                # Affiliate logout
GET    /affiliate/dashboard             # Dashboard summary
GET    /affiliate/earnings              # Earnings history
GET    /affiliate/profile               # Get profile
PUT    /affiliate/profile               # Update profile
```

#### Referral Partner Endpoints
```
POST   /referral-partner/register       # Create new referral partner
POST   /referral-partner/login          # Login
POST   /referral-partner/logout         # Logout
GET    /referral-partner/dashboard      # Dashboard summary
GET    /referral-partner/referrals      # Get deals/referrals
POST   /referral-partner/submit-referral # Submit new deal
```

#### Retail Partner Endpoints
```
POST   /retail-partner/register         # Create retail partner account
POST   /retail-partner/login            # Login
POST   /retail-partner/logout           # Logout
GET    /retail-partner/dashboard        # Dashboard summary
```

#### Executive Endpoints
```
POST   /executive/register              # Create executive account
POST   /executive/login                 # Login
POST   /executive/logout                # Logout
GET    /executive/dashboard             # Dashboard summary
```

#### Shared Endpoints
```
GET    /messages                        # Get messages for logged-in partner
POST   /messages                        # Send message
GET    /announcements                   # Get announcements for partner group
```

---

## 📊 Dashboard Templates

### 1. Affiliate Creator Dashboard (/affiliate_dashboard.html)

**Purpose:** Track referral earnings, conversions, and social media reach.

**Key Sections:**
- 💰 **Total Earnings** — All-time commission earned
- ⏳ **Pending Earnings** — Commissions awaiting approval
- 🔗 **Referral Link** — One-click copy/share link
- 📈 **Conversion Rate** — Clicks to sales ratio
- 💵 **Earnings History** Tab — Sortable earnings by status (pending/approved/paid)
- 🔗 **Recent Referrals** Tab — Recent orders & conversions
- 📊 **Campaigns** Tab — (Future) Track performance by campaign
- 💬 **Messages** Tab — Inbox from JONCHE team
- 👤 **Profile** Tab — Edit social media handles, bio, website

**Key Features:**
- Real-time earnings display
- Referral link with copy/share buttons
- Sortable earnings history with status indicators
- Direct message inbox

---

### 2. Referral Partner Dashboard (/referral_partner_dashboard.html)

**Purpose:** Track deal pipeline, commissions, and partnership performance.

**Key Sections:**
- 🎯 **Deals Submitted** — Total deals submitted
- ✅ **Funded Deals** — Deals that closed
- 💰 **Total Commission** — All paid commissions
- ⏳ **Pending Commission** — Approved but unpaid
- 📊 **Deal Pipeline** Tab — Visual breakdown by status (submitted/review/approved/funded)
- 💼 **All Deals** Tab — Filterable list of all referrals
- 💵 **Commission Report** Tab — Summary of all commissions
- 💬 **Direct Messages** Tab — Private communication with JONCHE team
- 👤 **Profile** Tab — Edit contact info, company, region

**Key Features:**
- Deal submission form modal
- Pipeline status tracker with visual cards
- Commission tracking (projected vs. paid)
- Direct line to JONCHE team

---

### 3. Retail Partner Dashboard (/retail_partner_dashboard.html)

**Purpose:** Manage allocations, orders, and wholesale distribution.

**Key Sections:**
- 📦 **Total Allocations** — Units allocated across drops
- ✅ **Purchased Units** — Units actually ordered
- ⏳ **Pending Orders** — Orders awaiting shipment
- 🎁 **Available Drops** — New releases to order
- 🎁 **Available Drops** Tab — Browse and request allocations
- 📋 **My Allocations** Tab — Current units allocated per drop
- 📦 **My Orders** Tab — Order history and status
- 🎨 **Marketing Assets** Tab — Download promotional materials
- 💬 **Messages** Tab — Communication from JONCHE
- 👤 **Profile** Tab — Store info, contact, website

**Key Features:**
- Browse live drops with easy order buttons
- Allocation request workflow
- Order tracking with shipping info
- Marketing asset downloads

---

### 4. Executive Dashboard (/executive_dashboard.html)

**Purpose:** High-level strategic overview of deal portfolio and territory.

**Key Sections:**
- 💼 **Total Deal Value** — Aggregate value of all partnerships
- 💰 **Commission Earned** — Total paid commissions
- ⏳ **Pending Revenue** — Approved deals pending payment
- 🎯 **Territory** — Assigned geographic region
- 📊 **Dashboard** Tab — Active deals, recent announcements
- 🎯 **Territory Opportunities** Tab — Region-specific partnership prospects
- 💼 **My Deals** Tab — Full deal portfolio with filtering
- 📢 **Partners & Updates** Tab — Strategic announcements
- 💬 **Direct Line** Tab — Premium communication channel
- 👤 **Profile** Tab — Executive info and territory

**Key Features:**
- Premium visual design reflecting status
- Territory-specific opportunity tracking
- High-level deal value visualization
- Strategic announcement feed
- Direct communication with executive team

---

## 🔐 Authentication Flow

### Register a Partner
```javascript
// POST /api/dashboards/{role}/register
{
  "email": "partner@example.com",
  "password": "secure_pass",
  // role-specific fields...
}
```

### Login
```javascript
// POST /api/dashboards/{role}/login
{
  "email": "partner@example.com",
  "password": "secure_pass"
}
```

Session token is stored in browser session. All subsequent requests include the session cookie for authentication.

### Logout
```javascript
// POST /api/dashboards/{role}/logout
```

---

## 💾 Database Schema

### Partner Account Tables

```sql
-- Affiliate Creators
CREATE TABLE affiliate_accounts (
  id INTEGER PRIMARY KEY,
  email VARCHAR UNIQUE NOT NULL,
  password_hash VARCHAR,
  display_name VARCHAR,
  referral_link_token VARCHAR UNIQUE,
  commission_rate_percent FLOAT DEFAULT 10.0,
  total_earnings_cents INTEGER DEFAULT 0,
  pending_earnings_cents INTEGER DEFAULT 0,
  total_clicks INTEGER DEFAULT 0,
  total_conversions INTEGER DEFAULT 0,
  status VARCHAR DEFAULT 'active',
  created_at DATETIME
);

-- Referral Partner Accounts
CREATE TABLE referral_partner_accounts (
  id INTEGER PRIMARY KEY,
  email VARCHAR UNIQUE NOT NULL,
  password_hash VARCHAR,
  contact_name VARCHAR NOT NULL,
  company_name VARCHAR,
  total_deals_submitted INTEGER DEFAULT 0,
  total_deals_funded INTEGER DEFAULT 0,
  projected_commission_cents INTEGER DEFAULT 0,
  total_commission_cents INTEGER DEFAULT 0,
  pending_commission_cents INTEGER DEFAULT 0,
  tier VARCHAR DEFAULT 'bronze',
  status VARCHAR DEFAULT 'active',
  created_at DATETIME
);

-- Retail Partner Accounts
CREATE TABLE retail_partner_accounts (
  id INTEGER PRIMARY KEY,
  retailer_id INTEGER FOREIGN KEY,
  email VARCHAR UNIQUE NOT NULL,
  password_hash VARCHAR,
  store_name VARCHAR NOT NULL,
  contact_name VARCHAR NOT NULL,
  total_allocations INTEGER DEFAULT 0,
  total_purchased_units INTEGER DEFAULT 0,
  pending_orders INTEGER DEFAULT 0,
  tier VARCHAR DEFAULT 'basic',
  status VARCHAR DEFAULT 'active',
  created_at DATETIME
);

-- Executive Accounts
CREATE TABLE executive_accounts (
  id INTEGER PRIMARY KEY,
  email VARCHAR UNIQUE NOT NULL,
  password_hash VARCHAR,
  executive_name VARCHAR NOT NULL,
  company_name VARCHAR NOT NULL,
  territory VARCHAR,
  total_deal_value_cents INTEGER DEFAULT 0,
  total_commission_cents INTEGER DEFAULT 0,
  pending_commission_cents INTEGER DEFAULT 0,
  status VARCHAR DEFAULT 'active',
  created_at DATETIME
);

-- Earnings Tracking
CREATE TABLE affiliate_earnings (
  id INTEGER PRIMARY KEY,
  affiliate_id INTEGER FOREIGN KEY,
  order_id INTEGER FOREIGN KEY,
  referral_source VARCHAR,
  order_value_cents INTEGER,
  commission_rate_percent FLOAT,
  commission_cents INTEGER,
  status VARCHAR DEFAULT 'pending', -- pending/approved/paid
  paid_at DATETIME,
  payout_batch_id VARCHAR,
  created_at DATETIME
);

-- Deal/Referral Tracking
CREATE TABLE partner_referrals (
  id INTEGER PRIMARY KEY,
  referral_partner_id INTEGER FOREIGN KEY,
  executive_id INTEGER FOREIGN KEY,
  referral_type VARCHAR, -- funding/bulk_order/partnership
  title VARCHAR,
  description TEXT,
  estimated_value_cents INTEGER,
  actual_value_cents INTEGER,
  commission_percent FLOAT,
  commission_cents INTEGER,
  status VARCHAR, -- submitted/approved/funded/closed/paid
  created_at DATETIME
);

-- Messaging System
CREATE TABLE partner_messages (
  id INTEGER PRIMARY KEY,
  affiliate_id INTEGER FOREIGN KEY,
  referral_partner_id INTEGER FOREIGN KEY,
  retail_partner_id INTEGER FOREIGN KEY,
  executive_id INTEGER FOREIGN KEY,
  subject VARCHAR,
  body TEXT,
  message_type VARCHAR DEFAULT 'general',
  read_at DATETIME,
  created_at DATETIME,
  created_by_admin BOOLEAN DEFAULT true
);

-- Announcements
CREATE TABLE partner_announcements (
  id INTEGER PRIMARY KEY,
  title VARCHAR,
  content TEXT,
  target_groups VARCHAR, -- comma-separated: affiliates, referral_partners, retail_partners, executives, all
  priority VARCHAR DEFAULT 'normal',
  status VARCHAR DEFAULT 'draft', -- draft/published/archived
  published_at DATETIME,
  expires_at DATETIME,
  created_at DATETIME
);
```

---

## 🚀 Implementation Checklist

- [x] Database models created (8 models total)
- [x] API endpoints implemented (all 4 partner types + shared)
- [x] Dashboard templates created (4 templates)
- [x] Authentication system (login/register/logout)
- [x] Frontend JavaScript for all dashboards
- [x] Messaging system
- [x] Announcements system
- [ ] Admin panel for partner management (next)
- [ ] Email notifications
- [ ] Payout system integration
- [ ] Analytics and reporting
- [ ] Export functions

---

## 📋 Next Steps

### Phase 2: Admin Panel
Create `/api/admin/partners` endpoints for:
- Approve/reject partner applications
- Manage partner status (active/suspended)
- View partner performance metrics
- Send announcements to groups
- Process commissions & payouts

### Phase 3: Integration
- Link affiliate referrals to orders (add `affiliate_id` to Order model)
- Track clicks via QR codes → affiliate
- Automatic commission calculation & payout
- Email notifications for earnings/deals

### Phase 4: Analytics
- Dashboard metrics export
- Performance leaderboards
- Territory heat maps
- Commission reporting

---

## 🔗 URL Routes (Web Frontend)

```
/affiliate                    → Affiliate login/register page
/affiliate/dashboard          → Affiliate dashboard
/referral-partner             → Referral partner login/register
/referral-partner/dashboard   → Referral partner dashboard
/retail-partner               → Retail partner login/register
/retail-partner/dashboard     → Retail partner dashboard
/executive                     → Executive login/register
/executive/dashboard           → Executive dashboard
```

---

## 💡 Key Features Summary

| Feature | Affiliate | Referral | Retail | Executive |
|---------|-----------|----------|--------|-----------|
| Earnings Tracking | ✅ | ✅ | — | ✅ |
| Referral Link | ✅ | — | — | — |
| Deal Pipeline | — | ✅ | — | ✅ |
| Allocations | — | — | ✅ | — |
| Messaging | ✅ | ✅ | ✅ | ✅ |
| Announcements | ✅ | ✅ | ✅ | ✅ |
| Performance Metrics | ✅ | ✅ | ✅ | ✅ |
| Profile Management | ✅ | ✅ | ✅ | ✅ |

---

## 🎯 Commission Models

### Affiliate Creator Commission
- **On:** Each referral → sale conversion
- **Amount:** 10% (configurable, default 10%)
- **Status Flow:** pending → approved → paid
- **Payout:** Monthly aggregation

### Referral Partner Commission
- **On:** Lead value when deal closes
- **Amount:** Specified per deal
- **Status Flow:** submitted → approved → funded → closed → paid
- **Payout:** Quarterly after deal closes

### Executive Commission
- **On:** Territory deal volume
- **Amount:** Percentage of deal value
- **Payout:** Quarterly

### Retail Partner
- **Commission:** Wholesale pricing built into orders
- **No separate commission tracking needed**

---

## 📞 Support

For integration questions or issues, refer to:
- [partner_dashboards.py](../routes/partner_dashboards.py) — API endpoints
- [models.py](../db/models.py) — Database schema (search "# ── Affiliate Creator" section)
- Dashboard templates — JavaScript logic for frontend

## Deployment Notes

1. Run database migration to create new tables:
   ```bash
   flask db upgrade
   ```

2. Create admin endpoints for partner management (see next phase)

3. Test each dashboard login/register flow

4. Set up email notification service for announcements

5. Implement affiliate link tracking integration

6. Set up commission payout system
