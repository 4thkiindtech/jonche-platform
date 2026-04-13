"""apps/api/routes/fulfillment.py — Fulfillment webhook endpoints for Apliiq & warehouses."""

import os
import json
import hmac
import hashlib
import base64
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from db import db
from db.models import StoreOrder, FulfillmentEvent, Warehouse
from middleware.auth import require_admin

fulfillment_bp = Blueprint("fulfillment", __name__)


def _validate_hmac(payload_bytes: bytes, hmac_header: str, shared_secret: str) -> bool:
    """
    Validate HMAC signature.
    Expected format: base64_encode(HMACSHA256([Base64_payload], Shared_SECRET))
    """
    try:
        # Compute HMAC-SHA256 of base64-encoded payload
        b64_payload = base64.b64encode(payload_bytes)
        expected_hmac = hmac.new(
            shared_secret.encode('utf-8'),
            b64_payload,
            hashlib.sha256
        ).digest()
        expected_hmac_b64 = base64.b64encode(expected_hmac).decode('utf-8')
        
        # Compare with provided HMAC
        return hmac.compare_digest(expected_hmac_b64, hmac_header)
    except Exception:
        return False


@fulfillment_bp.route("/webhook/<string:warehouse_token>", methods=["POST"])
def fulfillment_webhook(warehouse_token):
    """
    Receive fulfillment updates from Apliiq or warehouse systems.
    
    Expected header: x-apliiq-hmac
    Expected payload:
    {
        "fulfillment": {
            "order_id": "1569438492",
            "status": "success",
            "tracking_company": "USPS",
            "tracking_numbers": ["9400111699000516881728"],
            "tracking_urls": [],
            "line_items": [...]
        }
    }
    """
    
    # Find warehouse by token (you can use warehouse_id or a special token)
    warehouse = Warehouse.query.filter_by(id=int(warehouse_token)).first()
    if not warehouse:
        return jsonify({"error": "Warehouse not found"}), 404
    
    # Get raw payload for HMAC validation
    payload_bytes = request.get_data()
    hmac_header = request.headers.get("x-apliiq-hmac", "")
    
    # Validate HMAC if webhook secret is configured
    hmac_valid = True
    if warehouse.webhook_secret:
        hmac_valid = _validate_hmac(payload_bytes, hmac_header, warehouse.webhook_secret)
        if not hmac_valid:
            return jsonify({"error": "Invalid HMAC signature"}), 401
    
    try:
        data = request.get_json()
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400
    
    if "fulfillment" not in data:
        return jsonify({"error": "Missing fulfillment object"}), 400
    
    fulfillment = data["fulfillment"]
    order_id = fulfillment.get("order_id")
    status = fulfillment.get("status")
    tracking_company = fulfillment.get("tracking_company")
    tracking_numbers = fulfillment.get("tracking_numbers", [])
    line_items = fulfillment.get("line_items", [])
    
    # Find the store order by apliiq_order_id or warehouse order reference
    store_order = StoreOrder.query.filter_by(
        apliiq_order_id=order_id,
        warehouse_id=warehouse.id
    ).first()
    
    if not store_order:
        # Try to find by internal order reference (if warehouse uses different ID mapping)
        # This depends on your warehouse system - adjust as needed
        return jsonify({"error": "Store order not found for this fulfillment"}), 404
    
    # Create fulfillment event
    fulfillment_event = FulfillmentEvent(
        store_order_id=store_order.id,
        warehouse_id=warehouse.id,
        status=status,
        tracking_company=tracking_company,
        tracking_numbers=json.dumps(tracking_numbers),
        line_items=json.dumps(line_items),
        webhook_payload=json.dumps(fulfillment),
        hmac_valid=hmac_valid,
    )
    
    db.session.add(fulfillment_event)
    
    # Update store order status based on fulfillment status
    if status == "success":
        store_order.status = "shipped"
        store_order.fulfillment_status = status
        if tracking_numbers:
            store_order.tracking_number = tracking_numbers[0]
        store_order.updated_at = datetime.utcnow()
    elif status == "pending":
        store_order.status = "in_fulfillment"
        store_order.fulfillment_status = status
        store_order.updated_at = datetime.utcnow()
    elif status == "failed":
        store_order.status = "pending"  # Reset to pending for retry
        store_order.fulfillment_status = status
        store_order.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        "status": "received",
        "fulfillment_event_id": fulfillment_event.id,
        "store_order_id": store_order.id,
    }), 200


@fulfillment_bp.route("/webhook-url", methods=["GET"])
@require_admin
def get_webhook_urls():
    """Admin endpoint to retrieve webhook URLs for all active warehouses."""
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    
    webhook_config = []
    for warehouse in warehouses:
        # Build the webhook URL for this warehouse
        # Assuming your domain is available via config
        base_url = os.getenv("API_URL", "http://localhost:5001")
        webhook_urls = {
            "warehouse_id": warehouse.id,
            "name": warehouse.name,
            "type": warehouse.warehouse_type,
            "webhook_url": f"{base_url}/api/fulfillment/webhook/{warehouse.id}",
            "header": "x-apliiq-hmac",
            "header_description": "base64_encode(HMACSHA256([Base64_payload], Shared_SECRET))",
        }
        webhook_config.append(webhook_urls)
    
    return jsonify(webhook_config), 200


@fulfillment_bp.route("/events/<int:store_order_id>", methods=["GET"])
@require_admin
def get_fulfillment_events(store_order_id):
    """Get all fulfillment events for a store order."""
    store_order = StoreOrder.query.get_or_404(store_order_id)
    
    events = FulfillmentEvent.query.filter_by(store_order_id=store_order_id).order_by(
        FulfillmentEvent.received_at.desc()
    ).all()
    
    return jsonify([e.to_dict() for e in events]), 200


@fulfillment_bp.route("/test/<int:warehouse_id>", methods=["POST"])
@require_admin
def test_webhook(warehouse_id):
    """
    Admin endpoint to test webhook endpoint with a sample payload.
    Useful for validating webhook configuration.
    """
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    
    # Create a test payload
    test_payload = {
        "fulfillment": {
            "order_id": "TEST-12345",
            "status": "success",
            "tracking_company": "USPS",
            "tracking_numbers": ["9400111699000516881728"],
            "tracking_urls": [],
            "line_items": [
                {
                    "id": "1511138222",
                    "quantity": 1,
                    "sku": "TEST-SKU-001",
                    "name": "Test Item"
                }
            ]
        }
    }
    
    payload_bytes = json.dumps(test_payload).encode('utf-8')
    
    # Generate HMAC if secret is configured
    hmac_header = ""
    if warehouse.webhook_secret:
        b64_payload = base64.b64encode(payload_bytes)
        expected_hmac = hmac.new(
            warehouse.webhook_secret.encode('utf-8'),
            b64_payload,
            hashlib.sha256
        ).digest()
        hmac_header = base64.b64encode(expected_hmac).decode('utf-8')
    
    return jsonify({
        "test_payload": test_payload,
        "webhook_url": f"/api/fulfillment/webhook/{warehouse.id}",
        "headers": {
            "x-apliiq-hmac": hmac_header if hmac_header else "N/A - no secret configured",
            "Content-Type": "application/json"
        },
        "instructions": "POST the test_payload to the webhook_url with the headers"
    }), 200
