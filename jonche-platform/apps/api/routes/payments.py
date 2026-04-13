"""apps/api/routes/payments.py — Stripe PaymentIntents + webhook confirmation."""

from __future__ import annotations

import os

from flask import Blueprint, request, jsonify, g
from db import db
from db.models import Order, OrderItem, CheckoutLock, Drop, PreOrder, StoreOrder
from middleware.auth import require_admin, require_member
from services.stripe_client import (
    StripeError,
    create_payment_intent,
    create_refund,
    verify_webhook_signature,
)
from services.order_finalizer import finalize_order, mark_refunded
from services.store_order_finalizer import finalize_store_order, mark_store_order_payment_failed

payments_bp = Blueprint("payments", __name__)


def _currency() -> str:
    return (os.getenv("STRIPE_CURRENCY") or "usd").strip().lower()


@payments_bp.route("/drop-intent", methods=["POST"])
@require_member
def create_drop_intent():
    """
    Creates/returns a PaymentIntent for a member drop purchase and creates a pending Order.
    Requires an active checkout lock.
    """
    data = request.get_json() or {}
    required = ["drop_id", "lock_id", "size", "shipping_name", "shipping_address"]
    for f in required:
        if f not in data:
            return jsonify({"error": f"Missing field: {f}"}), 400

    drop = Drop.query.get_or_404(int(data["drop_id"]))

    lock = CheckoutLock.query.get(int(data["lock_id"]))
    if not lock:
        return jsonify({"error": "Lock not found"}), 404
    if lock.member_id != g.current_member.id:
        return jsonify({"error": "Not your lock"}), 403
    if lock.drop_id != drop.id or lock.size != str(data["size"]):
        return jsonify({"error": "Lock does not match drop/size"}), 400
    if lock.status != "active" or lock.is_expired:
        return jsonify({"error": "Lock expired — please restart checkout"}), 409
    if drop.status != "live":
        return jsonify({"error": "Drop is not live"}), 400

    # Purchase limit enforcement (completed orders)
    existing_completed = Order.query.filter_by(
        drop_id=drop.id, member_id=g.current_member.id, status="completed"
    ).count()
    if existing_completed >= drop.max_per_member:
        return jsonify({"error": f"Purchase limit of {drop.max_per_member} reached"}), 409

    # One pending order per lock
    existing = Order.query.filter_by(checkout_lock_id=lock.id).first()
    if existing and existing.stripe_payment_intent:
        return jsonify({"order": existing.to_dict(), "payment_intent": existing.stripe_payment_intent}), 200

    # Create Stripe PaymentIntent
    try:
        pi = create_payment_intent(
            amount_cents=drop.price,
            currency=_currency(),
            description=f"JONCHE Drop — {drop.slug}",
            receipt_email=g.current_member.email,
            metadata={
                "type": "drop",
                "drop_id": str(drop.id),
                "lock_id": str(lock.id),
            },
            idempotency_key=f"drop-{drop.id}-lock-{lock.id}",
        )
    except StripeError as e:
        return jsonify({"error": str(e)}), 502

    # Create pending order bound to lock + intent
    order = existing or Order(
        drop_id=drop.id,
        member_id=g.current_member.id,
        checkout_lock_id=lock.id,
        total_cents=drop.price,
        shipping_name=data["shipping_name"],
        shipping_address=data["shipping_address"],
        stripe_payment_intent=pi.get("id"),
        status="pending",
    )
    db.session.add(order)
    db.session.flush()

    if not order.items:
        db.session.add(OrderItem(
            order_id=order.id,
            size=str(data["size"]),
            quantity=1,
            unit_price=drop.price,
        ))

    db.session.commit()

    return jsonify({
        "order": order.to_dict(),
        "payment_intent": {
            "id": pi.get("id"),
            "client_secret": pi.get("client_secret"),
            "status": pi.get("status"),
        },
    }), 201


@payments_bp.route("/preorder-intent", methods=["POST"])
def create_preorder_intent():
    """
    Creates a PaymentIntent for a preorder deposit (public).
    Requires `preorder_id` and matching `email`.
    """
    data = request.get_json() or {}
    required = ["preorder_id", "email"]
    for f in required:
        if f not in data:
            return jsonify({"error": f"Missing field: {f}"}), 400

    preorder = PreOrder.query.get_or_404(int(data["preorder_id"]))
    if preorder.email.lower() != str(data["email"]).strip().lower():
        return jsonify({"error": "Email does not match preorder"}), 403

    amount = int(data.get("amount_cents") or preorder.deposit_cents or 0)
    if amount <= 0:
        return jsonify({"error": "Deposit amount must be > 0"}), 400

    if preorder.stripe_payment_intent:
        return jsonify({"preorder": preorder.to_dict(), "payment_intent": preorder.stripe_payment_intent}), 200

    try:
        pi = create_payment_intent(
            amount_cents=amount,
            currency=_currency(),
            description=f"JONCHE Preorder Deposit — drop {preorder.drop_id}",
            receipt_email=preorder.email,
            metadata={
                "type": "preorder",
                "preorder_id": str(preorder.id),
                "drop_id": str(preorder.drop_id),
            },
            idempotency_key=f"preorder-{preorder.id}",
        )
    except StripeError as e:
        return jsonify({"error": str(e)}), 502

    preorder.stripe_payment_intent = pi.get("id")
    db.session.commit()

    return jsonify({
        "preorder": preorder.to_dict(),
        "payment_intent": {
            "id": pi.get("id"),
            "client_secret": pi.get("client_secret"),
            "status": pi.get("status"),
        },
    }), 201


@payments_bp.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.get_data() or b""
    sig = request.headers.get("Stripe-Signature", "")
    secret = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()

    if secret:
        if not verify_webhook_signature(payload, sig, secret):
            return jsonify({"error": "Invalid signature"}), 400

    try:
        event = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    event_type = event.get("type")
    obj = (event.get("data") or {}).get("object") or {}

    if event_type == "payment_intent.succeeded":
        pi_id = obj.get("id")
        if not pi_id:
            return jsonify({"ok": True}), 200

        # Drop order confirmation
        order = Order.query.filter_by(stripe_payment_intent=pi_id).first()
        if order and order.status == "pending":
            finalize_order(order)

        # Store order confirmation
        metadata = obj.get("metadata") or {}
        if metadata.get("type") == "store_order":
            store_order = StoreOrder.query.filter_by(stripe_payment_intent=pi_id).first()
            if store_order and store_order.payment_status == "pending":
                finalize_store_order(store_order)

        # Preorder confirmation
        if metadata.get("type") == "preorder":
            pid = metadata.get("preorder_id")
            if pid:
                preorder = PreOrder.query.get(int(pid))
                if preorder and preorder.status == "pending":
                    preorder.status = "confirmed"
                    db.session.commit()

        return jsonify({"ok": True}), 200

    if event_type in ("charge.refunded", "payment_intent.payment_failed"):
        pi_id = obj.get("payment_intent") or obj.get("id")
        if pi_id:
            order = Order.query.filter_by(stripe_payment_intent=pi_id).first()
            if order:
                mark_refunded(order) if event_type == "charge.refunded" else None
            
            # Handle store order failures
            store_order = StoreOrder.query.filter_by(stripe_payment_intent=pi_id).first()
            if store_order and event_type == "payment_intent.payment_failed":
                reason = obj.get("last_payment_error", {}).get("message") or "Payment failed"
                mark_store_order_payment_failed(store_order, reason)
        
        return jsonify({"ok": True}), 200

    return jsonify({"ok": True}), 200


@payments_bp.route("/orders/<int:order_id>/refund", methods=["POST"])
@require_admin
def refund_order(order_id: int):
    """
    Admin refund helper: creates a Stripe refund (if configured) and marks the order refunded.
    """
    order = Order.query.get_or_404(order_id)
    if not order.stripe_payment_intent:
        return jsonify({"error": "Order has no Stripe PaymentIntent"}), 400

    data = request.get_json() or {}
    amount = data.get("amount_cents")
    reason = data.get("reason")

    try:
        create_refund(payment_intent_id=order.stripe_payment_intent, amount_cents=amount, reason=reason)
    except StripeError as e:
        return jsonify({"error": str(e)}), 502

    mark_refunded(order)
    return jsonify(order.to_dict())


@payments_bp.route("/dev/confirm-intent", methods=["POST"])
@require_admin
def dev_confirm_intent():
    """
    Dev-only helper to finalize an order without calling Stripe.
    Enabled only when FLASK_ENV != production.
    """
    if (os.getenv("FLASK_ENV") or "development") == "production":
        return jsonify({"error": "Not allowed in production"}), 403

    data = request.get_json() or {}
    pi_id = data.get("payment_intent")
    if not pi_id:
        return jsonify({"error": "payment_intent required"}), 400

    order = Order.query.filter_by(stripe_payment_intent=pi_id).first()
    if not order:
        return jsonify({"error": "Order not found for payment_intent"}), 404
    out = finalize_order(order)
    return jsonify({
        "order": out["order"].to_dict(),
        "certificate": out["certificate"].to_dict() if out.get("certificate") else None,
    })
