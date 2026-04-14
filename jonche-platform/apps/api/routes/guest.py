"""
New API routes for guest checkout support:
- Guest order creation
- Guest order lookup by token
- Newsletter signup
- External tracking ingestion from fulfillment partners
"""

from flask import Blueprint, request, jsonify, g
from db import db
from db.models import Order, GuestOrderLookup, EmailSubscriber, OrderTracking
from datetime import datetime
import secrets
import json

guest_bp = Blueprint("guest", __name__)


# ── Guest Order Lookup ─────────────────────────────────────────────────────

@guest_bp.route("/orders/<lookup_token>", methods=["GET"])
def get_guest_order(lookup_token):
    """
    Public endpoint for guests to look up their order by token.
    No authentication required.
    """
    lookup = GuestOrderLookup.query.filter_by(lookup_token=lookup_token).first()
    if not lookup:
        return jsonify({"error": "Order not found"}), 404

    order = Order.query.get(lookup.order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    # Verify email if provided
    guest_email = request.args.get("email", "").strip().lower()
    if guest_email and guest_email != order.shipping_email.lower():
        return jsonify({"error": "Email mismatch"}), 403

    return jsonify(order.to_dict()), 200


# ── Newsletter Signup ──────────────────────────────────────────────────────

@guest_bp.route("/newsletter/subscribe", methods=["POST"])
def subscribe_newsletter():
    """
    Optional newsletter signup (not forced).
    Can be called by guests or members after checkout.
    """
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()

    if not email or "@" not in email:
        return jsonify({"error": "Invalid email"}), 400

    # Check if already subscribed
    subscriber = EmailSubscriber.query.filter_by(email=email).first()
    if subscriber:
        subscriber.subscribed = True
        subscriber.category = data.get("category", "newsletter")
        db.session.commit()
        return jsonify({
            "message": "Already subscribed",
            "subscriber": subscriber.to_dict()
        }), 200

    # Create new subscription
    subscriber = EmailSubscriber(
        email=email,
        subscribed=True,
        category=data.get("category", "newsletter"),
    )
    db.session.add(subscriber)
    db.session.commit()

    return jsonify({
        "message": "Subscribed successfully",
        "subscriber": subscriber.to_dict()
    }), 201


@guest_bp.route("/newsletter/unsubscribe", methods=["POST"])
def unsubscribe_newsletter():
    """Unsubscribe from newsletter"""
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()

    subscriber = EmailSubscriber.query.filter_by(email=email).first()
    if not subscriber:
        return jsonify({"error": "Not subscribed"}), 404

    subscriber.subscribed = False
    db.session.commit()

    return jsonify({"message": "Unsubscribed"}), 200


# ── External Tracking Ingestion ────────────────────────────────────────────

@guest_bp.route("/tracking/ingest", methods=["POST"])
def ingest_tracking_data():
    """
    Endpoint for external fulfillment partners (Apliiq, distributors, manufacturers)
    to push tracking updates.
    
    IMPORTANT: This endpoint is for DATA INGESTION ONLY.
    Partners must NOT send emails directly to customers.
    Jonche handles all customer communication based on suppress_manufacturer_emails flag.
    
    Can include:
    - Tracking numbers from carriers (UPS, FedEx, USPS)
    - Status updates (in_production, shipped, delivered)
    - Shipping dates and expected delivery dates
    
    Supports API key authentication (bearer token).
    
    Flow:
    1. Partner sends tracking data to this endpoint
    2. Jonche stores the tracking record
    3. Jonche sends notification email to customer (never the partner)
    4. If suppress_manufacturer_emails=True on order, DO NOT forward to partner systems
    """
    # TODO: Implement API key authentication
    # auth_header = request.headers.get("Authorization", "")
    # if not auth_header.startswith("Bearer "):
    #     return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    
    # Required fields
    required = ["order_id", "source", "status"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    order_id = data.get("order_id")
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    # Check if customer wants to suppress manufacturer communications
    if order.suppress_manufacturer_emails:
        # This order has suppress_manufacturer_emails=True
        # Proceed with data ingestion, but DO NOT forward communications to partner systems
        pass

    # Create or update tracking record
    tracking = OrderTracking(
        order_id=order_id,
        source=data.get("source"),  # apliiq/manufacturer/distributor/email_parse
        status=data.get("status"),  # pending/in_production/shipped/delivered
        tracking_number=data.get("tracking_number"),
        tracking_company=data.get("tracking_company"),
        shipping_date=_parse_iso_date(data.get("shipping_date")),
        delivery_date=_parse_iso_date(data.get("delivery_date")),
        metadata=json.dumps(data.get("metadata", {})) if data.get("metadata") else None,
    )
    
    db.session.add(tracking)
    
    # Update order status if tracking status is more advanced
    if data.get("status") == "shipped" and not order.shipped_at:
        order.shipped_at = datetime.utcnow()
    if data.get("status") == "delivered":
        order.status = "completed"
    if data.get("tracking_number") and not order.tracking_number:
        order.tracking_number = data.get("tracking_number")
    
    db.session.commit()

    # TODO: Send notification email to customer
    # notify_customer_of_shipment(order, tracking)

    return jsonify({
        "message": "Tracking data ingested",
        "tracking": tracking.to_dict()
    }), 201


@guest_bp.route("/tracking/<int:order_id>", methods=["GET"])
def get_order_tracking(order_id):
    """
    Get all tracking updates for an order.
    Guests can access using order ID + lookup token OR email verification.
    """
    lookup_token = request.args.get("token", "")
    guest_email = request.args.get("email", "").strip().lower()

    # Verify access
    if lookup_token:
        lookup = GuestOrderLookup.query.filter_by(lookup_token=lookup_token).first()
        if not lookup or lookup.order_id != order_id:
            return jsonify({"error": "Invalid token"}), 403
    elif guest_email:
        order = Order.query.get(order_id)
        if not order or not order.shipping_email or order.shipping_email.lower() != guest_email:
            return jsonify({"error": "Email verification failed"}), 403
    else:
        return jsonify({"error": "Authentication required (token or email)"}), 401

    # Get all tracking updates for this order
    tracking_records = OrderTracking.query.filter_by(order_id=order_id).order_by(
        OrderTracking.created_at.desc()
    ).all()

    return jsonify({
        "order_id": order_id,
        "tracking": [t.to_dict() for t in tracking_records]
    }), 200


def _parse_iso_date(date_str):
    """Parse ISO 8601 date string to datetime"""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
