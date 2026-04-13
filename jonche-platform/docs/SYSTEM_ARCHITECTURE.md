# Partner Ecosystem - System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    JONCHE PARTNER ECOSYSTEM v1.0                        │
│                          (Phases 1-3 Complete)                          │
└─────────────────────────────────────────────────────────────────────────┘

                          ┌──────────────────────┐
                          │   ADMIN PORTAL       │
                          │  /admin/dashboards   │
                          └──────────┬───────────┘
                                     │
                ┌────────────────────┼────────────────────┐
                │                    │                    │
        ┌───────▼────────┐   ┌──────▼─────────┐  ┌──────▼─────────┐
        │  Applications  │   │  Partner Mgmt  │  │  Announcements │
        │   (auto-email) │   │   (auto-email) │  │   (broadcast)  │
        └────────────────┘   └────────────────┘  └────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        PARTNER DASHBOARDS (4 Types)                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   AFFILIATES │  │  REFERRALS   │  │   RETAIL     │  │ EXECUTIVES │ │
│  │   Dashboard  │  │   Dashboard  │  │   Dashboard  │  │ Dashboard  │ │
│  │              │  │              │  │              │  │            │ │
│  │ • Earnings   │  │ • Deal Pipe  │  │ • Allocations│  │ • Territory│ │
│  │ • Referrals  │  │ • Submit Deal│  │ • Orders     │  │ • Deals    │ │
│  │ • Links      │  │ • Commission │  │ • Campaigns  │  │ • Announce │ │
│  │ • Messages   │  │ • Messages   │  │ • Messages   │  │ • Messages │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
│                                                                          │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼───────┐   ┌────▼──────┐   ┌─────▼──────┐
    │ Auth Login │   │ View Data  │   │   Submit   │
    │ Endpoints  │   │ Endpoints  │   │  Endpoints │
    └────┬───────┘   └────┬──────┘   └─────┬──────┘
         │                │                │
         └────────────────┼────────────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │    API LAYER        │    /api/dashboards  │
    │   (Flask Routes)    │  /api/admin/        │
    │                     │                     │
    │  • partner_         │  • admin_           │
    │    dashboards.py    │    partners.py      │
    │                     │                     │
    └─────────────────────┼─────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────▼──────────┐ ┌──▼──────┐ ┌──────▼─────┐
    │   DATABASES   │ │ SERVICES │ │   MODELS   │
    │               │ │          │ │            │
    │ 8 New Models: │ │Notify    │ │ • Affiliate│
    │               │ │(email)   │ │ • Referral │
    │ 1. Affiliate  │ │          │ │ • Retail   │
    │ 2. Referral   │ │          │ │ • Executive│
    │ 3. Retail     │ │          │ │ • Earnings │
    │ 4. Executive  │ │          │ │ • Referral │
    │ 5. Earning    │ │          │ │ • Message  │
    │ 6. Referral   │ │          │ │ • Announce │
    │ 7. Message    │ │          │ │            │
    │ 8. Announce   │ │          │ │            │
    └───────────────┘ └──────────┘ └────────────┘
```

## Workflow: From Application to Payout

```
PARTNER SIGNUP & ONBOARDING
──────────────────────────────────────────────────────────────────
1. Partner fills application form (web)
   ↓
2. Admin reviews application via /admin/dashboards
   ↓
3. Admin clicks "Approve" → Status changes to "approved"
   ↓
4. 🔔 SYSTEM: Email "Application Approved" sent automatically
   ↓
5. Partner receives email with dashboard login link
   ↓


ONGOING ENGAGEMENT
──────────────────────────────────────────────────────────────────

FOR AFFILIATE CREATORS:
─────────────────────
1. Customer purchases via partner's referral link
   ↓
2. System creates AffiliateEarning (status: "pending")
   ↓
3. Admin reviews pending earnings
   ↓
4. Admin clicks "Approve Earnings"
   ↓
5. 🔔 SYSTEM: Email "Commission Approved" sent
   ↓
6. Partner sees commission in "Ready for Payout" section
   ↓
7. Admin marks as "Paid"
   ↓
8. 🔔 SYSTEM: Email "Payout Processed" sent with details
   ↓
9. Partner receives payment


FOR REFERRAL PARTNERS:
─────────────────────
1. Partner submits deal via dashboard
   ↓
2. 🔔 SYSTEM: Email "Deal Submitted" sent (confirmation)
   ↓
3. Admin reviews deal in dashboard
   ↓
4. Admin updates status → "approved" → "funded"
   ↓
5. 🔔 SYSTEM: Email "Deal Funded" sent with commission amount
   ↓
6. Admin marks deal as "paid"
   ↓
7. 🔔 SYSTEM: Email "Payout Processed" sent
   ↓
8. Partner receives payment


ANNOUNCEMENTS & COMMUNICATIONS
──────────────────────────────
1. Admin creates announcement in /admin/dashboards
   ↓
2. Admin selects target groups (affiliate_creators, referral_network, etc)
   ↓
3. Admin clicks "Publish"
   ↓
4. 🔔 SYSTEM: Email sent to ALL active partners in target groups
   ↓
5. Partners receive branded announcement email with link to dashboard
```

## Data Flow: Email Notifications

```
                    API ENDPOINT TRIGGERED
                             │
                    (e.g., PUT /admin/partners/applications/123)
                             │
                    ┌────────▼────────┐
                    │   APPLICATION   │
                    │  LOGIC RUNS      │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   (Status       (Deal          (Earnings         (Announcement
    Updated)     Submitted)      Approved)        Published)
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────────────────────────────────────────────────┐
   │  PARTNER NOTIFICATIONS SERVICE                      │
   │  (services/partner_notifications.py)                │
   │                                                     │
   │  decide_which_email_to_send()                      │
   │  └─→ application_approved()                        │
   │  └─→ referral_submitted()                          │
   │  └─→ deal_funded()                                 │
   │  └─→ commission_approved()                         │
   │  └─→ payout_processed()                            │
   │  └─→ announcement()                                │
   └────────────────┬────────────────────────────────────┘
                    │
        ┌───────────▼───────────┐
        │  EMAIL RENDERER       │
        │  (Generate HTML)      │
        │  + Branding           │
        │  + Status Indicators  │
        │  + CTAs               │
        │  + Footer             │
        └───────────┬───────────┘
                    │
   ┌────────────────▼────────────────┐
   │  ENQUEUE_EMAIL()                │
   │  (Add to notifications table)    │
   │  Status: "queued"               │
   │  ↓ Save to DB                   │
   └────────────────┬────────────────┘
                    │
        ┌───────────▼──────────────┐
        │   NOTIFICATION QUEUE     │
        │   (notifications table)   │
        │                          │
        │   ├─ queued: 25          │
        │   ├─ sent: 1024          │
        │   └─ failed: 3           │
        └───────────┬──────────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
MANUAL TRIGGER  OR  SCHEDULED JOB  IMMEDIATE
curl /notify/send  (future)      (in code)
    │               │               │
    └───────────────┼───────────────┘
                    │
        ┌───────────▼──────────────┐
        │  EMAIL PROVIDER          │
        │  (select based on env)    │
        │                          │
        │  ├─ console (dev)        │
        │  ├─ sendgrid (prod)      │
        │  └─ mailgun (prod)       │
        └───────────┬──────────────┘
                    │
        ┌───────────▼──────────────┐
        │  EMAIL DELIVERED         │
        │                          │
        │  Partner inbox ✉️        │
        │                          │
        │  Status: "sent"          │
        │  Timestamp: recorded     │
        └──────────────────────────┘
```

## Component Interactions

### Admin Panel → Emails

```
Admin Action                Email Trigger               Recipient
─────────────────────────────────────────────────────────────────
Approve Application    →   Application Approved    →   New Partner
Auto-create Account    →   Account Created         →   Admin only
Update Earnings        →   Commission Approved     →   Affiliate
Mark as Paid           →   Payout Processed        →   Partner
Update Referral Status →   Deal Funded             →   Ref Partner
Publish Announcement   →   Announcements Broadcast →   Partner Groups
```

### Partner Dashboard → Emails

```
Partner Action             Email Trigger              Recipient
──────────────────────────────────────────────────────────────
Submit Referral        →   Deal Submitted        →   Partner (confirm)
Update Profile         →   (no email)            →   —
View Messages          →   (no email)            →   —
Download Assets        →   (no email)            →   —
```

## Database Schema Relationships

```
┌──────────────────────────────────────┐
│     AFFILIATE_ACCOUNT                │
├──────────────────────────────────────┤
│ id (PK)                              │
│ email (UNIQUE)                       │
│ password_hash                        │
│ display_name                         │
│ commission_rate_percent              │
│ total_earnings_cents                 │
│ pending_earnings_cents               │
│ status (active/suspended/inactive)   │
└──────────────────────┬─────────────────┘
                       │ 1:N
                       │
                       ▼
        ┌──────────────────────────────┐
        │  AFFILIATE_EARNING           │
        ├──────────────────────────────┤
        │ id (PK)                      │
        │ affiliate_id (FK)            │
        │ order_id (FK)                │
        │ commission_cents             │
        │ status (pending/approved/paid)│
        └──────────────────────────────┘

┌──────────────────────────────────────┐
│  REFERRAL_PARTNER_ACCOUNT            │
├──────────────────────────────────────┤
│ id (PK)                              │
│ email (UNIQUE)                       │
│ password_hash                        │
│ company_name                         │
│ contact_name                         │
│ tier (bronze/silver/gold)            │
│ total_deal_value_cents               │
│ pending_commission_cents             │
│ status                               │
└──────────────────────┬─────────────────┘
                       │ 1:N
                       │
                       ▼
        ┌──────────────────────────────┐
        │  PARTNER_REFERRAL            │
        ├──────────────────────────────┤
        │ id (PK)                      │
        │ referral_partner_id (FK)     │
        │ title                        │
        │ estimated_value_cents        │
        │ actual_value_cents           │
        │ commission_cents             │
        │ status (submitted..funded)   │
        └──────────────────────────────┘

┌──────────────────────────────────────┐
│  PARTNER_MESSAGE (Multi-recipient)   │
├──────────────────────────────────────┤
│ id (PK)                              │
│ affiliate_id (FK) - nullable         │
│ referral_partner_id (FK) - nullable  │
│ retail_partner_id (FK) - nullable    │
│ executive_id (FK) - nullable         │
│ subject                              │
│ body                                 │
│ is_read (boolean)                    │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│  NOTIFICATIONS (Email Queue)         │
├──────────────────────────────────────┤
│ id (PK)                              │
│ recipient_email                      │
│ recipient_name                       │
│ subject                              │
│ body_html                            │
│ notif_type (partner_*)               │
│ status (queued/sent/failed)          │
│ sent_at (timestamp)                  │
│ error (if failed)                    │
└──────────────────────────────────────┘
```

## Event State Machines

### Application Lifecycle
```
NEW → CONTACTED → APPROVED ──[Email]──▶ Partner Receives
                 ↘ REJECTED
                   [No Email]
```

### Deal Lifecycle
```
SUBMITTED ──[Email]──▶ Partner Confirmed
    ↓
UNDER_REVIEW
    ↓
APPROVED → FUNDED ──[Email]──▶ Partner Notified
    ↘ REJECTED
      [Admin sees]
```

### Commission Lifecycle
```
PENDING ──[Email when Approved]──▶ APPROVED ──[Email when Paid]──▶ PAID
                                       ↓
                                    Ready for payout
```

## URLs & Endpoints

### Admin Portal
```
/admin/dashboards              Admin dashboard (protected)
/api/admin/partners/*          All admin endpoints
```

### Partner Dashboards
```
/affiliate_dashboard.html      Affiliate portal
/referral_partner_dashboard.html Referral portal
/retail_partner_dashboard.html Retail portal
/executive_dashboard.html      Executive portal
/api/dashboards/*              All partner endpoints
```

### Email Queue
```
GET /api/notifications/        List all notifications
POST /api/notifications/send   Process queued emails (max 25)
```

## Configuration

### Environment Variables
```
NOTIFY_PROVIDER=console|sendgrid|mailgun
NOTIFY_FROM_EMAIL=no-reply@jonche.com
NOTIFY_FROM_NAME=JONCHE
SENDGRID_API_KEY=...           (if using SendGrid)
MAILGUN_API_KEY=...            (if using Mailgun)
MAILGUN_DOMAIN=...             (if using Mailgun)
```

### Email Providers
```
Console:  Dev only, no actual delivery
SendGrid: 99.99% deliverability, webhook support
Mailgun:  Reliable, affordable, flexible
```

## Performance Considerations

```
Queries:
├─ All queries use pagination (default: 50/page)
├─ Foreign key lookups indexed
├─ Status filters indexed
└─ N+1 queries avoided with joins

Email:
├─ Queue-based (non-blocking)
├─ Batch processing (25-50 at a time)
├─ Retry logic for failures
└─ No rate limiting (provider handles)

Database:
├─ Separate tables per entity type
├─ Lazy loading for relationships
├─ Timestamps on all records
└─ Proper cascading deletes
```

---

**Architecture Version:** 1.0  
**Phases Implemented:** 1, 2, 3 (Admin, Dashboards, Email)  
**Status:** Production Ready ✅
