# Partner Email Notifications - Implementation Guide

## Overview

The partner ecosystem sends **6 types of automated emails** to keep partners engaged and informed about important updates in real-time.

## Notification Events

### 1. 🎉 Application Approved
**When:** Admin approves a partner application  
**Recipient:** New partner from PartnerApplication  
**Content:**
- Welcome message with program type
- Account activation status
- Link to login/dashboard
- Next steps guide

**API Trigger:** `PUT /api/admin/partners/applications/{id}` with `status: "approved"`

---

### 2. 📋 Deal Submitted
**When:** Referral partner submits a new deal/referral  
**Recipient:** Partner who submitted the deal  
**Content:**
- Deal title and details
- Estimated value and commission percentage
- Projected payout calculation
- Link to view deal pipeline
- Status: "Under Review"

**API Trigger:** `POST /api/dashboards/referral-partner/submit-referral`

---

### 3. 🎯 Deal Funded
**When:** Admin updates referral status to "funded"  
**Recipient:** Referral partner who submitted the deal  
**Content:**
- Deal approval confirmation
- Actual deal value (if different from estimate)
- Final commission amount
- Payment status indicator
- Processing timeline (3-5 business days)

**API Trigger:** `PUT /api/admin/partners/referrals/{id}` with `status: "funded"`

---

### 4. ✅ Commission Approved
**When:** Admin approves pending affiliate/referral earnings  
**Recipient:** Affiliate or referral partner  
**Content:**
- Commission amount approved
- Reason/breakdown if applicable
- Status: "Scheduled for Payout"
- Timeline (1-3 business days)
- Link to payout history

**API Trigger:** `POST /api/admin/partners/affiliates/{id}/approve-earnings`

---

### 5. 💰 Payout Processed
**When:** Admin marks commission/referral as paid  
**Recipient:** Affiliate or referral partner who earned the payout  
**Content:**
- Payout amount
- ACH transfer details
- Transaction ID
- Account confirmation instructions
- Estimated arrival time (1-2 business days)

**API Trigger:** `PUT /api/admin/partners/referrals/{id}` with `mark_paid: true`

---

### 6. 📢 Announcement Broadcast
**When:** Admin publishes announcement to partner groups  
**Recipient:** All active partners in target groups  
**Content:**
- Announcement title (with priority badge)
- Full announcement content
- Priority level (Normal/High/Urgent) with color coding
- Link to dashboards for more info

**API Trigger:** `POST /api/admin/partners/announcements` with `publish: true`

---

## Email Configuration

### Environment Variables

```env
# Email Provider (console, sendgrid, mailgun)
NOTIFY_PROVIDER=console

# Sender Configuration
NOTIFY_FROM_EMAIL=no-reply@jonche.com
NOTIFY_FROM_NAME=JONCHE

# SendGrid (if using SendGrid)
SENDGRID_API_KEY=your_api_key_here

# Mailgun (if using Mailgun)
MAILGUN_API_KEY=your_api_key_here
MAILGUN_DOMAIN=mail.jonche.com
```

### Providers

**Console** (Development)
- Marks emails as "sent" without delivering
- Safe for testing
- Default provider

**SendGrid** (Production)
- Enterprise-grade email delivery
- 99.99% deliverability
- Set `NOTIFY_PROVIDER=sendgrid` and add API key

**Mailgun** (Production)
- Reliable email service
- Set `NOTIFY_PROVIDER=mailgun` and add credentials

## API Integration

### Enqueue Emails
All partner notifications are automatically queued via the `enqueue_email()` function:

```python
from services.partner_notifications import PartnerNotifications

# Send application approved email
PartnerNotifications.notify_application_approved(
    email="partner@example.com",
    name="John Doe",
    program_type="affiliate_creators"
)

# Send deal submitted email
PartnerNotifications.notify_referral_submitted(
    email="partner@example.com",
    partner_name="Acme Corp",
    deal_title="Q1 2024 Partnership",
    estimated_value=50000,
    commission_pct=5.0
)

# Send deal funded email
PartnerNotifications.notify_deal_funded(
    email="partner@example.com",
    partner_name="Acme Corp",
    deal_title="Q1 2024 Partnership",
    actual_value=55000,
    commission_cents=275000
)

# Send commission approved email
PartnerNotifications.notify_commission_approved(
    email="affiliate@example.com",
    partner_name="Content Creator",
    commission_cents=10000,
    reason="Referral earnings for March"
)

# Send payout processed email
PartnerNotifications.notify_payout_processed(
    email="partner@example.com",
    partner_name="Strategic Partner",
    payout_cents=275000,
    payout_method="ACH",
    transaction_id="DEAL-1234"
)

# Send announcement email
PartnerNotifications.notify_announcement(
    email="partner@example.com",
    partner_name="Partner Name",
    announcement_title="Q2 Partner Summit",
    announcement_content="Join us for...",
    priority="high"
)
```

### Processing Queue

Emails are queued in the `notifications` table with status "queued". Admin can process them via:

```
POST /api/notifications/send?limit=25
```

This sends up to 25 queued emails using the configured provider.

**Manual Processing in Code:**
```python
from services.notifications import send_queued

# Send all queued emails (limit 50)
results = send_queued(limit=50)
print(f"Sent {results['sent']}, Failed {results['failed']}")
```

## Email Templates

All 6 email templates use:
- **Branded header** with dark gradient + gold accents (matches dashboard)
- **Responsive HTML** optimized for mobile and desktop
- **Clear CTAs** with dashboard links
- **Status indicators** with color coding
- **Professional footer** with links and branding

### Template Colors

| Status | Color | Hex |
|--------|-------|-----|
| Success/Approved | Green | #2e7d32 |
| Pending | Blue | #2196f3 |
| Urgent | Red | #f44336 |
| High Priority | Orange | #ff9800 |
| Normal | Dark | #000 |
| Accent | Gold | #ffd700 |

## Notification State Machine

```
Application:
new → contacted → approved → [Email] → partner_active
                → rejected

Deal:
submitted → [Email notifies partner]
         → under_review → approved → funded → [Email] → paid
                       → rejected

Commission:
pending → [Email when approved] → approved → scheduled → [Email when paid] → paid

Announcement:
draft → [Email broadcast] → published → archived
```

## Broadcasting Announcements

**Admin Endpoint:**
```
POST /api/admin/partners/announcements
{
  "title": "Q2 Partner Summit",
  "content": "Join us for...",
  "target_groups": ["affiliate_creators", "referral_network", "retail_alliance"],
  "priority": "high",
  "publish": true
}
```

**Broadcast Logic:**
- If `publish: true`, immediately sends emails to all active partners in target groups
- Target groups: `affiliate_creators`, `referral_network`, `retail_alliance`, `executives`
- Only sends to partners with `status = "active"`
- Prevents duplicate emails (one per partner per announcement)

## Testing & Development

### In Development
1. Set `NOTIFY_PROVIDER=console`
2. Emails are queued but not delivered
3. Check `notifications` table for "sent" status
4. View email content in database: `select * from notifications where status='sent' order by created_at desc;`

### Preview Templates
All templates are rendered by `PartnerEmailRenderer` class. To preview:

```python
from services.partner_notifications import PartnerEmailRenderer

# Get subject and HTML
subject, html = PartnerEmailRenderer.application_approved(
    name="John Doe",
    program_type="affiliate_creators"
)

# Save to file for browser preview
with open("test_email.html", "w") as f:
    f.write(html)
```

### Testing Production Providers

**SendGrid:**
```bash
export NOTIFY_PROVIDER=sendgrid
export SENDGRID_API_KEY=your_key_here
curl -X POST http://localhost:5001/api/notifications/send
```

**Mailgun:**
```bash
export NOTIFY_PROVIDER=mailgun
export MAILGUN_API_KEY=your_key_here
export MAILGUN_DOMAIN=mail.jonche.com
curl -X POST http://localhost:5001/api/notifications/send
```

## Monitoring & Troubleshooting

### Check Pending Emails
```sql
SELECT * FROM notifications WHERE status='queued' ORDER BY created_at;
```

### Failed Emails
```sql
SELECT id, recipient_email, subject, error, created_at 
FROM notifications 
WHERE status='failed' 
ORDER BY created_at DESC 
LIMIT 20;
```

### Email Statistics Dashboard
```
GET /api/notifications/
```

Returns list of all notifications with status breakdown.

### Common Issues

| Issue | Solution |
|-------|----------|
| Emails not sending | Check `NOTIFY_PROVIDER` env var or queue processing |
| Wrong sender email | Verify `NOTIFY_FROM_EMAIL` in environment |
| SendGrid fails | Confirm API key in `SENDGRID_API_KEY` |
| Mailgun fails | Check `MAILGUN_API_KEY` and `MAILGUN_DOMAIN` |
| HTML rendering issues | Test in Gmail, Outlook, mobile clients |

## Analytics

Partner emails are tagged with `notif_type` for tracking:
- `partner_app_approved`
- `partner_referral_submitted`
- `partner_deal_funded`
- `partner_commission_approved`
- `partner_payout_processed`
- `partner_announcement`

Use to track engagement and delivery rates:
```sql
SELECT notif_type, COUNT(*) as total, 
       SUM(CASE WHEN status='sent' THEN 1 ELSE 0 END) as sent,
       SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
FROM notifications
WHERE created_at > NOW() - INTERVAL 7 DAY
GROUP BY notif_type;
```

## Integration Checklist

- [x] Email service module created (`services/partner_notifications.py`)
- [x] 6 email templates implemented
- [x] Admin endpoints integrated (applications, earnings, referrals, announcements)
- [x] Partner dashboard endpoints integrated (referral submission)
- [x] Queued email system (existing `Notification` model)
- [x] Announcement broadcasting with group targeting
- [x] Helper function for multi-recipient broadcasts

## Next Steps (Phase 4)

1. **Email Analytics**
   - Track open rates via pixel tracking
   - Link clicks in CTAs
   - Bounce rate monitoring

2. **Unsubscribe & Preferences**
   - Per-partner email preference page
   - Opt-out for specific notification types
   - Frequency controls (daily digest vs real-time)

3. **Admin Email**
   - Alerts when deals exceed thresholds
   - Daily summary of new applications
   - Weekly revenue/payout reports

4. **Scheduled Emails**
   - 24h reminder before deal deadline
   - Weekly earnings summary
   - Monthly payout reconciliation

5. **SMS Notifications** (optional)
   - Urgent announcement alerts
   - High-priority deal status updates
   - Payout confirmation SMS

---

**Implementation Date:** 2024  
**Status:** Phase 3 Complete - Email Notifications Active  
**Next:** Phase 4 - Analytics & Preferences
