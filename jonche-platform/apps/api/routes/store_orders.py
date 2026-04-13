"""apps/api/routes/store_orders.py — Store order management for retailers."""

from datetime import datetime
from flask import Blueprint, request, jsonify, g
from db import db
from db.models import StoreOrder, StoreOrderItem, InventoryItem, ShoeDesign, Warehouse, Retailer
from middleware.auth import require_admin, require_retailer

store_orders_bp = Blueprint("store_orders", __name__)


# ── Store Order Management (Admin) ────────────────────────────────────────────

@store_orders_bp.route("/", methods=["GET"])
@require_admin
def list_store_orders():
    """List all store orders."""
    status = request.args.get("status")
    warehouse_id = request.args.get("warehouse_id", type=int)
    retailer_id = request.args.get("retailer_id", type=int)
    
    query = StoreOrder.query
    
    if status:
        query = query.filter_by(status=status)
    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)
    if retailer_id:
        query = query.filter_by(retailer_id=retailer_id)
    
    orders = query.order_by(StoreOrder.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders]), 200


@store_orders_bp.route("/<int:order_id>", methods=["GET"])
@require_admin
def get_store_order(order_id):
    """Get store order details."""
    order = StoreOrder.query.get_or_404(order_id)
    return jsonify(order.to_dict()), 200


@store_orders_bp.route("/<int:order_id>", methods=["PUT"])
@require_admin
def update_store_order_status(order_id):
    """Update store order status."""
    order = StoreOrder.query.get_or_404(order_id)
    data = request.get_json()
    
    if "status" in data:
        order.status = data["status"]
        order.updated_at = datetime.utcnow()
    
    if "fulfillment_status" in data:
        order.fulfillment_status = data["fulfillment_status"]
    
    if "tracking_number" in data:
        order.tracking_number = data["tracking_number"]
    
    db.session.commit()
    
    return jsonify(order.to_dict()), 200


# ── Store Order Creation (Admin) ──────────────────────────────────────────────

@store_orders_bp.route("/", methods=["POST"])
@require_admin
def create_store_order():
    """
    Create a new store order.
    
    Request body:
    {
        "retailer_id": 1,
        "warehouse_id": 1,
        "order_type": "custom_shoes",  // or "apliiq"
        "items": [
            {
                "shoe_design_id": 5,
                "quantity": 10,
                "size": "10"
            }
        ],
        "shipping_name": "Store Name",
        "shipping_address": "123 Main St, City, State 12345"
    }
    """
    data = request.get_json()
    
    required = ["retailer_id", "warehouse_id", "order_type", "items"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400
    
    retailer = Retailer.query.get_or_404(data["retailer_id"])
    warehouse = Warehouse.query.get_or_404(data["warehouse_id"])
    
    if not warehouse.is_active:
        return jsonify({"error": "Warehouse is not active"}), 400
    
    if data["order_type"] not in ["apliiq", "custom_shoes"]:
        return jsonify({"error": "order_type must be 'apliiq' or 'custom_shoes'"}), 400
    
    # Calculate total and validate items
    total_cents = 0
    items_list = []
    
    for item_data in data["items"]:
        if "shoe_design_id" not in item_data and "sku" not in item_data:
            return jsonify({"error": "Each item must have shoe_design_id or sku"}), 400
        
        quantity = item_data.get("quantity", 1)
        
        # Get design and pricing info
        design = None
        design_id = item_data.get("shoe_design_id")
        
        if design_id:
            design = ShoeDesign.query.get_or_404(design_id)
            unit_price = design.retail_price_cents
            name = design.name
            sku = item_data.get("sku") or f"SHOE-{design.id}"
        else:
            # Apliiq item
            inventory = InventoryItem.query.filter_by(
                warehouse_id=warehouse.id,
                sku=item_data["sku"]
            ).first()
            if not inventory:
                return jsonify({"error": f"SKU {item_data['sku']} not found in warehouse"}), 404
            
            unit_price = inventory.unit_cost_cents
            name = inventory.name
            sku = inventory.sku
        
        # Check availability
        if design:
            available = InventoryItem.query.filter_by(
                warehouse_id=warehouse.id,
                shoe_design_id=design.id
            ).first()
            if not available or available.quantity_available < quantity:
                return jsonify({"error": f"Not enough inventory for {name}"}), 409
        else:
            if available.quantity_available < quantity:
                return jsonify({"error": f"Not enough inventory for {sku}"}), 409
        
        item_total = unit_price * quantity
        total_cents += item_total
        
        items_list.append({
            "shoe_design_id": design_id,
            "inventory_item_id": available.id if available else None,
            "sku": sku,
            "name": name,
            "size": item_data.get("size"),
            "quantity": quantity,
            "unit_price_cents": unit_price,
        })
    
    # Create store order
    store_order = StoreOrder(
        retailer_id=data["retailer_id"],
        warehouse_id=data["warehouse_id"],
        order_type=data["order_type"],
        status="pending",
        total_cents=total_cents,
        shipping_name=data.get("shipping_name"),
        shipping_address=data.get("shipping_address"),
    )
    
    db.session.add(store_order)
    db.session.flush()  # Get the order ID
    
    # Add order items
    for item in items_list:
        order_item = StoreOrderItem(
            store_order_id=store_order.id,
            shoe_design_id=item["shoe_design_id"],
            inventory_item_id=item["inventory_item_id"],
            sku=item["sku"],
            name=item["name"],
            size=item["size"],
            quantity=item["quantity"],
            unit_price_cents=item["unit_price_cents"],
        )
        db.session.add(order_item)
        
        # Reserve inventory
        if item["inventory_item_id"]:
            inv = InventoryItem.query.get(item["inventory_item_id"])
            inv.quantity_available -= item["quantity"]
            inv.quantity_reserved += item["quantity"]
    
    db.session.commit()
    
    return jsonify(store_order.to_dict()), 201


# ── Retailer Store Order View ─────────────────────────────────────────────────

@store_orders_bp.route("/my-orders", methods=["GET"])
@require_retailer
def retailer_list_orders():
    """Get store orders for current retailer."""
    retailer_id = g.current_retailer.id
    status = request.args.get("status")
    
    query = StoreOrder.query.filter_by(retailer_id=retailer_id)
    
    if status:
        query = query.filter_by(status=status)
    
    orders = query.order_by(StoreOrder.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders]), 200


@store_orders_bp.route("/my-orders/<int:order_id>", methods=["GET"])
@require_retailer
def retailer_get_order(order_id):
    """Get specific store order for current retailer."""
    order = StoreOrder.query.get_or_404(order_id)
    
    if order.retailer_id != g.current_retailer.id:
        return jsonify({"error": "Not authorized"}), 403
    
    return jsonify(order.to_dict()), 200


# ── Store Order Placement (from Retailer Portal UI) ───────────────────────────

@store_orders_bp.route("/place-order", methods=["POST"])
@require_retailer
def place_store_order():
    """
    Retailer places an order for custom shoes or Apliiq items.

    Request body:
    {
        "warehouse_id": 2,
        "order_type": "custom_shoes",
        "items": [
            {"inventory_item_id": 5, "quantity": 10}
        ],
        "shipping_name": "Store Name",
        "shipping_address": "Full Address"
    }
    """
    data = request.get_json()
    retailer = g.current_retailer

    required = ["warehouse_id", "items", "shipping_name", "shipping_address"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    warehouse = Warehouse.query.get_or_404(data["warehouse_id"])

    if not warehouse.is_active:
        return jsonify({"error": "Warehouse is not active"}), 400

    # Create store order
    order = StoreOrder(
        retailer_id=retailer.id,
        warehouse_id=warehouse.id,
        order_type=warehouse.warehouse_type,
        shipping_name=data["shipping_name"],
        shipping_address=data["shipping_address"],
        status="pending",
        payment_status="unpaid",
    )

    try:
        total_cents = 0

        # Process items and reserve inventory
        for item_data in data.get("items", []):
            inv_id = item_data.get("inventory_item_id")
            qty = int(item_data.get("quantity", 1))

            if not inv_id or qty < 1:
                return jsonify({"error": "Invalid item format"}), 400

            inv = InventoryItem.query.get_or_404(inv_id)

            if inv.quantity_available < qty:
                msg = f"Not enough inventory for {inv.name}"
                return jsonify({"error": msg}), 409

            # Reserve inventory
            inv.quantity_reserved += qty
            inv.quantity_available -= qty

            # Create order item
            order_item = StoreOrderItem(
                inventory_item_id=inv_id,
                sku=inv.sku,
                name=inv.name,
                quantity=qty,
                unit_price_cents=inv.unit_cost_cents,
                total_cents=qty * inv.unit_cost_cents,
            )
            order.items.append(order_item)
            total_cents += qty * inv.unit_cost_cents

        order.total_cents = total_cents
        db.session.add(order)
        db.session.commit()

        return jsonify(order.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ── Order Fulfillment Status ──────────────────────────────────────────────────

@store_orders_bp.route("/<int:order_id>/fulfillment", methods=["GET"])
@require_admin
def get_order_fulfillment(order_id):
    """Get fulfillment details for an order."""
    order = StoreOrder.query.get_or_404(order_id)
    
    result = order.to_dict()
    
    if order.fulfillment_event:
        result["fulfillment_event"] = order.fulfillment_event.to_dict()
    
    return jsonify(result), 200


@store_orders_bp.route("/by-warehouse/<int:warehouse_id>", methods=["GET"])
@require_admin
def list_orders_by_warehouse(warehouse_id):
    """List orders for a specific warehouse."""
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    status = request.args.get("status")
    
    query = StoreOrder.query.filter_by(warehouse_id=warehouse_id)
    
    if status:
        query = query.filter_by(status=status)
    
    orders = query.order_by(StoreOrder.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders]), 200


# ── Store Order Payments ──────────────────────────────────────────────────────

@store_orders_bp.route("/<int:order_id>/payment-intent", methods=["POST"])
@require_retailer
def create_store_payment_intent(order_id):
    """
    Create a Stripe PaymentIntent for a store order.
    
    The order must be in 'pending' status and unpaid.
    """
    from services.stripe_client import create_payment_intent
    
    order = StoreOrder.query.get_or_404(order_id)
    
    # Verify ownership
    if order.retailer_id != g.current_retailer.id:
        return jsonify({"error": "Not authorized"}), 403
    
    # Verify order status
    if order.status != "pending":
        return jsonify({"error": "Order must be in pending status"}), 400
    
    if order.payment_status in ["paid", "pending"]:
        return jsonify({"error": "Order already has a payment in progress"}), 400
    
    try:
        # Create payment intent
        pi = create_payment_intent(
            amount_cents=order.total_cents,
            currency="usd",
            metadata={
                "type": "store_order",
                "order_id": str(order.id),
                "order_number": order.order_number,
            },
            idempotency_key=f"store-order-{order.id}",
        )
        
        # Store payment intent ID
        order.stripe_payment_intent = pi["id"]
        order.payment_status = "pending"
        db.session.commit()
        
        return jsonify({
            "client_secret": pi["client_secret"],
            "order_id": order.id,
            "amount_cents": order.total_cents,
            "currency": "usd",
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@store_orders_bp.route("/<int:order_id>/payment-status", methods=["GET"])
@require_retailer
def get_store_payment_status(order_id):
    """Get payment status for a store order."""
    order = StoreOrder.query.get_or_404(order_id)
    
    # Verify ownership
    if order.retailer_id != g.current_retailer.id:
        return jsonify({"error": "Not authorized"}), 403
    
    return jsonify({
        "order_id": order.id,
        "payment_status": order.payment_status,
        "stripe_payment_intent": order.stripe_payment_intent,
        "payment_completed_at": order.payment_completed_at.isoformat() if order.payment_completed_at else None,
        "invoice_url": order.invoice_url,
    }), 200
