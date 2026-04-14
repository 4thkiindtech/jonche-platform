# 🚫 Manufacturer Communication Suppression

**Date:** April 14, 2026  
**Feature:** Prevent manufacturers/fulfillment partners from sending direct emails to customers

---

## 📋 Overview

Jonche is the **sole communicator** with end customers. Manufacturers, distributors, and shipping carriers are **not permitted** to send direct emails or messages to customers.

### Why This Matters

- **Brand Control:** All customer communication comes from Jonche (unified brand voice)
- **Support Efficiency:** All customer inquiries funnel through Jonche support
- **Customer Experience:** One trusted sender instead of multiple external parties
- **Data Privacy:** Customers' contact info stays private from manufacturers
- **Relationship Control:** Jonche maintains the customer relationship

---

## 🏗️ Architecture

### Communication Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     CUSTOMER (Guest or Member)                  │
└─────────────────────────────────────────────────────────────────┘
                               ▲
                               │
                    (Email/SMS only from Jonche)
                               │
┌─────────────────────────────────────────────────────────────────┐
│                      JONCHE PLATFORM                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ • Order confirmation                                     │  │
│  │ • Shipping notifications                                │  │
│  │ • Tracking updates                                      │  │
│  │ • Delivery confirmations                                │  │
│  │ • Support communications                                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
    ▲                                              ▲
    │                                              │
    │ (Data Only - NO direct customer contact)    │
    │                                              │
┌───┴──────────────┐                   ┌──────────┴──────┐
│  Manufacturer    │                   │  Shipping Cos.  │
│  • Send order    │                   │  (UPS/FedEx)    │
│    data via API  │                   │  • Send AWB     │
│  • NO emails     │                   │  • NO emails    │
│  • NO SMS        │                   │  • NO SMS       │
│  • NO contact    │                   │  • NO contact   │
└──────────────────┘                   └─────────────────┘
```

### Key Point
External partners interact **only with Jonche via API**. They never contact customers directly.

---

## 🔑 Implementation

### New Database Field

**Order Model - `suppress_manufacturer_emails`**

```python
suppress_manufacturer_emails = db.Column(db.Boolean, default=True)
```

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `suppress_manufacturer_emails` | Boolean | `True` | Manufacturer/partner emails are blocked |

### Set During Order Creation

When a guest or member completes checkout:

```python
order = Order(
    # ... other fields ...
    suppress_manufacturer_emails=True,  # Always True for customer orders
)
```

**This means:** The order is locked down. No external party can send email directly to the customer.

---

## 🔌 External Partner Integration

### Tracking Data Ingestion

External partners push tracking data via the public API:

**Endpoint:** `POST /api/guest/tracking/ingest`

#### Request Format

```json
{
  "order_id": 12345,
  "source": "apliiq",
  "status": "shipped",
  "tracking_number": "1Z999AA10123456784",
  "tracking_company": "UPS",
  "shipping_date": "2026-04-14T14:00:00Z",
  "delivery_date": "2026-04-16T17:00:00Z",
  "metadata": {
    "warehouse_location": "CA-WEST",
    "carrier_code": "UPS_GROUND",
    "estimated_delivery": "2026-04-16"
  }
}
```

#### Important Constraints

✅ **ALLOWED:**
- Send tracking data (order number, status, AWB)
- Update fulfillment status (in_production → shipped → delivered)
- Provide carrier information (UPS, FedEx, USPS)
- Estimated delivery dates

❌ **NOT ALLOWED:**
- Send emails to customer
- Send SMS to customer
- Contact customer directly
- Share customer email with third parties
- CC/BCC customer on any correspondence
- Forward customer requests elsewhere

### Response

```json
{
  "message": "Tracking data ingested",
  "tracking": {
    "id": 789,
    "order_id": 12345,
    "source": "apliiq",
    "status": "shipped",
    "tracking_number": "1Z999AA10123456784",
    "tracking_company": "UPS",
    "shipping_date": "2026-04-14T14:00:00Z",
    "delivery_date": "2026-04-16T17:00:00Z",
    "created_at": "2026-04-14T15:30:00Z"
  }
}
```

### Processing Pipeline

When Jonche receives tracking data:

```python
# 1. Validate order exists
order = Order.query.get(order_id)
if not order:
    return error  # Order not found

# 2. Check if manufacturer emails are suppressed
if order.suppress_manufacturer_emails:
    # YES - Proceed with data ingestion only
    # Do NOT call manufacturer systems to send emails
    pass

# 3. Create tracking record
tracking = OrderTracking(
    order_id=order_id,
    source=source,
    status=status,
    tracking_number=tracking_number,
    ...
)
db.session.add(tracking)

# 4. Update order status
if status == "shipped":
    order.shipped_at = datetime.utcnow()
if status == "delivered":
    order.status = "completed"

db.session.commit()

# 5. Send notification email TO CUSTOMER (not manufacturer)
notify_customer_of_shipment(order, tracking)  # Jonche sends email

# 6. Return success to partner
# Partner is now done - no further action needed
return {"message": "Tracking data ingested", ...}
```

---

## 📧 Customer Communication Examples

### Order Confirmation (From Jonche)
```
From: orders@jonche.com
To: customer@example.com

Subject: Order Confirmed - JNC-ABC12345

Thank you for your order!
...
Track your order: [unique link with token]
```

### Shipment Notification (From Jonche)
```
From: shipping@jonche.com
To: customer@example.com

Subject: Your Order Has Shipped! - JNC-ABC12345

Your order is on the way!
Carrier: UPS
Tracking: 1Z999AA10123456784
Expected Delivery: April 16
```

### Delivery Confirmation (From Jonche)
```
From: shipping@jonche.com
To: customer@example.com

Subject: Your Order Delivered - JNC-ABC12345

Your order was delivered on April 16, 2026
Signature: Not Required
```

**Note:** All examples show Jonche as sender, never the manufacturer

---

## 🔒 Data Privacy

### Customer Data Protection

| Data Point | Manufacturer Access | Distributor Access | Courier Access |
|-----------|-------------------|-------------------|----------------|
| Customer Name | ✅ YES (on order only) | ✅ YES (on order only) | ✅ YES (on delivery) |
| Customer Email | ❌ NO (blocked) | ❌ NO (blocked) | ❌ NO (blocked) |
| Customer Phone | ❌ NO (blocked) | ❌ NO (blocked) | ❌ NO (blocked) |
| Customer Address | ✅ YES (shipping only) | ✅ YES (shipping only) | ✅ YES (delivery) |
| Order Total | ✅ YES (for invoicing) | ✅ YES (for invoicing) | ❌ NO |
| Product Details | ✅ YES (for fulfillment) | ✅ YES (for fulfillment) | ❌ NO |

### API Key Authentication (Future)

```
Authorization: Bearer partner_api_key_xyz123
```

Partners authenticate with API key, limiting their access to:
- Their own orders only
- Tracking data ingestion endpoint only
- No access to customer personal info beyond what's on the order

---

## 🚀 Implementation Checklist

- [x] Add `suppress_manufacturer_emails` field to Order model (default=True)
- [x] Include field in Order.to_dict() serialization
- [x] Set flag=True during order creation in store.py
- [x] Update tracking ingest endpoint docstring with clear guidelines
- [x] Add API-level comments preventing direct customer contact
- [x] Document data privacy matrix
- [ ] Implement API key authentication for partners (Bearer token)
- [ ] Add validation: reject requests trying to send customer emails
- [ ] Create partner integration docs (in separate wiki)
- [ ] Add audit logging for all tracking ingestions
- [ ] Implement email notification templates (order_confirmation, shipment_notification, delivery_confirmation)
- [ ] Add admin dashboard for monitoring partner data ingestions

---

## 📞 Partner Onboarding

### Required Agreements

When onboarding a new fulfillment partner:

1. ✅ **Review Communication Policy**
   - Manufacturer must acknowledge they will NOT contact customers directly
   - All communication happens through Jonche API

2. ✅ **API Integration Training**
   - Partner learns to use `/api/guest/tracking/ingest` endpoint only
   - No direct customer contact capabilities provided

3. ✅ **Data Usage Agreement**
   - Partner can only access order data sent explicitly
   - Customer email/phone not accessible via API
   - All data is for fulfillment purposes only

### Integration Checklist (Per Partner)

- [ ] Partner reviews communication guidelines
- [ ] API keys generated and activated
- [ ] Partner implements tracking data ingestion
- [ ] Test data sent and verified
- [ ] Partner agrees to suppress direct customer emails
- [ ] Live integration activated

---

## ⚠️ Troubleshooting

### "Partner Sent Email Directly to Customer"

**Action Items:**
1. Check if `suppress_manufacturer_emails=True` on order
2. Review customer's email logs for direct partner contact
3. Contact partner about policy violation
4. Add partner to blocklist if repeated

### "Customer Received Multiple Emails"

**Diagnosis:**
- If both Jonche + partner emails: Partner violated policy
- If multiple Jonche emails: Check notification system for duplicates

**Resolution:**
- Verify `suppress_manufacturer_emails=True` is enforced
- Add partner email domain to block list if needed
- Update partner integration to respect flag

---

## 📋 API Reference

### Tracking Ingest Endpoint

**POST `/api/guest/tracking/ingest`**

**Headers:**
```
Authorization: Bearer {api_key}  (future)
Content-Type: application/json
```

**Request Body:**
```json
{
  "order_id": 12345,
  "source": "apliiq|manufacturer|distributor|email_parse",
  "status": "pending|in_production|shipped|delivered",
  "tracking_number": "1Z999AA10123456784",
  "tracking_company": "UPS|FedEx|USPS",
  "shipping_date": "2026-04-14T14:00:00Z",
  "delivery_date": "2026-04-16T17:00:00Z",
  "metadata": {
    "warehouse": "CA-WEST",
    "carrier_code": "UPS_GROUND"
  }
}
```

**Success Response (201):**
```json
{
  "message": "Tracking data ingested",
  "tracking": { ... }
}
```

---

## 🎯 Summary

✅ **Jonche owns the customer relationship**
✅ **All communication goes through Jonche**
✅ **Partners send data only via API**
✅ **No direct manufacturer/partner emails to customers**
✅ **Customer data privacy protected**
✅ **Unified brand experience for customers**

**Key Flag:** `suppress_manufacturer_emails = True` (always for guest orders)

