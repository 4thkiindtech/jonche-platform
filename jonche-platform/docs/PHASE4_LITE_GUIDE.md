# Phase 4 Lite - Manual Payout System
## Implementation Guide

**Status**: ✅ Production Ready  
**Release Date**: April 13, 2026  
**Breaking Changes**: None - full backward compatibility

---

## Overview

Phase 4 Lite is a **manual payout approval system** that enables immediate payouts to partners without full Stripe Connect automation. Perfect for bootstrapping partner payments while maintaining administrative control.

### Three-Tier Payout Schedule

| Partner Type | Frequency | Minimum Threshold | Launch Cost |
|---|---|---|---|
| **Affiliates** | Monthly (last business day) | $100 | Volume-driven |
| **Referral Partners** | Bi-weekly (1st & 15th) | $500 | High-value deals |
| **Executives** | Weekly (Monday) | $0 (none) | Fast closers |

---

## Installation Steps

### 1. Apply Database Migration

```bash
# Generate and apply Flask-Migrate migration
cd apps/api
flask db migrate -m "phase4_lite_payout_system"
flask db upgrade
```

**What This Creates**:
- `payout_schedules` - Schedule configuration table
- `payout_batches` - Grouped payouts per cycle
- `commission_payouts` - Individual payouts to partners
- `payment_methods` - Partner ACH/Zelle/Wire routing
- `payout_logs` - Immutable audit trail

### 2. Initialize Payout Schedules

```bash
# Run from apps/api directory
python -c "from scripts.init_payout_schedules import init_payout_schedules; init_payout_schedules()"
```

**Output**:
```
✓ Payout schedules initialized:
  - Affiliate: Monthly (last business day, $100 min)
  - Referral Partner: Bi-weekly (1st & 15th, $500 min)
  - Executive: Weekly (Monday, no minimum)
```

### 3. Verify Installation

```bash
curl -H "X-Admin-ID: 1" http://localhost:5001/api/admin/payouts/batches
```

Expected response:
```json
{
  "total": 0,
  "batches": []
}
```

---

## API Reference

### Partner Earnings Summary
```
GET /api/partners/<partner_type>/<partner_id>/earnings
```

**Response**:
```json
{
  "partner_id": 42,
  "partner_type": "affiliate",
  "partner_email": "creator@example.com",
  "pending_cents": 15000,
  "pending_dollars": 150.00,
  "approved_cents": 5000,
  "approved_dollars": 50.00,
  "projected_cents": 20000,
  "projected_dollars": 200.00,
  "meets_minimum": true,
  "minimum_threshold_cents": 10000,
  "minimum_threshold_dollars": 100.00,
  "next_payout_date": "2026-04-30T23:59:59"
}
```

### List Pending Payouts
```
GET /api/admin/payouts/pending?partner_type=affiliate&status=pending
Header: X-Admin-ID: <admin_id>
```

### Create Payout Batch (Manual)
```
POST /api/admin/payouts/batch/create
Body: {
  "partner_type": "affiliate"
}
Header: X-Admin-ID: <admin_id>
```

**Response**:
```json
{
  "success": true,
  "batch": {
    "id": 1,
    "batch_number": "BATCH-A1B2C3",
    "partner_type": "affiliate",
    "total_amount_dollars": 2450.00,
    "payout_count": 12,
    "status": "pending"
  },
  "payouts_created": 12
}
```

### Approve Batch
```
POST /api/admin/payouts/batch/<batch_id>/approve
Header: X-Admin-ID: <admin_id>
```

### Record Manual Payment
```
POST /api/admin/payouts/<payout_id>/payment
Header: X-Admin-ID: <admin_id>
Body: {
  "payment_method": "ach",
  "payment_reference": "ACH-REF-12345"
}
```

Valid payment methods: `ach`, `zelle`, `wire`, `check`, `stripe`

---

## Workflow: Step-by-Step

### Week 1: Setup & Testing

```
1. Run migrations
2. Initialize schedules
3. Create test affiliate earnings
4. Create test payout batch
5. Approve batch
6. Record sample payment
```

### Ongoing: Monthly Cycle

```
AFFILIATE MONTHLY (Last Monday of Month)
├─ 9:00 AM: Collect all pending earnings ≥ $100
├─ 10:00 AM: Create batch
├─ 11:00 AM: Review in admin dashboard
├─ 12:00 PM: Approve batch
├─ 2:00 PM: Make payments (ACH/Zelle)
├─ 3:00 PM: Log payment reference
└─ 4:00 PM: Send confirmation emails

REFERRAL PARTNER BI-WEEKLY (1st & 15th)
├─ 2:00 AM: Collect all invoiced deals ≥ $500
├─ 2:30 AM: Create batch
├─ Business hours: Admin review & approve
├─ Payment: Process manually (ACH/Wire)
└─ Log: Record payment details

EXECUTIVE WEEKLY (Every Monday)
├─ 6:00 AM: Collect all pending deals
├─ 6:30 AM: Create batch (no minimum)
├─ 8:00 AM: Approve & process
├─ Payment: ACH transfer
└─ Notification: Email confirmation
```

---

## Code Examples

### Calculate Projected Earnings (From Service)

```python
from services.payout_calculator import PayoutCalculator

# Recalculate all projected earnings
PayoutCalculator.calculate_all_projected_earnings()

# Get specific partner's pending
pending = PayoutCalculator.calculate_affiliate_pending(affiliate_id=42)
print(f"Pending earnings: ${pending/100:.2f}")
```

### Create Batch Programmatically

```python
from services.payout_calculator import BatchProcessor
from db import db

# Create affiliate batch
batch = BatchProcessor.create_affiliate_batch()

if batch:
    print(f"Created batch {batch.batch_number}")
    print(f"Payouts: {batch.payout_count} | Total: ${batch.total_amount_cents/100:.2f}")
    db.session.commit()
```

### Check Minimum Threshold

```python
from services.payout_calculator import PayoutValidator

is_ready = PayoutValidator.check_partner_meets_minimum(
    partner_type="affiliate",
    partner_id=42
)
```

---

## Database Schema

### PayoutSchedule
```sql
- id (int, PK)
- partner_type (str, unique): affiliate, referral_partner, executive
- frequency (str): monthly, biweekly, weekly
- day_of_cycle (str): 1st, 15th, last_business_day, monday
- minimum_payout_cents (int): $0, $100, $500
- hold_period_days (int): 0 (future use)
- enabled (boolean): activate/deactivate schedule
```

### PayoutBatch
```sql
- id (int, PK)
- batch_number (str, unique): BATCH-XXXXXX
- partner_type (str): affiliate, referral_partner, executive
- cycle_date (datetime): when batch was created
- total_amount_cents (int): sum of all payouts
- payout_count (int): number of payouts
- status (str): pending → approved → paid
- approved_by_admin_id (int, FK): which admin approved
- approved_at (datetime): when approved
- paid_at (datetime): when payment was recorded
```

### CommissionPayout
```sql
- id (int, PK)
- batch_id (int, FK): which batch
- partner_type (str): affiliate, referral_partner, executive
- partner_id (int): the partner receiving payment
- partner_email (str): for notifications
- source_ids (json): [earning_id, earning_id] or [referral_id]
- gross_amount_cents (int): before fees
- payment_fee_cents (int): ACH, processing, etc.
- net_amount_cents (int): after fees
- status (str): pending → approved → paid
- payment_method (str): ach, zelle, wire, check, stripe
- payment_reference (str): confirmation #, ref #, etc.
- paid_at (datetime): when paid
```

### PayoutLog
```sql
- id (int, PK)
- batch_id (int, FK, nullable)
- payout_id (int, FK, nullable)
- action (str): batch_created, batch_approved, payment_recorded, etc.
- details (json): { "reason": "...", "amount_cents": 12345 }
- actor_type (str): admin, system, partner
- actor_id (int): which admin/system took action
```

---

## Field Changes to Existing Models

**No modifications to existing models.** Three new optional fields added to partner accounts (backward-compatible):

### AffiliateAccount
- `pending_commission_cents` (int, default=0): Sum of pending payouts

### ReferralPartnerAccount
- `pending_commission_cents` (int, default=0): Sum of pending payouts

### ExecutiveAccount
- `pending_commission_cents` (int, default=0): Sum of pending payouts

These fields are **read-only** and calculated by the service. Existing records initialize to 0.

---

## Payment Method Configuration

Partners store preferred payment routing:

```python
# Example: Add ACH payment method for affiliate
payment_method = PaymentMethod(
    partner_type="affiliate",
    partner_id=42,
    method_type="ach",
    recipient_name="John Creator",
    bank_name="Chase",
    account_type="checking",
    routing_number="021000021",
    account_number_encrypted="[encrypted]",
    account_number_last4="5432",
    is_primary=True,
    verified=True
)
db.session.add(payment_method)
db.session.commit()
```

---

## Admin Dashboard Integration

### Required Components

1. **Earnings Summary Widget**
   - Show pending by partner type
   - Show next payout date
   - Show minimum threshold status

2. **Payout Batch Manager**
   - List pending batches
   - Approve/reject with notes
   - Filter by partner type, status, date

3. **Payment Recorder**
   - Select batch or payout
   - Enter payment method & reference
   - Mark as paid

4. **Audit Log Viewer**
   - All batch operations
   - Payment confirmations
   - Actor (admin/system) tracking

### Key Metrics to Display

```
- Pending payouts: ${amount} to {count} partners
- Next payout date: {date}
- Minimum thresholds:
  - Affiliate: $100/month
  - Referral: $500/biweekly
  - Executive: Immediate
- Monthly payout volume: ${historical_avg}
- Partner payment success rate: {percent}%
```

---

## Email Templates

### New Payout Notification
```
Subject: Your Monthly Commission Payout - {date}

Hi {partner_name},

Your commission of ${amount} has been approved and will be paid on {payout_date}.

Details:
- Earnings Period: {start_date} to {end_date}
- Gross Commission: ${gross}
- Payment Method: {method}
- Status: Approved

Questions? Contact support@jonche.com

Best regards,
Jonche Team
```

### Payment Confirmation
```
Subject: Payment Received - {confirmation_ref}

Hi {partner_name},

Your commission payment of ${amount} has been processed.

Details:
- Amount: ${amount}
- Reference #: {ref}
- Payment Method: {method}
- Paid Date: {date}

Check your account in 1-2 business days.

Best regards,
Jonche Team
```

---

## Troubleshooting

### Q: Batch won't create - no payouts
**A**: Check if partners meet minimum threshold:
```python
from services.payout_calculator import PayoutValidator
result = PayoutValidator.check_partner_meets_minimum("affiliate", 42)
```

### Q: Need to change minimum threshold
**A**: Update PayoutSchedule table:
```python
from db.models import PayoutSchedule
schedule = PayoutSchedule.query.filter_by(partner_type="affiliate").first()
schedule.minimum_payout_cents = 15000  # $150
db.session.commit()
```

### Q: How to view audit trail
**A**: Query PayoutLog:
```python
from db.models import PayoutLog
logs = PayoutLog.query.filter_by(batch_id=1).order_by(PayoutLog.created_at.desc()).all()
for log in logs:
    print(f"{log.created_at} - {log.action} by {log.actor_type}#{log.actor_id}")
```

### Q: Payout stuck in "approved" status
**A**: Record payment manually:
```bash
POST /api/admin/payouts/{payout_id}/payment
{
  "payment_method": "ach",
  "payment_reference": "ACH-20260413-12345"
}
```

---

## Security & Compliance

✅ **No Financial Data in Logs**: Payment reference only (not account numbers)  
✅ **Encrypted ACH Data**: Account numbers encrypted in transit & at rest  
✅ **Audit Trail**: Immutable log of all actions with actor tracking  
✅ **Admin-Only Approval**: All payouts require manual human review  
✅ **RBAC Ready**: Check X-Admin-ID header on sensitive endpoints  

---

## Next Steps: Phase 5

- [ ] Stripe Connect automation (replace manual ACH)
- [ ] Automatic tax withholding (1099-NEC generation)
- [ ] Multi-day hold periods for disputes
- [ ] Partner self-service payment method setup
- [ ] Automated batch processing on schedule (Celery)

---

## Support

Deployment Questions? → [DEPLOY.md](../DEPLOY.md)  
API Debugging? → Check PayoutLog table  
Partner Issues? → Review pending earnings & batch status
