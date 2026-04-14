"""apps/api/routes/orders.py — Orders and checkout lock engine (pending → confirmed)."""

from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from db import db
from db.models import Order, OrderItem, CheckoutLock, Drop
from middleware.auth import require_admin, require_member, require_admin_or_member

orders_bp = Blueprint("orders", __name__)

LOCK_DURATION_MINUTES = 8


# ── Checkout Lock ─────────────────────────────────────────────────────────────

@orders_bp.route("/lock", methods=["POST"])
@require_member
def create_lock():
    """Reserve a pair for 8 minutes while member checks out."""
    data = request.get_json()
    if not data or "drop_id" not in data or "size" not in data:
        return jsonify({"error": "drop_id and size required"}), 400

    drop = Drop.query.get_or_404(data["drop_id"])
    member = g.current_member

    if drop.status != "live":
        return jsonify({"error": "Drop is not currently live"}), 400

    # Check availability
    if drop.units_available <= 0:
        return jsonify({"error": "No units available"}), 409

    # Check purchase limit
    existing_orders = Order.query.filter_by(
        drop_id=drop.id, member_id=member.id, status="completed"
    ).count()
    if existing_orders >= drop.max_per_member:
        return jsonify({"error": f"Purchase limit of {drop.max_per_member} reached"}), 409

    # Release any expired locks from this member on this drop
    CheckoutLock.query.filter(
        CheckoutLock.drop_id == drop.id,
        CheckoutLock.member_id == member.id,
        CheckoutLock.status == "active",
    ).update({"status": "expired"})

    lock = CheckoutLock(
        drop_id=drop.id,
        member_id=member.id,
        size=data["size"],
        quantity=1,
        status="active",
        expires_at=datetime.utcnow() + timedelta(minutes=LOCK_DURATION_MINUTES),
    )
    db.session.add(lock)
    db.session.commit()

    return jsonify({
        "lock": lock.to_dict(),
        "drop": drop.to_dict(),
        "expires_in_seconds": LOCK_DURATION_MINUTES * 60,
    }), 201


@orders_bp.route("/lock/<int:lock_id>/release", methods=["POST"])
@require_member
def release_lock(lock_id):
    lock = CheckoutLock.query.get_or_404(lock_id)
    if lock.member_id != g.current_member.id:
        return jsonify({"error": "Not your lock"}), 403
    lock.status = "expired"
    db.session.commit()
    return jsonify({"message": "Lock released"})


# ── Orders ────────────────────────────────────────────────────────────────────

@orders_bp.route("/", methods=["POST"])
@require_member
def create_order():
    """
    Create a pending order after client creates a Stripe PaymentIntent.
    Use `/api/payments/drop-intent` for the full flow (recommended).
    """
    data = request.get_json()
    required = ["drop_id", "size", "lock_id", "shipping_name", "shipping_address", "stripe_payment_intent"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    drop = Drop.query.get_or_404(data["drop_id"])
    member = g.current_member

    # Validate lock
    lock = CheckoutLock.query.get(data["lock_id"])
    if not lock or lock.member_id != member.id or lock.drop_id != drop.id:
        return jsonify({"error": "Invalid lock"}), 400
    if lock.status != "active" or lock.is_expired:
        return jsonify({"error": "Lock expired — please restart checkout"}), 409

    existing = Order.query.filter_by(checkout_lock_id=lock.id).first()
    if existing:
        return jsonify({"order": existing.to_dict()}), 200

    # Create pending order (confirmed via Stripe webhook)
    order = Order(
        drop_id=drop.id,
        member_id=member.id,
        checkout_lock_id=lock.id,
        total_cents=drop.price,
        shipping_name=data["shipping_name"],
        shipping_address=data["shipping_address"],
        stripe_payment_intent=data["stripe_payment_intent"],
        status="pending",
    )
    db.session.add(order)
    db.session.flush()

    item = OrderItem(
        order_id=order.id,
        size=data["size"],
        quantity=1,
        unit_price=drop.price,
    )
    db.session.add(item)

    db.session.commit()

    return jsonify({"order": order.to_dict()}), 201


@orders_bp.route("/", methods=["GET"])
@require_admin_or_member
def list_orders():
    status = request.args.get("status")
    q = Order.query
    
    # If member, show only their orders
    if hasattr(g, 'current_member') and g.current_member:
        q = q.filter_by(member_id=g.current_member.id)
    # If admin, show all orders
    
    if status:
        q = q.filter_by(status=status)
    orders = q.order_by(Order.created_at.desc()).limit(100).all()
    return jsonify([o.to_dict() for o in orders])


@orders_bp.route("/my-orders", methods=["GET"])
@require_member
def my_orders():
    orders = Order.query.filter_by(
        member_id=g.current_member.id
    ).order_by(Order.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders])


@orders_bp.route("/<order_number>", methods=["GET"])
@require_member
def get_order(order_number):
    order = Order.query.filter_by(order_number=order_number).first()
    if not order:
        return jsonify({"error": "Order not found"}), 404
    if order.member_id != g.current_member.id:
        return jsonify({"error": "Access denied"}), 403
    return jsonify(order.to_dict())


@orders_bp.route("/<int:order_id>/ship", methods=["POST"])
@require_admin
def mark_shipped(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.get_json() or {}
    order.shipped_at = datetime.utcnow()
    order.tracking_number = data.get("tracking_number")
    db.session.commit()
    return jsonify(order.to_dict())
