# Phase 4: Commission Payout Schedule & Processing

## Executive Summary

Phase 4 implements a complete commission and payout system for the Jonche Platform partner ecosystem. This enables automated calculation, scheduling, and processing of payments to Affiliates, Referral Partners, Retail Partners, and Executives based on their performance metrics.

**Timeline & Status:**
- Phase 1-3: ✅ Partner onboarding, dashboards, emails complete
- Phase 4: 🔄 Commission & Payout Processing (THIS PHASE)

---

## 1. Commission Structure by Partner Type

### 1.1 Affiliate Creators (Content Creators)

**Commission Trigger:** Completed order via referral link
```
commission = order_value × commission_rate_percent / 100
```

**Default Structure:**
| Tier | Commission Rate | Status | Requirements |
|------|-----------------|--------|---------------|
| Starter | 10% | Active | New affiliates |
| Gold | 15% | Active | 50+ conversions/month |
| Platinum | 20% | Active | 200+ conversions/month |
| Premium | 25% | Active | 1000+ conversions/month + approved creators |

**Status Progression:**
```
pending (7 days) → approved (after verification) → paid
```

**Validation Rules:**
- Affiliate must be verified at commission creation
- Order must have completed status
- Member must have clicked affiliate link
- No duplicate commissions per order
- Commission locked once order confirmed

---

### 1.2 Referral Partners (Deal Brokers)

**Commission Trigger:** Deal funding completion
```
commission = deal_value × commission_rate / 100
```

**Deal Lifecycle:**
```
submitted → approved → in_progress → closed → invoiced → paid
```

**Commission Structure:**
| Deal Type | Commission Rate | Payout Timing |
|-----------|-----------------|---------------|
| Bulk Order (<$50K) | 3-5% | 60 days post-shipment |
| Partnership (>$50K) | 5-8% | 90 days post-completion |
| Funding Round | 8-12% | Custom (deal-specific) |
| Standard Deal | 5% | 60 days post-close |

**Status Flows:**
- `submitted`: Awaiting admin review
- `approved`: Admin approved, deal active
- `in_progress`: Work being performed
- `closed`: Deal completed, awaiting final reconciliation
- `invoiced`: Ready for payment (admin has verified completion)
- `paid`: Commission disbursed
- `disputed`: Under review (holds payout processing)

**Commission Calculation:**
```python
if deal.status == "invoiced":
    commission_cents = deal.actual_value_cents * (deal.commission_percent / 100)
    status = "pending"
    payout_date = deal.closed_at + timedelta(days=60)
```

---

### 1.3 Retail Partners (Wholesale)

**Commission Trigger:** Store order payment + fulfillment
```
commission = order_value × wholesale_margin × partner_share_percent
```

**Model:**
- Earn on margin differential (retail vs. cost)
- Only after fulfillment completion
- Tiered based on volume

| Annual Volume | Margin Take | Payout Schedule |
|---------------|-----------|-----------------|
| <$100K | 15% | Monthly |
| $100K-$500K | 20% | Monthly |
| >$500K | 25% | Bi-weekly |

**Status:** Auto-approved (no pending required)

---

### 1.4 Executives (Territory Managers)

**Commission Trigger:** Approved partnership deal with assigned territory

**Structure:**
```
commission = deal_value × executive_commission_rate / 100
```

**Commission Table:**
| Territory Size | Rate | Assignment | Payout |
|---|---|---|---|
| Small (<$5M) | 2-3% | Single exec | Monthly |
| Medium ($5M-$20M) | 3-5% | Single exec | Bi-weekly |
| Large (>$20M) | 5-7% | Exec split | Weekly |

**Constraints:**
- Only ONE executive per territory
- Deal must have executive_id set
- Split commissions handled via deal configuration

---

## 2. Payout Schedule Design

### 2.1 Payout Batch Calendar

```
Weekly (Mondays @ 2 AM UTC):
  ├─ Executives (immediate settlement)
  ├─ Retail Partners (high-volume partners)
  └─ Status: WEEKLY_BATCH

Bi-Weekly (1st & 15th @ 2 AM UTC):
  ├─ Referral Partners (88% of standard deals)
  ├─ Mid-tier Affiliates
  └─ Status: BIWEEKLY_BATCH

Monthly (Last business day @ 2 AM UTC):
  ├─ Affiliate Creators (tier-based)
  ├─ Retail Partners (low-volume)
  ├─ Small deals awaiting reconciliation
  └─ Status: MONTHLY_BATCH
```

### 2.2 Hold & Release Rules

**Affiliate Earnings Hold:**
```python
if commission.status == "pending":
    if days_since_order_confirmed >= 7:
        commission.status = "approved"
        # Auto-approve after 7 days (fraud checking window)
```

**Referral Deal Hold:**
```python
if deal.status == "closed":
    days_since_close = now() - deal.closed_at
    if days_since_close >= 30 and deal.approved_by_admin:
        deal.status = "invoiced"  # Ready for payment
        # Admin must explicitly invoice before payout
```

**Retail Order Hold:**
```python
# Track fulfillment status from warehouse webhook
if store_order.fulfillment_status == "shipped":
    # Commission only created after shipment
    commission_created = True
    commission.status = "approved"  # No pending needed
```

### 2.3 Payout Window

**Cutoff Times (per batch type):**
- **Weekly:** Friday 8 PM UTC → Monday 2 AM payout
- **Bi-Weekly:** Friday (end of period) 8 PM UTC → Monday 2 AM payout  
- **Monthly:** Last business day 8 PM UTC → EOM Monday 2 AM payout

---

## 3. Database Schema Additions

### 3.1 New Table: PayoutSchedule

```python
class PayoutSchedule(db.Model):
    __tablename__ = "payout_schedules"

    id                      = db.Column(db.Integer, primary_key=True)
    
    # Identity
    name                    = db.Column(db.String(100), nullable=False)
                            # "weekly_exec", "biweekly_referral", "monthly_affiliate"
    frequency               = db.Column(db.String(20), nullable=False)
                            # weekly|bi-weekly|monthly
    day_of_week             = db.Column(db.Integer, nullable=True)  # 0=Monday, 6=Sunday
    day_of_month            = db.Column(db.Integer, nullable=True)  # 1-31
    
    # Execution
    cutoff_day_time         = db.Column(db.String(20), nullable=False)
                            # e.g., "Fri 20:00 UTC", "Mon 08:00 UTC"
    payout_time             = db.Column(db.String(20), nullable=False)
                            # e.g., "Mon 02:00 UTC", "EOM Mon 02:00 UTC"
    
    # Eligibility filters
    eligible_partner_types  = db.Column(db.String(200), nullable=False)
                            # comma-separated: affiliates, referral, retail, executive
    eligible_statuses       = db.Column(db.String(200), nullable=False)
                            # comma-separated: approved, invoiced, paid_pending
    min_amount_cents        = db.Column(db.Integer, default=0)
    
    # Config
    hold_period_days        = db.Column(db.Integer, default=0)
                            # Additional hold before eligible
    is_active               = db.Column(db.Boolean, default=True)
    notes                   = db.Column(db.Text, nullable=True)
    
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at              = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    batches                 = db.relationship("PayoutBatch", back_populates="schedule", lazy="dynamic")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "frequency": self.frequency,
            "cutoff_day_time": self.cutoff_day_time,
            "payout_time": self.payout_time,
            "eligible_partner_types": self.eligible_partner_types.split(','),
            "eligible_statuses": self.eligible_statuses.split(','),
            "min_amount_cents": self.min_amount_cents,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }
```

### 3.2 New Table: PayoutBatch

```python
class PayoutBatch(db.Model):
    __tablename__ = "payout_batches"

    id                      = db.Column(db.Integer, primary_key=True)
    batch_number            = db.Column(db.String(50), unique=True, nullable=False)
                            # e.g., "WEEKLY_2026_04_13_001", "MONTHLY_2026_04_01_001"
    schedule_id             = db.Column(db.Integer, db.ForeignKey("payout_schedules.id"), nullable=False)
    
    # Batch details
    payout_cycle_start      = db.Column(db.DateTime, nullable=False)
    payout_cycle_end        = db.Column(db.DateTime, nullable=False)
    scheduled_payout_date   = db.Column(db.DateTime, nullable=False)
    
    # Metrics
    total_payouts_cents     = db.Column(db.Integer, default=0)
    payee_count             = db.Column(db.Integer, default=0)
    affiliate_count         = db.Column(db.Integer, default=0)
    referral_partner_count  = db.Column(db.Integer, default=0)
    retail_partner_count    = db.Column(db.Integer, default=0)
    executive_count         = db.Column(db.Integer, default=0)
    
    # Status
    status                  = db.Column(db.String(30), default="pending")
                            # pending|processing|paid|partial|failed|cancelled
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)
    processing_started_at   = db.Column(db.DateTime, nullable=True)
    completed_at            = db.Column(db.DateTime, nullable=True)
    
    # Processing info
    stripe_batch_id         = db.Column(db.String(100), nullable=True)
    ach_batch_id            = db.Column(db.String(100), nullable=True)
    notes                   = db.Column(db.Text, nullable=True)
    
    # Relationships
    schedule                = db.relationship("PayoutSchedule", back_populates="batches")
    payouts                 = db.relationship("CommissionPayout", back_populates="batch", lazy="dynamic")
    
    @property
    def total_payouts_dollars(self):
        return self.total_payouts_cents / 100
    
    def to_dict(self):
        return {
            "id": self.id,
            "batch_number": self.batch_number,
            "schedule_id": self.schedule_id,
            "payout_cycle_start": self.payout_cycle_start.isoformat(),
            "payout_cycle_end": self.payout_cycle_end.isoformat(),
            "scheduled_payout_date": self.scheduled_payout_date.isoformat(),
            "total_payouts_cents": self.total_payouts_cents,
            "total_payouts_dollars": self.total_payouts_dollars,
            "payee_count": self.payee_count,
            "status": self.status,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
```

### 3.3 New Table: CommissionPayout

```python
class CommissionPayout(db.Model):
    __tablename__ = "commission_payouts"

    id                      = db.Column(db.Integer, primary_key=True)
    batch_id                = db.Column(db.Integer, db.ForeignKey("payout_batches.id"), nullable=False)
    
    # Identity
    payout_number           = db.Column(db.String(50), unique=True, nullable=False)
                            # e.g., "PAYOUT_2026_04_13_0001"
    payee_type              = db.Column(db.String(30), nullable=False)
                            # affiliate|referral_partner|retail_partner|executive
    payee_id                = db.Column(db.Integer, nullable=False)
                            # FK to appropriate partner table
    
    # Amount & source
    commission_cents        = db.Column(db.Integer, nullable=False)
    payout_cents            = db.Column(db.Integer, nullable=False)
                            # After fees and deductions
    fee_cents               = db.Column(db.Integer, default=0)
                            # Processing fee
    tax_withheld_cents      = db.Column(db.Integer, default=0)
                            # If 1099 required
    deduction_cents         = db.Column(db.Integer, default=0)
                            # Chargebacks, adjustments, etc.
    
    # Earnings aggregated
    earnings_count          = db.Column(db.Integer, default=0)
                            # How many earnings/deals bundled
    earnings_list           = db.Column(db.JSON, nullable=True)
                            # [{"earning_id": 123, "amount_cents": 500}, ...]
    
    # Payment method
    payment_method          = db.Column(db.String(30), nullable=False)
                            # stripe_connect|ach|paypal|check
    payment_status          = db.Column(db.String(30), default="pending")
                            # pending|processing|paid|failed|reversed
    
    # Payout references
    stripe_payout_id        = db.Column(db.String(100), nullable=True)
    stripe_recipient_id     = db.Column(db.String(100), nullable=True)
    ach_reference           = db.Column(db.String(100), nullable=True)
    external_reference      = db.Column(db.String(100), nullable=True)
    
    # Tracking
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at            = db.Column(db.DateTime, nullable=True)
    completed_at            = db.Column(db.DateTime, nullable=True)
    failure_reason          = db.Column(db.Text, nullable=True)
    
    # Relationships
    batch                   = db.relationship("PayoutBatch", back_populates="payouts")
    
    @property
    def commission_dollars(self):
        return self.commission_cents / 100
    
    @property
    def payout_dollars(self):
        return self.payout_cents / 100
    
    def to_dict(self):
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "payout_number": self.payout_number,
            "payee_type": self.payee_type,
            "payee_id": self.payee_id,
            "commission_cents": self.commission_cents,
            "commission_dollars": self.commission_dollars,
            "payout_cents": self.payout_cents,
            "payout_dollars": self.payout_dollars,
            "fee_cents": self.fee_cents,
            "tax_withheld_cents": self.tax_withheld_cents,
            "payment_method": self.payment_method,
            "payment_status": self.payment_status,
            "stripe_payout_id": self.stripe_payout_id,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
```

### 3.4 Schema Updates: Existing Tables

**Update `AffiliateEarning`:**
```python
class AffiliateEarning(db.Model):
    # ... existing fields ...
    
    # ADD:
    payout_id               = db.Column(db.Integer, db.ForeignKey("commission_payouts.id"), nullable=True)
    payout_batch_id         = db.Column(db.String(100), nullable=True)  # For historical tracking
    hold_reason             = db.Column(db.String(255), nullable=True)  # If held/disputed
    hold_until              = db.Column(db.DateTime, nullable=True)     # Release date if held
    verification_token      = db.Column(db.String(100), nullable=True)  # For 1099 verification
```

**Update `PartnerReferral`:**
```python
class PartnerReferral(db.Model):
    # ... existing fields ...
    
    # ADD:
    payout_id               = db.Column(db.Integer, db.ForeignKey("commission_payouts.id"), nullable=True)
    payout_batch_id         = db.Column(db.String(100), nullable=True)
    invoice_date            = db.Column(db.DateTime, nullable=True)  # When admin invoiced
    invoice_number          = db.Column(db.String(50), nullable=True)
    payment_terms           = db.Column(db.String(50), nullable=True)  # Net 30, Net 60, etc.
    verification_notes      = db.Column(db.Text, nullable=True)
```

**Update `RetailerAllocation` (for retail commission tracking):**
```python
class RetailerCommission(db.Model):
    __tablename__ = "retailer_commissions"
    
    id                      = db.Column(db.Integer, primary_key=True)
    retailer_id             = db.Column(db.Integer, db.ForeignKey("retailers.id"), nullable=False)
    store_order_id          = db.Column(db.Integer, db.ForeignKey("store_orders.id"), nullable=False)
    order_value_cents       = db.Column(db.Integer, nullable=False)
    margin_cents            = db.Column(db.Integer, nullable=False)
    commission_rate_percent = db.Column(db.Float, nullable=False)
    commission_cents        = db.Column(db.Integer, nullable=False)
    fulfillment_status      = db.Column(db.String(50), nullable=True)
    status                  = db.Column(db.String(20), default="pending")
    payout_id               = db.Column(db.Integer, db.ForeignKey("commission_payouts.id"), nullable=True)
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)
```

### 3.5 New Table: PayoutReport

```python
class PayoutReport(db.Model):
    __tablename__ = "payout_reports"

    id                      = db.Column(db.Integer, primary_key=True)
    batch_id                = db.Column(db.Integer, db.ForeignKey("payout_batches.id"), nullable=False)
    
    # Report details
    report_type             = db.Column(db.String(50), nullable=False)
                            # summary|detailed|irs_1099|bank_settlement
    status                  = db.Column(db.String(20), default="pending")
                            # pending|ready|sent|archived
    
    # Content
    report_data             = db.Column(db.JSON, nullable=True)
    pdf_url                 = db.Column(db.String(500), nullable=True)
    csv_url                 = db.Column(db.String(500), nullable=True)
    
    # Audit trail
    generated_at            = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at                 = db.Column(db.DateTime, nullable=True)
    sent_to                 = db.Column(db.String(500), nullable=True)  # Email addresses
    
    # Relationships
    batch                   = db.relationship("PayoutBatch", foreign_keys=[batch_id])
    
    def to_dict(self):
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "report_type": self.report_type,
            "status": self.status,
            "generated_at": self.generated_at.isoformat(),
        }
```

---

## 4. Payout Processing Workflow

### 4.1 End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    PAYOUT CYCLE (Weekly/Bi-weekly/Monthly)      │
└─────────────────────────────────────────────────────────────────┘
         ↓
  ┌──────────────────────┐
  │ 1. IDENTIFY ELIGIBLE │
  │    EARNINGS/DEALS    │
  └──────────────────────┘
         ↓
   Query all commissions with:
   - status = "approved" or "invoiced"
   - hold_until < NOW or NO hold
   - min_amount > 0
   - created_at within payout cycle
         ↓
  ┌──────────────────────┐
  │ 2. AGGREGATE BY      │
  │    PAYEE/TYPE        │
  └──────────────────────┘
         ↓
   Group commissions:
   - Sum by payee_type + payee_id
   - Calculate fees (2-3% Stripe fee)
   - Calculate taxes (if required)
   - Deduct chargebacks/disputes
         ↓
  ┌──────────────────────┐
  │ 3. CREATE BATCH      │
  └──────────────────────┘
         ↓
   PayoutBatch {
     batch_number: "WEEKLY_2026_04_13_001",
     status: "pending",
     total_payouts_cents: X,
     payee_count: N,
   }
         ↓
  ┌──────────────────────┐
  │ 4. ADMIN REVIEW      │
  │    & APPROVAL        │
  └──────────────────────┘
         ↓
   Admin can:
   - Review breakdown by partner type
   - Remove individual payouts
   - Adjust fees
   - Add notes/hold reason
   - Approve/Reject batch
         ↓
  ┌──────────────────────┐
  │ 5. PROCESS PAYMENT   │
  │    (Stripe/ACH)      │
  └──────────────────────┘
         ↓
   For each CommissionPayout:
   - Stripe Connect: POST /v1/payouts
   - ACH: POST to ACH provider
   - Check: Generate, mail
         ↓
  ┌──────────────────────┐
  │ 6. CONFIRM & UPDATE  │
  │    STATUS            │
  └──────────────────────┘
         ↓
   Update batch status → "processing"
   Create PayoutReport
   Send payment confirmation emails
         ↓
  ┌──────────────────────┐
  │ 7. MARK COMPLETE     │
  │    & ARCHIVE         │
  └──────────────────────┘
         ↓
   Batch status → "paid"
   Flag commission_payouts as "paid"
   Generate IRS 1099s (quarterly)
   Create audit trail entry
```

### 4.2 Detailed Calculation Logic

**For Affiliate Earnings:**
```python
def calculate_affiliate_payout(affiliate_id, cycle_start, cycle_end):
    # Get all approved earnings in cycle
    earnings = AffiliateEarning.query.filter(
        AffiliateEarning.affiliate_id == affiliate_id,
        AffiliateEarning.status == "approved",
        AffiliateEarning.created_at >= cycle_start,
        AffiliateEarning.created_at <= cycle_end,
        AffiliateEarning.hold_until < now() | AffiliateEarning.hold_until == None
    ).all()
    
    gross_commission_cents = sum(e.commission_cents for e in earnings)
    
    if gross_commission_cents < 100:  # $1.00 minimum
        return None  # Skip payout
    
    # Calculate fees
    stripe_fee_cents = int(gross_commission_cents * 0.02)  # 2%
    processing_fee_cents = 50  # $0.50 flat fee
    
    # Tax handling (if 1099 required)
    tax_cents = 0
    if gross_commission_cents >= 20000:  # $200+ threshold
        tax_cents = int(gross_commission_cents * 0.1)  # 10% withhold
    
    # Final payout
    payout_cents = (
        gross_commission_cents -
        stripe_fee_cents -
        processing_fee_cents -
        tax_cents
    )
    
    return {
        "gross": gross_commission_cents,
        "stripe_fee": stripe_fee_cents,
        "processing_fee": processing_fee_cents,
        "tax_withheld": tax_cents,
        "payout": payout_cents,
        "earnings_ids": [e.id for e in earnings],
    }
```

**For Referral Deals:**
```python
def calculate_referral_payout(referral_partner_id, cycle_start, cycle_end):
    # Get all invoiced deals
    deals = PartnerReferral.query.filter(
        PartnerReferral.referral_partner_id == referral_partner_id,
        PartnerReferral.status == "invoiced",
        PartnerReferral.invoice_date >= cycle_start,
        PartnerReferral.invoice_date <= cycle_end,
    ).all()
    
    gross_commission_cents = sum(d.commission_cents for d in deals)
    
    if gross_commission_cents < 500:  # $5.00 minimum for referral partners
        return None
    
    ach_fee_cents = 100 if gross_commission_cents < 5000 else 150  # $1 or $1.50
    
    payout_cents = gross_commission_cents - ach_fee_cents
    
    return {
        "gross": gross_commission_cents,
        "ach_fee": ach_fee_cents,
        "payout": payout_cents,
        "deal_ids": [d.id for d in deals],
    }
```

---

## 5. API Endpoints (Phase 4)

### 5.1 Admin Payout Management

#### List Payout Schedules
```
GET /api/admin/payouts/schedules
Response:
{
    "schedules": [
        {
            "id": 1,
            "name": "weekly_exec",
            "frequency": "weekly",
            "cutoff_day_time": "Fri 20:00 UTC",
            "eligible_partner_types": ["executive"],
            "payee_count": 45,
            "next_run": "2026-04-20T02:00:00Z"
        }
    ]
}
```

#### Create/Update Payout Schedule
```
POST /api/admin/payouts/schedules
{
    "name": "monthly_affiliate",
    "frequency": "monthly",
    "day_of_month": 28,
    "cutoff_day_time": "Fri 20:00 UTC",
    "payout_time": "EOM Mon 02:00 UTC",
    "eligible_partner_types": "affiliates",
    "eligible_statuses": "approved,invoiced",
    "hold_period_days": 7,
    "is_active": true
}
```

#### List Payout Batches
```
GET /api/admin/payouts/batches?status=pending&limit=50&offset=0
Response:
{
    "batches": [
        {
            "id": 123,
            "batch_number": "WEEKLY_2026_04_13_001",
            "scheduled_payout_date": "2026-04-13T02:00:00Z",
            "total_payouts_cents": 50000,
            "payee_count": 25,
            "status": "pending",
            "payouts": [
                {
                    "payout_number": "PAYOUT_2026_04_13_0001",
                    "payee_type": "affiliate",
                    "payee_id": 5,
                    "payout_cents": 2000,
                    "fee_cents": 40
                }
            ]
        }
    ],
    "total": 15,
    "pending_count": 3
}
```

#### Review & Approve Batch
```
POST /api/admin/payouts/batches/{batch_id}/approve
{
    "notes": "Approved after review",
    "adjustments": [
        {
            "payout_id": 456,
            "action": "remove",
            "reason": "Dispute under review"
        }
    ]
}
Response: { "status": "processing", "message": "Batch approved. Processing..." }
```

#### Reject Batch
```
POST /api/admin/payouts/batches/{batch_id}/reject
{
    "reason": "Pending dispute resolution for 3 payouts"
}
Response: { "status": "cancelled", "reason": "..." }
```

#### Manually Trigger Payout Batch
```
POST /api/admin/payouts/batches/trigger
{
    "schedule_id": 1,
    "cycle_start": "2026-04-01T00:00:00Z",
    "cycle_end": "2026-04-13T23:59:59Z"
}
Response: {
    "batch_id": 124,
    "batch_number": "WEEKLY_2026_04_13_002",
    "total_payouts_cents": 75000,
    "status": "pending"
}
```

#### Download Batch Report
```
GET /api/admin/payouts/batches/{batch_id}/report?format=csv
Response: CSV file (Content-Disposition: attachment)

GET /api/admin/payouts/batches/{batch_id}/report?format=json
Response: 
{
    "batch_number": "WEEKLY_2026_04_13_001",
    "payouts": [...]
}
```

### 5.2 Partner Dashboard Endpoints

#### Get Payment History
```
GET /api/dashboards/affiliate/payments?limit=50
{
    "payments": [
        {
            "payout_number": "PAYOUT_2026_04_13_0001",
            "amount_cents": 1960,
            "amount_dollars": 19.60,
            "fee_cents": 40,
            "status": "paid",
            "paid_at": "2026-04-13T14:32:00Z",
            "batch_number": "WEEKLY_2026_04_13_001"
        }
    ],
    "total_lifetime_paid_cents": 50000,
    "total_pending_cents": 500,
    "next_payout_date": "2026-04-20T02:00:00Z"
}
```

#### Get Earnings Pending Payout
```
GET /api/dashboards/affiliate/pending-earnings
{
    "pending_earnings": [
        {
            "earning_id": 789,
            "order_value_cents": 10000,
            "commission_cents": 1000,
            "status": "approved",
            "created_at": "2026-04-10T12:00:00Z",
            "scheduled_payout_date": "2026-04-20T02:00:00Z"
        }
    ],
    "total_pending_cents": 500
}
```

#### Request Manual Payout (if below threshold)
```
POST /api/dashboards/referral-partner/request-payout
{
    "reason": "Need funds for business expense"
}
Response: {
    "status": "request_submitted",
    "message": "Admin will review within 24 hours",
    "minimum_threshold_cents": 500
}
```

### 5.3 Scheduled Batch Processing

#### View Upcoming Scheduled Batches
```
GET /api/admin/payouts/scheduled
{
    "upcoming": [
        {
            "schedule_id": 1,
            "name": "weekly_exec",
            "next_run": "2026-04-20T02:00:00Z",
            "expected_payee_count": 42,
            "expected_total_cents": 85000
        }
    ]
}
```

---

## 6. Implementation Phases

### Phase 4.1: Database & Core Processing (Week 1-2)

- [x] Create PayoutSchedule model
- [x] Create PayoutBatch model
- [x] Create CommissionPayout model
- [x] Create PayoutReport model
- [x] Add ForeignKey to AffiliateEarning, PartnerReferral
- [x] Add RetailerCommission model
- [ ] Run migrations
- [ ] Create indexes on (schedule_id, status), (batch_id, payee_id)

### Phase 4.2: Admin API & Batch Management (Week 2-3)

- [ ] Implement `/api/admin/payouts/schedules` endpoints
- [ ] Implement `/api/admin/payouts/batches` endpoints
- [ ] Implement batch calculation logic (Python service)
- [ ] Create batch approval/rejection flow
- [ ] Implement Stripe Connect payout integration
- [ ] Unit tests for calculation logic

### Phase 4.3: Partner Dashboard & Self-Service (Week 3-4)

- [ ] Implement `/api/dashboards/*/payments` endpoint
- [ ] Implement `/api/dashboards/*/pending-earnings` endpoint
- [ ] Add payment history UI to partner dashboards
- [ ] Add "Request Payout" button (for small balances)
- [ ] Create payment settlement notifications

### Phase 4.4: Reports & Compliance (Week 4-5)

- [ ] Generate IRS 1099 forms (annual)
- [ ] Generate ACH/bank settlement reports
- [ ] Export tax documents to accountant
- [ ] Create audit trail/compliance reports
- [ ] Email payout summaries to partners

### Phase 4.5: Monitoring & Support Tools (Week 5-6)

- [ ] Create admin dashboard for payout status
- [ ] Add alerting for failed/stuck payouts
- [ ] Manual payout adjustment tools
- [ ] Payout reversal/chargeback handling
- [ ] Partner support ticket system

---

## 7. Business Rules & Constraints

### 7.1 Hold Periods

```
Affiliate Earnings:    7 days (fraud detection window)
Referral Deals:        60+ days (verify deal completion)
Retail Orders:         0 days (auto-approved after shipment)
Executive Commissions: 0 days (auto-approved)
```

### 7.2 Minimum Thresholds

```
Affiliate Creators:    $1.00 (included in batch)
Referral Partners:     $5.00 (excluded if below)
Retail Partners:       $10.00 (excluded if below)
Executives:            $25.00 (excluded if below)
```

### 7.3 Fee Structure

| Processor | Fee | Cap | Conditions |
|-----------|-----|-----|------------|
| Stripe Connect | 2% | $5 | Preferred for affiliates |
| ACH Batch | $1.00-$1.50 flat | None | Preferred for partners >$5K |
| Check | $2.00 flat | None | For on-demand requests |
| International Wire | 3% + $15 | $500 | Special request |

### 7.4 Compliance & Taxes

```
1099-NEC Threshold: $600+ annual earnings
  ├─ Issued: Jan 31 following tax year
  ├─ Partner must provide SSN/EIN
  ├─ Tax ID verification required

W-8BEN (International): $600+ earnings + non-US person
  ├─ FATCA withholding: 30%
  ├─ Treaty exemptions apply

Form 8949 (1099-K Alternative):
  ├─ Third-party payment processors
  ├─ $20K + 200 transactions threshold
```

### 7.5 Dispute & Reversal Handling

```
Chargeback Flow:
  1. Customer disputes charge
  2. Stripe/processor notifies
  3. Partner earning status → "disputed"
  4. Hold commission/referral payout
  5. Admin investigates
  6. Resolution: approve reversal or reinstate
  7. Process adjustment in next batch

Max reversal window: 180 days (per processor)
```

---

## 8. Security & Audit Trail

### 8.1 Payment Security

- ✅ All Stripe payouts use OAuth (not API keys)
- ✅ ACH uses encrypted bank details
- ✅ HMAC signing on all transactions
- ✅ Immutable audit log (no updates post-payment)
- ✅ Two-factor approval for batches >$50K

### 8.2 Audit Logging

```python
AuditLog:
- payout_id: Link to payment
- action: created|approved|rejected|processed|failed|reversed
- admin_id: Who performed action
- old_value / new_value: Changes
- reason: Why
- timestamp: When
- ip_address: From where
```

### 8.3 Reconciliation

```
Monthly reconciliation:
  1. Compare PayoutBatch status vs. bank statement
  2. Flag mismatches (pending but not arrived)
  3. Investigate failed payments
  4. Reverse payments if chargeback claimed
  5. Generate reconciliation report
```

---

## 9. Configuration & Deployment

### 9.1 Environment Variables

```bash
# Stripe settings
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLIC_KEY=pk_live_...
STRIPE_CONNECT_ENABLED=true

# ACH processor (if used)
ACH_PROVIDER=dwolla  # or stripe_ach
ACH_API_KEY=...

# Tax settings
IRS_1099_THRESHOLD_CENTS=60000  # $600
ENABLE_TAX_WITHHOLDING=true
TAX_WITHHOLD_RATE=0.10

# Payout settings
PAYOUT_PROCESSING_ENABLED=true
PAYOUT_MIN_AMOUNT_CENTS=100
PAYOUT_MAX_BATCH_SIZE=1000
PAYOUT_APPROVAL_REQUIRED=true  # Require manual approval
```

### 9.2 Scheduled Tasks (Celery)

```python
# Send at 1 AM UTC (1 hour before payout) for admin review
@periodic_task(run_every=crontab(hour=1, minute=0))
def notify_admin_payout_pending():
    """Alert admin to pending batches ready for approval"""
    pass

# Execute payouts at designated times
@periodic_task(run_every=crontab(hour=2, minute=0))
def process_weekly_payouts():
    """Process weekly schedule"""
    pass

@periodic_task(run_every=crontab(hour=2, minute=0, day_of_week=1))
def process_monthly_payouts():
    """Process monthly schedule (first Monday)"""
    pass

# Daily reconciliation
@periodic_task(run_every=crontab(hour=9, minute=0))
def reconcile_stripe_payouts():
    """Compare batch status vs. Stripe API"""
    pass

# Annual 1099 generation
@periodic_task(run_every=crontab(month=1, day=25))
def generate_1099_forms():
    """Generate and email 1099-NECs"""
    pass
```

---

## 10. Partner Communication

### 10.1 Email Templates

**Payment Approved (to partner):**
```
Subject: ✅ Your Payout of $XX.XX is Scheduled

Hi [Partner Name],

Great news! Your commission payout has been approved and scheduled.

Amount: $XX.XX
Due Date: [DATE]
Payment Method: [Stripe/Check/ACH]

Your commission breakdown:
- Gross earnings: $XXX.XX
- Processing fee: -$X.XX
- Net payout: $XX.XX

You can track this payout in your dashboard: [LINK]
```

**Batch Ready for Admin Review:**
```
Subject: ⏳ Payout Batch Pending Approval [BATCH_NUMBER]

Hi [Admin],

A payout batch is ready for your review:

Batch: [WEEKLY_2026_04_13_001]
Total: $XX,XXX.XX
Payees: [NUMBER]
Schedule: Weekly Executive Payouts

Review & approve: [ADMIN_LINK]
```

**Failed Payout (to admin):**
```
Subject: ⚠️ Payout Failed - Manual Review Required

Batch: [BATCH_NUMBER]
Payout: [PAYOUT_NUMBER]
Error: Stripe connection error
Amount: $XXX.XX

Take action: [ADMIN_LINK]
```

### 10.2 Dashboard Notifications

- ✅ "Your payout of $XX was paid on [DATE]"
- ✅ "You have $XX pending payout (scheduled for [DATE])"
- ✅ "Your payment failed due to [REASON]. Contact support."
- ✅ "Tax form 1099-NEC available for download"

---

## 11. Example Scenarios

### Scenario 1: Weekly Affiliate Payout

```
Monday, April 13, 2 AM UTC

Affiliate #5 (Creator):
├─ Earned from orders (Apr 6-12):
│  ├─ Order #1: $50 × 10% = $5.00 (approved Apr 10)
│  ├─ Order #2: $100 × 10% = $10.00 (approved Apr 9)
│  ├─ Order #3: $75 × 10% = $7.50 (approved Apr 11)
│  └─ Total: $22.50
├─ Hold period: 7 days (waived, all approved >7 days ago)
├─ Gross commission: $22.50
├─ Stripe fee (2%): -$0.45
├─ Processing fee: -$0.50
├─ Payout: $21.55 ✅

Creates:
- PayoutBatch: WEEKLY_2026_04_13_001
- CommissionPayout: PAYOUT_2026_04_13_0001
- Emails notification to affiliate
```

### Scenario 2: Monthly Referral Partner Payout

```
Monday, April 28, 2 AM UTC (End of month)

Referral Partner #2:
├─ Invoiced deals (Apr 1-30):
│  ├─ Deal #1 ($50K): 5% = $2,500 (invoiced Apr 15)
│  ├─ Deal #2 ($75K): 5% = $3,750 (invoiced Apr 22)
│  └─ Total: $6,250
├─ Hold period: 60 days from close (ALL deals >30 days closed, waived)
├─ Gross commission: $6,250.00
├─ ACH fee: -$1.50
├─ Payout: $6,248.50 ✅

Creates:
- PayoutBatch: MONTHLY_2026_04_28_001
- CommissionPayout: PAYOUT_2026_04_28_0001
- Sends ACH via Dwolla
- Partner sees $6,248.50 in bank by May 1
```

### Scenario 3: Disputed Earning (Hold)

```
Affiliate #3 has $500 pending commission, but:
- Customer files chargeback on source order
- Earning status → "disputed"
- hold_until = now() + 180 days (chargeback window)

Result:
- Commission NOT included in March payout batch
- April payout: Pending admin review
- Resolved: Admin approves reinstatement on April 20
- Next batch (May 4): Payout processes normally
```

---

## 12. Roadmap: Beyond Phase 4

**Phase 5+ Future Enhancements:**

- [ ] Real-time earnings dashboard (WebSocket updates)
- [ ] Partner-requested early payouts (emergency fund)
- [ ] Tiered commission rates (performance-based increases)
- [ ] Multi-currency payout support (EUR, GBP, JPY)
- [ ] Paypal/Wise integration (international transfers)
- [ ] Commission reversal appeals process
- [ ] Earnings forecasting (ML-based)
- [ ] Commission splits (partner shares)
- [ ] Bulk manual adjustments UI
- [ ] IRS e-filing automation (1099-NEC)

---

## 13. Testing Checklist

- [ ] Unit tests: Commission calculations (all 4 partner types)
- [ ] Unit tests: Hold period logic
- [ ] Integration test: Full payout cycle (mock Stripe)
- [ ] Integration test: Batch creation with 100+ payees
- [ ] Integration test: Failed payout retry logic
- [ ] API test: All admin endpoints
- [ ] API test: Partner dashboard endpoints
- [ ] E2E test: Affiliate registers → earns → gets paid
- [ ] Security test: Admin approval required for batches >$50K
- [ ] Compliance test: 1099 generation and tax withholding

---

## 14. Support & Troubleshooting

### Common Scenarios

**Q: Why wasn't my commission in this month's payout?**
A: Likely reasons:
1. Still in hold period (Affiliates: 7 days, Referrals: 60 days)
2. Below minimum threshold ($1 for affiliates, $5 for referrals)
3. Under dispute/investigation
4. Order status not yet marked "completed"

**Q: When will I get paid?**
A: Depends on your partner type:
- Executives: Weekly (every Monday)
- High-volume Retail: Bi-weekly (1st & 15th)
- Affiliates: Monthly (last Monday of month)
- Referral Partners: Bi-weekly (1st & 15th)

**Q: I need money urgently. Can I get early payout?**
A: We can potentially process an emergency payout for balances >$100. Contact support with reason.

**Q: What fees will I have deducted?**
A: Stripe (2%), ACH ($1-$1.50), or Check ($2). Tax withholding (10%) if earnings >$600/year in US.

---

## Appendix A: Database Migration Script

```python
# apps/api/migrations/versions/XXXXXX_add_phase4_payout_tables.py

from alembic import op
import sqlalchemy as sa
from datetime import datetime

def upgrade():
    # Create PayoutSchedule
    op.create_table(
        'payout_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('frequency', sa.String(20), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=True),
        sa.Column('day_of_month', sa.Integer(), nullable=True),
        sa.Column('cutoff_day_time', sa.String(20), nullable=False),
        sa.Column('payout_time', sa.String(20), nullable=False),
        sa.Column('eligible_partner_types', sa.String(200), nullable=False),
        sa.Column('eligible_statuses', sa.String(200), nullable=False),
        sa.Column('min_amount_cents', sa.Integer(), default=0),
        sa.Column('hold_period_days', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_payout_schedule_name')
    )
    
    # Create PayoutBatch
    op.create_table(
        'payout_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('batch_number', sa.String(50), nullable=False, unique=True),
        sa.Column('schedule_id', sa.Integer(), nullable=False),
        # ... (continued)
    )
    
    # Create CommissionPayout
    op.create_table(
        'commission_payouts',
        # ... (continued)
    )
    
    # Create indexes
    op.create_index('idx_payout_batch_schedule_status', 'payout_batches', ['schedule_id', 'status'])
    op.create_index('idx_commission_payout_batch_payee', 'commission_payouts', ['batch_id', 'payee_id'])
    op.create_index('idx_affiliate_earning_status', 'affiliate_earnings', ['status', 'created_at'])

def downgrade():
    op.drop_table('commission_payouts')
    op.drop_table('payout_batches')
    op.drop_table('payout_schedules')
```

---

**Document Version:** 1.0  
**Last Updated:** April 2026  
**Status:** Phase 4 Design Complete - Ready for Implementation  
**Owner:** Engineering Team  
**Next Review:** Upon Phase 4 Implementation Completion
