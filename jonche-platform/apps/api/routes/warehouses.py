"""apps/api/routes/warehouses.py — Warehouse and inventory management endpoints."""

from flask import Blueprint, request, jsonify, g
from db import db
from db.models import Warehouse, InventoryItem, ShoeDesign
from middleware.auth import require_admin

warehouses_bp = Blueprint("warehouses", __name__)


# ── Warehouse Management ──────────────────────────────────────────────────────

@warehouses_bp.route("/", methods=["GET"])
@require_admin
def list_warehouses():
    """List all warehouses."""
    warehouses = Warehouse.query.all()
    return jsonify([w.to_dict() for w in warehouses]), 200


@warehouses_bp.route("/<int:warehouse_id>", methods=["GET"])
@require_admin
def get_warehouse(warehouse_id):
    """Get warehouse details."""
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    data = warehouse.to_dict()
    
    # Include inventory count
    inventory_count = InventoryItem.query.filter_by(warehouse_id=warehouse_id).count()
    data["inventory_count"] = inventory_count
    
    return jsonify(data), 200


@warehouses_bp.route("/", methods=["POST"])
@require_admin
def create_warehouse():
    """Create a new warehouse."""
    data = request.get_json()
    required = ["name", "warehouse_type"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400
    
    if data["warehouse_type"] not in ["apliiq", "shoe_warehouse"]:
        return jsonify({"error": "warehouse_type must be 'apliiq' or 'shoe_warehouse'"}), 400
    
    if Warehouse.query.filter_by(name=data["name"]).first():
        return jsonify({"error": "Warehouse name already exists"}), 409
    
    warehouse = Warehouse(
        name=data["name"],
        warehouse_type=data["warehouse_type"],
        location=data.get("location"),
        webhook_url=data.get("webhook_url"),
        webhook_secret=data.get("webhook_secret"),
        is_active=data.get("is_active", True),
    )
    
    db.session.add(warehouse)
    db.session.commit()
    
    return jsonify(warehouse.to_dict()), 201


@warehouses_bp.route("/<int:warehouse_id>", methods=["PUT"])
@require_admin
def update_warehouse(warehouse_id):
    """Update warehouse details."""
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    data = request.get_json()
    
    if "name" in data:
        if data["name"] != warehouse.name and Warehouse.query.filter_by(name=data["name"]).first():
            return jsonify({"error": "Warehouse name already exists"}), 409
        warehouse.name = data["name"]
    
    if "location" in data:
        warehouse.location = data["location"]
    
    if "webhook_url" in data:
        warehouse.webhook_url = data["webhook_url"]
    
    if "webhook_secret" in data:
        warehouse.webhook_secret = data["webhook_secret"]
    
    if "is_active" in data:
        warehouse.is_active = data["is_active"]
    
    db.session.commit()
    
    return jsonify(warehouse.to_dict()), 200


# ── Inventory Management ──────────────────────────────────────────────────────

@warehouses_bp.route("/<int:warehouse_id>/inventory", methods=["GET"])
@require_admin
def list_inventory(warehouse_id):
    """List inventory for a warehouse."""
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    
    items = InventoryItem.query.filter_by(warehouse_id=warehouse_id).all()
    return jsonify([i.to_dict() for i in items]), 200


@warehouses_bp.route("/<int:warehouse_id>/inventory", methods=["POST"])
@require_admin
def add_inventory(warehouse_id):
    """Add or update inventory item."""
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    data = request.get_json()
    
    required = ["sku", "name", "quantity_total", "unit_cost_cents"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400
    
    # Check if SKU already exists for this warehouse
    existing = InventoryItem.query.filter_by(
        warehouse_id=warehouse_id,
        sku=data["sku"]
    ).first()
    
    if existing:
        existing.name = data.get("name", existing.name)
        existing.quantity_total = data["quantity_total"]
        existing.quantity_available = data.get("quantity_available", data["quantity_total"])
        existing.unit_cost_cents = data["unit_cost_cents"]
        existing.category = data.get("category", existing.category)
        
        db.session.commit()
        return jsonify(existing.to_dict()), 200
    
    # Create new inventory item
    inventory_item = InventoryItem(
        warehouse_id=warehouse_id,
        shoe_design_id=data.get("shoe_design_id"),
        sku=data["sku"],
        name=data["name"],
        category=data.get("category", "clothing"),
        quantity_total=data["quantity_total"],
        quantity_available=data.get("quantity_available", data["quantity_total"]),
        quantity_reserved=0,
        unit_cost_cents=data["unit_cost_cents"],
    )
    
    db.session.add(inventory_item)
    db.session.commit()
    
    return jsonify(inventory_item.to_dict()), 201


@warehouses_bp.route("/inventory/<int:inventory_id>", methods=["GET"])
@require_admin
def get_inventory_item(inventory_id):
    """Get inventory item details."""
    item = InventoryItem.query.get_or_404(inventory_id)
    return jsonify(item.to_dict()), 200


@warehouses_bp.route("/inventory/<int:inventory_id>", methods=["PUT"])
@require_admin
def update_inventory_item(inventory_id):
    """Update inventory item."""
    item = InventoryItem.query.get_or_404(inventory_id)
    data = request.get_json()
    
    if "quantity_total" in data:
        item.quantity_total = data["quantity_total"]
    
    if "quantity_available" in data:
        item.quantity_available = data["quantity_available"]
    
    if "quantity_reserved" in data:
        item.quantity_reserved = data["quantity_reserved"]
    
    if "unit_cost_cents" in data:
        item.unit_cost_cents = data["unit_cost_cents"]
    
    if "name" in data:
        item.name = data["name"]
    
    db.session.commit()
    
    return jsonify(item.to_dict()), 200


# ── Shoe Designs (for custom shoes from AliveShoes) ──────────────────────────

@warehouses_bp.route("/designs", methods=["GET"])
@require_admin
def list_shoe_designs():
    """List all shoe designs."""
    designs = ShoeDesign.query.all()
    return jsonify([d.to_dict() for d in designs]), 200


@warehouses_bp.route("/designs", methods=["POST"])
@require_admin
def create_shoe_design():
    """Create a new shoe design."""
    data = request.get_json()
    
    required = ["name", "retail_price_cents"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400
    
    # Check for duplicate AliveShoes ID if provided
    if data.get("aliveshoes_id"):
        existing = ShoeDesign.query.filter_by(aliveshoes_id=data["aliveshoes_id"]).first()
        if existing:
            return jsonify({"error": "Shoe design with this AliveShoes ID already exists"}), 409
    
    design = ShoeDesign(
        aliveshoes_id=data.get("aliveshoes_id"),
        name=data["name"],
        description=data.get("description"),
        design_image_url=data.get("design_image_url"),
        aliveshoes_url=data.get("aliveshoes_url"),
        status=data.get("status", "approved"),
        retail_price_cents=data["retail_price_cents"],
        markup_percentage=data.get("markup_percentage", 0.0),
        sizes_available=data.get("sizes_available"),
    )
    
    db.session.add(design)
    db.session.commit()
    
    return jsonify(design.to_dict()), 201


@warehouses_bp.route("/designs/<int:design_id>", methods=["GET"])
@require_admin
def get_shoe_design(design_id):
    """Get shoe design details."""
    design = ShoeDesign.query.get_or_404(design_id)
    data = design.to_dict()
    
    # Include inventory across warehouses
    inventory = InventoryItem.query.filter_by(shoe_design_id=design_id).all()
    data["inventory"] = [i.to_dict() for i in inventory]
    
    return jsonify(data), 200


@warehouses_bp.route("/designs/<int:design_id>", methods=["PUT"])
@require_admin
def update_shoe_design(design_id):
    """Update shoe design."""
    design = ShoeDesign.query.get_or_404(design_id)
    data = request.get_json()
    
    if "name" in data:
        design.name = data["name"]
    
    if "description" in data:
        design.description = data["description"]
    
    if "design_image_url" in data:
        design.design_image_url = data["design_image_url"]
    
    if "aliveshoes_url" in data:
        design.aliveshoes_url = data["aliveshoes_url"]
    
    if "status" in data:
        design.status = data["status"]
    
    if "retail_price_cents" in data:
        design.retail_price_cents = data["retail_price_cents"]
    
    if "markup_percentage" in data:
        design.markup_percentage = data["markup_percentage"]
    
    if "sizes_available" in data:
        design.sizes_available = data["sizes_available"]
    
    db.session.commit()
    
    return jsonify(design.to_dict()), 200
