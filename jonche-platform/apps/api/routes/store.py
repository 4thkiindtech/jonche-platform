"""apps/api/routes/store.py — Shopping cart and store checkout."""

import secrets
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g

from db import db
from db.models import Cart, CartItem, Product, ProductVariant, Member
from middleware.auth import require_member

store_bp = Blueprint("store", __name__)

CART_SESSION_COOKIE = "jonche_cart_session"
CART_EXPIRY_DAYS = 30


def _get_or_create_session_token():
    """Get cart session token from cookies or create new one."""
    token = request.cookies.get(CART_SESSION_COOKIE)
    if not token:
        token = secrets.token_hex(32)
    return token


def _get_cart(cart_id=None, session_token=None, member_id=None):
    """Get a cart by ID, session token, or member."""
    if cart_id:
        return Cart.query.get(cart_id)
    if session_token:
        return Cart.query.filter_by(session_token=session_token, status="active").first()
    if member_id:
        return Cart.query.filter_by(member_id=member_id, status="active").first()
    return None


# ── Get or Create Cart ─────────────────────────────────────────────────────

@store_bp.route("/cart", methods=["GET"])
def get_cart():
    """
    Get current cart.
    For members: retrieves their active cart.
    For guests: retrieves cart by session token from cookie.
    """
    cart = None

    if hasattr(g, "current_member") and g.current_member:
        # Member cart
        cart = _get_cart(member_id=g.current_member.id)
    else:
        # Guest cart
        session_token = request.cookies.get(CART_SESSION_COOKIE)
        if session_token:
            cart = _get_cart(session_token=session_token)

    if not cart:
        return jsonify({"items": [], "total_cents": 0, "total_dollars": 0, "item_count": 0}), 200

    return jsonify(cart.to_dict(include_items=True)), 200


@store_bp.route("/cart/init", methods=["POST"])
def init_cart():
    """Initialize a new cart for guests or get existing member cart."""
    if hasattr(g, "current_member") and g.current_member:
        # For members, check if cart exists
        cart = _get_cart(member_id=g.current_member.id)
        if cart:
            return jsonify(cart.to_dict(include_items=True)), 200

        # Create new member cart
        cart = Cart(
            member_id=g.current_member.id,
            status="active",
            expires_at=datetime.utcnow() + timedelta(days=CART_EXPIRY_DAYS),
        )
    else:
        # For guests, create session cart
        session_token = _get_or_create_session_token()
        cart = Cart(
            session_token=session_token,
            status="active",
            expires_at=datetime.utcnow() + timedelta(days=CART_EXPIRY_DAYS),
        )

    db.session.add(cart)
    db.session.commit()

    return jsonify(cart.to_dict(include_items=True)), 201


# ── Add/Remove Items ───────────────────────────────────────────────────────

@store_bp.route("/cart/items", methods=["POST"])
def add_to_cart():
    """Add item to cart."""
    data = request.get_json()
    required = ["product_id", "quantity"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Get or create cart
    if hasattr(g, "current_member") and g.current_member:
        cart = _get_cart(member_id=g.current_member.id)
        if not cart:
            cart = Cart(
                member_id=g.current_member.id,
                status="active",
                expires_at=datetime.utcnow() + timedelta(days=CART_EXPIRY_DAYS),
            )
            db.session.add(cart)
            db.session.flush()
    else:
        session_token = request.cookies.get(CART_SESSION_COOKIE) or _get_or_create_session_token()
        cart = _get_cart(session_token=session_token)
        if not cart:
            cart = Cart(
                session_token=session_token,
                status="active",
                expires_at=datetime.utcnow() + timedelta(days=CART_EXPIRY_DAYS),
            )
            db.session.add(cart)
            db.session.flush()

    # Validate product
    product = Product.query.get_or_404(data["product_id"])
    if not product.is_available:
        return jsonify({"error": "Product not available"}), 400

    # Validate variant if provided
    variant_id = data.get("variant_id")
    variant = None
    if variant_id:
        variant = ProductVariant.query.get_or_404(variant_id)
        if variant.product_id != product.id:
            return jsonify({"error": "Variant not found on this product"}), 400
        if variant.quantity_in_stock <= 0:
            return jsonify({"error": "Variant out of stock"}), 400

    # Get price
    unit_price_cents = variant.price if variant else product.base_price

    # Check if item already in cart
    existing_item = CartItem.query.filter_by(
        cart_id=cart.id,
        product_id=product.id,
        variant_id=variant_id,
    ).first()

    if existing_item:
        # Update quantity
        existing_item.quantity += int(data["quantity"])
    else:
        # Add new item
        item = CartItem(
            cart_id=cart.id,
            product_id=product.id,
            variant_id=variant_id,
            quantity=int(data["quantity"]),
            unit_price_cents=unit_price_cents,
        )
        db.session.add(item)

    cart.updated_at = datetime.utcnow()
    db.session.commit()

    response = jsonify(cart.to_dict(include_items=True))
    # Set session cookie for guests
    if not (hasattr(g, "current_member") and g.current_member):
        response.set_cookie(CART_SESSION_COOKIE, cart.session_token, max_age=30*24*3600)
    return response, 200


@store_bp.route("/cart/items/<int:item_id>", methods=["PUT"])
def update_cart_item(item_id):
    """Update item quantity in cart."""
    item = CartItem.query.get_or_404(item_id)

    # Verify ownership
    cart = item.cart
    if hasattr(g, "current_member") and g.current_member:
        if cart.member_id != g.current_member.id:
            return jsonify({"error": "Unauthorized"}), 403
    else:
        if cart.session_token != request.cookies.get(CART_SESSION_COOKIE):
            return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    if "quantity" in data:
        quantity = int(data["quantity"])
        if quantity <= 0:
            db.session.delete(item)
        else:
            item.quantity = quantity
    
    cart.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(cart.to_dict(include_items=True)), 200


@store_bp.route("/cart/items/<int:item_id>", methods=["DELETE"])
def remove_cart_item(item_id):
    """Remove item from cart."""
    item = CartItem.query.get_or_404(item_id)

    # Verify ownership
    cart = item.cart
    if hasattr(g, "current_member") and g.current_member:
        if cart.member_id != g.current_member.id:
            return jsonify({"error": "Unauthorized"}), 403
    else:
        if cart.session_token != request.cookies.get(CART_SESSION_COOKIE):
            return jsonify({"error": "Unauthorized"}), 403

    db.session.delete(item)
    cart.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(cart.to_dict(include_items=True)), 200


@store_bp.route("/cart/clear", methods=["POST"])
def clear_cart():
    """Clear all items from cart."""
    if hasattr(g, "current_member") and g.current_member:
        cart = _get_cart(member_id=g.current_member.id)
    else:
        session_token = request.cookies.get(CART_SESSION_COOKIE)
        cart = _get_cart(session_token=session_token)

    if not cart:
        return jsonify({"message": "Cart is empty"}), 200

    CartItem.query.filter_by(cart_id=cart.id).delete()
    cart.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify(cart.to_dict(include_items=True)), 200


# ── Checkout ───────────────────────────────────────────────────────────────

@store_bp.route("/cart/checkout", methods=["POST"])
@require_member
def checkout():
    """
    Prepare checkout (create payment intent).
    Requires member authentication.
    """
    member = g.current_member
    cart = _get_cart(member_id=member.id)

    if not cart or cart.item_count == 0:
        return jsonify({"error": "Cart is empty"}), 400

    data = request.get_json()
    required = ["shipping_name", "shipping_address", "shipping_email"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # In a real implementation, you would:
    # 1. Create a Stripe PaymentIntent
    # 2. Create a store Order record
    # 3. Return the client secret for the frontend to confirm payment

    # For now, return a mock response
    return jsonify({
        "message": "Checkout prepared",
        "cart": cart.to_dict(include_items=True),
        "shipping_info": {
            "name": data["shipping_name"],
            "address": data["shipping_address"],
            "email": data["shipping_email"],
        },
        "total_cents": cart.total_cents,
        "total_dollars": cart.total_dollars,
        # In real implementation: "client_secret": "pi_xxx"
    }), 200


@store_bp.route("/store/order", methods=["POST"])
@require_member
def create_store_order():
    """
    Complete purchase after payment confirmation.
    This would be called from payment webhook or client after payment succeeds.
    """
    member = g.current_member
    cart = _get_cart(member_id=member.id)

    if not cart or cart.item_count == 0:
        return jsonify({"error": "Cart is empty"}), 400

    data = request.get_json()
    required = ["stripe_payment_intent", "shipping_name", "shipping_address"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # In a real implementation:
    # 1. Verify payment with Stripe
    # 2. Create Order record from cart items
    # 3. Adjust inventory
    # 4. Mark cart as completed
    # 5. Send confirmation email

    # For now, just return success
    cart.status = "completed"
    cart.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "message": "Order created successfully",
        "order_id": "STORE-" + secrets.token_hex(4).upper(),
        "total_cents": cart.total_cents,
        "total_dollars": cart.total_dollars,
    }), 201
