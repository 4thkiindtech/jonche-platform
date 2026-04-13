# Phase 5 API Documentation: Store Order Payments

## Overview
Complete Stripe payment integration for store orders with retailer-facing endpoints and webhook handlers.

---

## Endpoints

### 1. Create Payment Intent
**POST** `/api/store-orders/{order_id}/payment-intent`

Create a Stripe PaymentIntent for a store order. Only available to the order's retailer.

#### Requirements
- Authentication: Bearer token (retailer)
- Order Status: `pending`
- Payment Status: `unpaid`

#### Response (200 OK)
```json
{
  "client_secret": "pi_1234_secret_5678",
  "order_id": 42,
  "amount_cents": 50000,
  "currency": "usd"
}
```

#### Error Responses
| Code | Reason |
|------|--------|
| 400 | Order not in pending status / Payment already in progress |
| 403 | Not authorized (trying to pay another retailer's order) |
| 404 | Order not found |
| 500 | Stripe API error |

#### Example Request
```bash
curl -X POST http://localhost:5001/api/store-orders/42/payment-intent \
  -H "Authorization: Bearer RETAILER_TOKEN" \
  -H "Content-Type: application/json"
```

---

### 2. Get Payment Status
**GET** `/api/store-orders/{order_id}/payment-status`

Retrieve payment information for a store order. Only available to the order's retailer.

#### Requirements
- Authentication: Bearer token (retailer)

#### Response (200 OK)
```json
{
  "order_id": 42,
  "payment_status": "paid",
  "stripe_payment_intent": "pi_1234_secret_5678",
  "payment_completed_at": "2024-01-15T10:30:00Z",
  "invoice_url": "https://invoice.stripe.com/..."
}
```

#### Error Responses
| Code | Reason |
|------|--------|
| 403 | Not authorized |
| 404 | Order not found |

#### Example Request
```bash
curl -X GET http://localhost:5001/api/store-orders/42/payment-status \
  -H "Authorization: Bearer RETAILER_TOKEN"
```

---

### 3. Stripe Webhook
**POST** `/api/payments/webhook`

Handle Stripe webhook events. Signature validated automatically.

#### Supported Events

**payment_intent.succeeded**
- Created by: `stripe.confirmCardPayment()` after card is charged
- Metadata: `{"type": "store_order", "order_id": "42", "order_number": "SO-001"}`
- Action: Calls `finalize_store_order()`
  - Updates `status` → "confirmed"
  - Updates `payment_status` → "paid"
  - Sets `payment_completed_at`
  - Deducts reserved inventory
  - Sends confirmation email

**payment_intent.payment_failed**
- Created by: Stripe when payment declined
- Metadata: Same as succeeded
- Action: Calls `mark_store_order_payment_failed()`
  - Updates `payment_status` → "failed"
  - Releases reserved inventory
  - Sends failure email

#### Response (200 OK)
```json
{
  "ok": true
}
```

#### Example Webhook Payload
```json
{
  "type": "payment_intent.succeeded",
  "data": {
    "object": {
      "id": "pi_1234_secret_5678",
      "status": "succeeded",
      "amount_received": 50000,
      "metadata": {
        "type": "store_order",
        "order_id": "42",
        "order_number": "SO-001"
      }
    }
  }
}
```

---

## Payment Flow Diagram

```
┌─ Retailer Portal ──────────────────────────────────────────┐
│                                                             │
│  1. Create Order                                            │
│     POST /api/store-orders/place-order                      │
│     └─ Returns: StoreOrder with status=pending              │
│                                                             │
│  2. Show Payment Modal                                      │
│     - Amount: order.total_cents / 100                       │
│     - Card form ready                                       │
│                                                             │
│  3. Retailer Enters Card                                    │
│     - Stripe Elements validates in real-time               │
│     - No card data sent to server                          │
│                                                             │
│  4. Submit Payment                                          │
│     - POST /api/store-orders/{id}/payment-intent            │
│     - Returns: client_secret for Stripe                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           ↓
         stripe.confirmCardPayment(client_secret)
                           ↓
┌─ Stripe Gateway ───────────────────────────────────────────┐
│                                                             │
│  5. Process Card                                            │
│     - Charge customer card                                 │
│     - Return PaymentIntent status                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           ↓
        Stripe Webhook: payment_intent.succeeded
                           ↓
┌─ Backend API ──────────────────────────────────────────────┐
│                                                             │
│  6. Handle Webhook                                          │
│     - Verify HMAC signature                                │
│     - Extract: payment_intent_id from event                │
│     - Query: StoreOrder by stripe_payment_intent           │
│                                                             │
│  7. Finalize Order                                          │
│     - status → "confirmed"                                 │
│     - payment_status → "paid"                              │
│     - Deduct inventory                                      │
│     - Send confirmation email                              │
│     - Notification to admin                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Order Status Transitions

```
Create Order
    ↓
pending + unpaid
    ↓
[Customer pays]
    ↓
confirmed + paid → in_fulfillment → shipped → completed
    ↓
[If payment fails]
    ↓
pending + failed (retry possible)
```

---

## Database Schema

### StoreOrder Payment Fields
```sql
-- Column          | Type        | Notes
stripe_payment_intent | VARCHAR(255) | Stripe PaymentIntent ID
payment_status    | VARCHAR(50)  | unpaid|pending|paid|failed|refunded
payment_completed_at | DATETIME   | When payment succeeded
invoice_url       | VARCHAR(500) | Stripe invoice link
```

---

## Security Considerations

### 1. Authentication
- All retailer endpoints require Bearer token
- Token validated in `require_retailer` middleware
- Order ownership verified before payment processing

### 2. Webhook Validation
- HMAC-SHA256 signature verified with `STRIPE_WEBHOOK_SECRET`
- Prevents replay attacks
- Rejects unsigned requests

### 3. PCI Compliance
- Card data never touches server
- Stripe Elements handles card input
- Only client_secret passed to frontend

### 4. Idempotency
- Payment intent creation idempotent via key: `store-order-{order_id}`
- Prevents duplicate charges on network retry

### 5. Inventory Protection
- Inventory reserved (not deducted) when order created
- Only deducted after payment confirmed
- Released if payment fails

---

## Error Handling

### Frontend
```javascript
stripe.confirmCardPayment(clientSecret)
  .then(result => {
    if (result.error) {
      // Show: result.error.message
      // User can retry
    } else if (result.paymentIntent.status === 'succeeded') {
      // Show success message
      // Redirect to orders
    }
  })
```

### Backend
```python
try:
    pi = create_payment_intent(...)
    order.stripe_payment_intent = pi["id"]
    db.session.commit()
except StripeError as e:
    return jsonify({"error": str(e)}), 502
except Exception as e:
    db.session.rollback()
    return jsonify({"error": str(e)}), 500
```

---

## Configuration

Required environment variables in `.env`:
```
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_CURRENCY=usd
```

---

## Testing

### Stripe Test Cards
| Card | Use Case | Result |
|------|----------|--------|
| 4242 4242 4242 4242 | Successful payment | Charge succeeds |
| 4000 0000 0000 0002 | Declined card | Charge fails |
| 4000 0025 0000 3155 | 3D Secure required | Authentication required |

All test cards:
- Any future expiry date
- Any 3-digit CVC
- Any cardholder name

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Payment system not configured" | Set STRIPE_PUBLIC_KEY in .env |
| "Webhook signature invalid" | Verify STRIPE_WEBHOOK_SECRET matches |
| "Not authorized" | Check order belongs to authenticated retailer |
| "Order already has payment in progress" | Wait for previous payment to fail or retry |
| Payment shows "pending" forever | Check webhook delivery in Stripe dashboard |

---

## Future Enhancements

- [ ] Partial refunds
- [ ] Invoice customization
- [ ] Recurring payments
- [ ] Payment plan options
- [ ] Multi-currency support
- [ ] Payment reconciliation dashboard
