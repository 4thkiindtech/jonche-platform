# Phase 4 Quick Reference Guide

## 📋 Commission Schedule at a Glance

### Affiliate Creators
- **Rate**: 10% (starter) → 25% (premium)
- **Hold Period**: 7 days
- **Payout**: Monthly (last Monday)
- **Min Threshold**: $1.00
- **Trigger**: Order completed

### Referral Partners  
- **Rate**: 3-12% (deal-dependent)
- **Hold Period**: 60 days
- **Payout**: Bi-weekly (1st & 15th)
- **Min Threshold**: $5.00
- **Trigger**: Deal invoiced by admin

### Retail Partners
- **Rate**: 15-25% (volume-based)
- **Hold Period**: None (auto-approved)
- **Payout**: Monthly (high-volume: bi-weekly)
- **Min Threshold**: $10.00
- **Trigger**: Order fulfillment complete

### Executives
- **Rate**: 2-7% (territory-based)
- **Hold Period**: None (auto-approved)
- **Payout**: Weekly (every Monday)
- **Min Threshold**: $25.00
- **Trigger**: Deal approved by admin

---

## 🔄 Workflow Summary

```
ELIGIBLE EARNING → CALCULATE → AGGREGATE → CREATE BATCH → ADMIN REVIEW → PROCESS PAYMENT → COMPLETE

1. IDENTIFY ELIGIBLE
   • Status = approved/invoiced
   • Hold period expired (or N/A)
   • Above minimum threshold
   • Created within payout cycle

2. CALCULATE 
   • Sum commissions per partner
   • Deduct fees (2-3%)
   • Calculate taxes (if >$600)
   • Apply holds/disputes

3. AGGREGATE
   • Group by payee + type
   • Create CommissionPayout record
   • Set payment_method (Stripe/ACH/Check)
   • Update batch metrics

4. CREATE BATCH
   • Generate batch_number
   • Set scheduled_payout_date
   • Status = "pending"
   • Await admin review

5. ADMIN REVIEW
   • Review payout breakdown
   • Can remove/adjust individual payouts
   • Can reject entire batch
   • Approve for processing

6. PROCESS PAYMENT
   • Route to appropriate processor (Stripe/ACH)
   • Send payment
   • Update payment_status = "processing"
   • Create payment receipt

7. COMPLETE
   • Track confirmation from processor
   • Send partner notification email
   • Update payment_status = "paid"
   • Mark batch complete
   • Generate audit log

```

---

## 💾 Database Tables

### New Tables (Add to models.py)

| Table | Purpose |
|-------|---------|
| `PayoutSchedule` | Recurring payout definitions (weekly/bi-weekly/monthly) |
| `PayoutBatch` | Groups of payouts created for one cycle |
| `CommissionPayout` | Individual payout to one partner |
| `PayoutReport` | Generated reports (CSV, JSON, 1099, etc.) |

### Updated Columns (Existing Tables)

Add to `AffiliateEarning`:
- `payout_id` - Links to CommissionPayout
- `hold_reason` - Why held (if disputed)
- `hold_until` - Release date

Add to `PartnerReferral`:
- `payout_id` - Links to CommissionPayout
- `invoice_date` - When admin invoiced deal
- `invoice_number` - For accounting

---

## 🔧 Implementation Checklist

### Week 1: Database
- [ ] Create migration file
- [ ] Add PayoutSchedule, PayoutBatch, CommissionPayout models
- [ ] Add foreign key columns to existing models
- [ ] Create indexes on (schedule_id, status), (batch_id, payee_id)
- [ ] Run: `flask db migrate && flask db upgrade`

### Week 2: Services
- [ ] Create `payout_processor.py` (PayoutCalculator, BatchProcessor)
- [ ] Create `payout_dispatcher.py` (Stripe, ACH payment handlers)
- [ ] Unit test commission calculations
- [ ] Unit test batch generation

### Week 3: Admin API
- [ ] Create `admin_payouts.py` routes
- [ ] List schedules: `GET /api/admin/payouts/schedules`
- [ ] Create schedule: `POST /api/admin/payouts/schedules`
- [ ] List batches: `GET /api/admin/payouts/batches`
- [ ] Approval: `POST /api/admin/payouts/batches/{id}/approve`
- [ ] Integration tests

### Week 4: Partner Dashboard
- [ ] Payment history: `GET /api/dashboards/{role}/payments`
- [ ] Pending earnings: `GET /api/dashboards/{role}/pending-earnings`
- [ ] Frontend: Payment table component
- [ ] Frontend: Earnings breakdown

### Week 5: Compliance
- [ ] IRS 1099-NEC generation
- [ ] Tax withholding logic
- [ ] Bank settlement reports
- [ ] Audit logging

### Week 6: DevOps
- [ ] Celery tasks for scheduled batches
- [ ] Monitoring/alerting for failed payouts
- [ ] Manual adjustment tools
- [ ] Chargeback reversal workflow

---

## 📊 Fee & Tax Structure

### Processing Fees

| Method | Fee | When |
|--------|-----|------|
| Stripe Connect | 2% (max $5) | All affiliate payouts |
| ACH | $1.00 | Referral, Retail, Exec <$5K |
| ACH | $1.50 | Referral, Retail, Exec ≥$5K |
| Check | $2.00 | Manual requests |

### Tax Withholding

- **Threshold**: $600+ annual earnings
- **Form**: IRS 1099-NEC (issued Jan 31)
- **Withholding Rate**: 10% (withheld from commission)
- **International**: 30% FATCA withholding (Form W-8BEN required)

---

## 🔐 Security Checkpoints

✅ **Authentication**
- Admin endpoints require session cookie
- Partner endpoints require partner login
- API key validation for Stripe

✅ **Authorization**  
- Admins can approve/reject batches >$50K
- Partners can only view own payouts
- Two-factor approval for high amounts

✅ **Data Integrity**
- Immutable audit log
- HMAC signing on all payments
- Webhook signature validation

✅ **Fraud Prevention**
- 7-day hold (affiliate fraud detection)
- 60-day hold (referral deal verification)
- Chargeback tracking & reversal
- Dispute resolution workflow

---

## 📧 Email Templates

### Payout Approved (to partner)
```
Subject: ✅ Your Payout of $XX.XX is Scheduled

Amount: $XX.XX
Due Date: [DATE]
Payment Method: [Stripe/Check/ACH]

Your commission breakdown:
- Gross earnings: $XXX.XX
- Processing fee: -$X.XX
- Net payout: $XX.XX

Track it: [DASHBOARD_LINK]
```

### Batch Ready (to admin)
```
Subject: ⏳ Payout Batch Pending Approval

Batch: [WEEKLY_2026_04_13_001]
Total: $XX,XXX.XX
Payees: [NUMBER]

Review: [ADMIN_LINK]
```

### Payment Failed (to admin)
```
Subject: ⚠️ Payout Failed - Manual Review Required

Batch: [BATCH_NUMBER]
Amount: $XXX.XX
Error: [ERROR_MESSAGE]

Action: [ADMIN_LINK]
```

---

## 🎯 API Quick Links

### Admin Payouts
```
GET    /api/admin/payouts/schedules              # List schedules
POST   /api/admin/payouts/schedules              # Create schedule
GET    /api/admin/payouts/batches                # List batches
POST   /api/admin/payouts/batches/trigger        # Create batch
POST   /api/admin/payouts/batches/{id}/approve   # Approve batch
POST   /api/admin/payouts/batches/{id}/reject    # Reject batch
GET    /api/admin/payouts/batches/{id}/report    # Download report
```

### Partner Dashboard
```
GET    /api/dashboards/{role}/payments           # Payment history
GET    /api/dashboards/{role}/pending-earnings   # Pending earnings
POST   /api/dashboards/{role}/request-payout     # Request early payout
```

---

## 🚀 Sample Payout Scenario (Scenario 1: Affiliates)

```
📅 Monday, April 13, 2 AM UTC - WEEKLY BATCH

Partner: Creator #5
├─ Orders (Apr 6-12):
│  ├─ Order #1: $50 × 10% = $5.00 (approved Apr 9)
│  ├─ Order #2: $100 × 10% = $10.00 (approved Apr 8)
│  ├─ Order #3: $75 × 10% = $7.50 (approved Apr 10)
│  └─ Gross: $22.50
├─ Less Stripe fee (2%): -$0.45
├─ Less processing fee: -$0.50
└─ NET PAYOUT: $21.55 ✅

Result:
- PayoutBatch created: WEEKLY_2026_04_13_001
- CommissionPayout: PAYOUT_2026_04_13_0001
- Status: Pending admin approval
- Email sent: "Your $21.55 payout is scheduled for Mon, Apr 13"
```

---

## 🔍 Troubleshooting

**Q: Why wasn't my commission in this payout batch?**
- Still in 7-day hold period (affiliates), or
- Below $1.00 minimum threshold, or
- Order status not "completed", or
- Earning marked "disputed"

**Q: When will I receive payment?**
- Affiliates: Last Monday of month (within 1-3 business days via Stripe)
- Referral partners: 1st & 15th (within 2-3 business days via ACH)
- Executives: Every Monday (within 1-2 business days via ACH)
- Retail partners: Monthly or bi-weekly depending on volume

**Q: What fees apply?**
- Stripe (2% + $0.50 flat) = ~2.5%
- ACH ($1-$1.50) = ~0.02-0.03%
- Tax withholding (10%) if earnings >$600/year

**Q: Can I get an early payout?**
- Yes, for balances >$100 (manual request)
- Admin reviews within 24 hours
- Additional $5 processing fee applies

---

## 📚 Reference Documents

1. **PHASE4_PAYOUT_PROCESSING.md** - Full specification (14 sections)
2. **PHASE4_IMPLEMENTATION_CODE.md** - Code templates (4 parts)
3. **models.py** - Database models (add to existing file)
4. **admin_payouts.py** - Admin routes (NEW file)
5. **payout_processor.py** - Business logic (NEW file)
6. **payout_dispatcher.py** - Payment dispatch (NEW file)

---

## 🎓 Learning Path

1. **Start here**: This quick reference
2. **Read section by section**: PHASE4_PAYOUT_PROCESSING.md
3. **Understand examples**: Scroll to "11. Example Scenarios"
4. **Review code**: PHASE4_IMPLEMENTATION_CODE.md
5. **Implement**: Follow implementation checklist
6. **Test**: Run unit & integration tests
7. **Deploy**: Follow Celery task setup

---

*Last Updated: April 2026*  
*Status: Design Complete ✅ | Ready for Implementation 🚀*
