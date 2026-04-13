# Partner Email Notifications - Quick Start

## TL;DR

Email notifications are **automatically sent** from the partner management system. No extra setup needed beyond environment variables.

## 1-Minute Setup

```bash
# Set in your .env file
export NOTIFY_PROVIDER=console    # dev: logs only, doesn't send
export NOTIFY_FROM_EMAIL=no-reply@jonche.com
export NOTIFY_FROM_NAME=JONCHE

# For production with SendGrid:
export NOTIFY_PROVIDER=sendgrid
export SENDGRID_API_KEY=your_actual_key_here
```

## What Sends Automatically

| Event | Trigger | Recipient |
|-------|---------|-----------|
| ✅ Application Approved | Admin clicks "approve" | New partner |
| 📋 Deal Submitted | Partner submits referral | That partner |
| 🎯 Deal Funded | Admin marks deal "funded" | Partner |
| ✅ Commission Approved | Admin approves earnings | Affiliate/Partner |
| 💰 Payout Processed | Admin marks as "paid" | Partner |
| 📢 Announcement | Admin hits "publish" | All in target groups |

## Examples

### Approve an Application
```bash
curl -X PUT http://localhost:5001/api/admin/partners/applications/123 \
  -H "Content-Type: application/json" \
  -d '{"status": "approved"}'
# → Email sent to applicant automatically
```

### Submit a Deal
```bash
curl -X POST http://localhost:5001/api/dashboards/referral-partner/submit-referral \
  -H "Content-Type: application/json" \
  -d '{
    "referral_type": "direct",
    "title": "Q1 Partnership",
    "estimated_value_cents": 50000,
    "commission_percent": 5.0
  }'
# → Confirmation email sent to partner automatically
```

### Broadcast Announcement
```bash
curl -X POST http://localhost:5001/api/admin/partners/announcements \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Q2 Partner Summit",
    "content": "Join us for our partner summit...",
    "target_groups": ["affiliate_creators", "referral_network"],
    "priority": "high",
    "publish": true
  }'
# → Emails sent to all active affiliates and referral partners
```

## Monitoring

### Check What Was Sent
```bash
# List all notifications
curl http://localhost:5001/api/notifications/

# You'll see: status (sent/queued/failed), recipient, subject, timestamp
```

### Process Queued Emails
```bash
# Send up to 25 queued emails
curl -X POST "http://localhost:5001/api/notifications/send?limit=25"

# Check result:
{
  "sent": 18,
  "failed": 0,
  "queued_remaining": 3
}
```

## Testing

### Dev Environment
1. Set `NOTIFY_PROVIDER=console`
2. Make a change (approve app, submit deal, etc.)
3. Check database: `select * from notifications order by created_at desc limit 5;`
4. You'll see status "sent" but no actual email delivered

### View Email Content (HTML)
```bash
sqlite3 jonche.db "SELECT body_html FROM notifications WHERE id=123;" > email.html
open email.html  # View in browser
```

### SendGrid Sandbox
```bash
export NOTIFY_PROVIDER=sendgrid
export SENDGRID_API_KEY=SG.xxx...
# Use sandbox recipient: test@example.com 
# Email will be sent but caught by SendGrid sandbox
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Emails not sending | Check `NOTIFY_PROVIDER` env var, run `/api/notifications/send` endpoint |
| Wrong sender name | Verify `NOTIFY_FROM_NAME` env var |
| SendGrid says "Unauthorized" | Check `SENDGRID_API_KEY` is correct |
| Emails sent but not arriving | Check recipient email is valid, test with SendGrid sandbox |
| HTML rendering broken | Email templates use inline CSS (no external stylesheets) |

## Common Patterns

### Approve Application & Send Email
```python
from routes.admin_partners import admin_partners_bp
from db.models import PartnerApplication

# Already integrated! When you do:
# PUT /api/admin/partners/applications/123 with status="approved"
# Email is sent automatically
```

### Broadcast to Specific Groups
```bash
# Send to just referral partners
curl -X POST http://localhost:5001/api/admin/partners/announcements \
  -d '{"title":"New Deal","content":"...","target_groups":["referral_network"],"publish":true}'

# Send to all groups
curl -X POST http://localhost:5001/api/admin/partners/announcements \
  -d '{"title":"New Deal","content":"...","target_groups":["affiliate_creators","referral_network","retail_alliance","executives"],"publish":true}'
```

### View Email History for One Partner
```sql
SELECT subject, status, sent_at, created_at 
FROM notifications 
WHERE recipient_email='partner@company.com' 
ORDER BY created_at DESC 
LIMIT 20;
```

## Template Preview

All 6 templates are in `services/partner_notifications.py`:
- `application_approved()` - Welcome email
- `referral_submitted()` - Deal submission confirmation
- `deal_funded()` - Commission earned
- `commission_approved()` - Payment ready
- `payout_processed()` - Payment sent
- `announcement()` - Group broadcast

Each returns `(subject, html_body)`.

## Production Checklist

- [x] Code integrated (auto-sending on key events)
- [x] Email templates designed and tested
- [x] Queue system working (notifications table)
- [ ] Choose email provider (SendGrid or Mailgun) ← DO THIS
- [ ] Set API keys in production environment
- [ ] Test with real email provider
- [ ] Set up email monitoring/dashboards
- [ ] Configure bounce/complaint handling

## FAQ

**Q: Can I customize email templates?**  
A: Yes! Edit `services/partner_notifications.py` → `PartnerEmailRenderer` class

**Q: Do emails retry if sending fails?**  
A: Yes, they stay in "queued" status. Re-run `/api/notifications/send` to retry

**Q: Can partners unsubscribe?**  
A: Not yet - Phase 4 feature. Currently all active partners get emails

**Q: How many emails can I send?**  
A: No limit! Queue supports unlimited. Provider APIs have rate limits (SendGrid: 100/second)

**Q: Can I schedule emails?**  
A: Not yet. They send immediately. Phase 4 will add scheduling

**Q: Test email address?**  
A: Use your own. For SendGrid sandbox: test@example.com

---

**For detailed docs:** See [PARTNER_EMAIL_NOTIFICATIONS.md](PARTNER_EMAIL_NOTIFICATIONS.md)
