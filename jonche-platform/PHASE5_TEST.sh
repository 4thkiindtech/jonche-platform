#!/bin/bash
# Quick start guide for Phase 5 payment testing

echo "======================================"
echo "JONCHE Phase 5 Payment Integration"
echo "======================================"
echo ""

# Check environment
echo "1. Verifying environment configuration..."
if [ -z "$STRIPE_PUBLIC_KEY" ]; then
    echo "❌ STRIPE_PUBLIC_KEY not set"
    echo "   Add to .env: STRIPE_PUBLIC_KEY=pk_test_..."
else
    echo "✅ STRIPE_PUBLIC_KEY configured"
fi

if [ -z "$STRIPE_SECRET_KEY" ]; then
    echo "❌ STRIPE_SECRET_KEY not set"
    echo "   Add to .env: STRIPE_SECRET_KEY=sk_test_..."
else
    echo "✅ STRIPE_SECRET_KEY configured"
fi

if [ -z "$STRIPE_WEBHOOK_SECRET" ]; then
    echo "❌ STRIPE_WEBHOOK_SECRET not set"
    echo "   Add to .env: STRIPE_WEBHOOK_SECRET=whsec_..."
else
    echo "✅ STRIPE_WEBHOOK_SECRET configured"
fi

echo ""
echo "2. Starting development server..."
echo "   Run: make dev"
echo ""

echo "3. Test Payment Flow:"
echo "   a) Login to retailer portal: http://localhost:5000/retailer"
echo "   b) Create new order:"
echo "      - Select warehouse (Apliiq or Shoe)"
echo "      - Select items"
echo "      - Enter shipping info"
echo "      - Click 'Submit Order'"
echo "   c) Payment modal will appear"
echo "   d) Use Stripe test card:"
echo "      Card: 4242 4242 4242 4242"
echo "      Exp: 12/25"
echo "      CVC: 123"
echo "   e) Verify:"
echo "      - Order status changes to 'confirmed'"
echo "      - Payment status changes to 'paid'"
echo "      - Inventory is deducted"
echo "      - Confirmation email in logs"
echo ""

echo "4. Test Payment Failure:"
echo "   Use Stripe test card: 4000 0000 0000 0002"
echo "   Expected:"
echo "   - Payment fails with error"
echo "   - Order remains 'pending' with 'unpaid' status"
echo "   - Inventory is released"
echo "   - Failure email in logs"
echo ""

echo "5. API Endpoints to Test:"
echo "   POST /api/store-orders/place-order"
echo "      - Creates order with 'pending' status"
echo ""
echo "   POST /api/store-orders/{id}/payment-intent"
echo "      - Creates Stripe PaymentIntent"
echo "      - Requires Bearer token"
echo ""
echo "   GET /api/store-orders/{id}/payment-status"
echo "      - Returns payment status"
echo ""
echo "   POST /api/payments/webhook"
echo "      - Handles Stripe webhooks"
echo "      - Verifies signature"
echo ""

echo "6. Check Logs:"
echo "   - Payment processing: API stdout"
echo "   - Email notifications: Check logs for email content"
echo "   - Webhook delivery: Stripe dashboard"
echo ""

echo "======================================"
echo "Ready to test! Run: make dev"
echo "======================================"
