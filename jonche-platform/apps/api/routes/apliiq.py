"""
apps/api/routes/apliiq.py
Admin-only Apliiq fulfillment endpoints.

Routes:
  GET  /api/apliiq/products                   — browse Apliiq catalog
  GET  /api/apliiq/orders                     — list all Apliiq orders (paginated)
  POST /api/apliiq/orders/<order_id>/submit   — submit a completed order to Apliiq
  GET  /api/apliiq/orders/<order_id>/status   — pull latest status from Apliiq
  POST /api/apliiq/orders/<order_id>/cancel   — cancel an order in Apliiq
"""

from __future__ import annotations

import json

from flask import Blueprint, jsonify, request
from db import db
from db.models import Order
from middleware.auth import require_admin
from services import apliiq_client
from services.apliiq_client import ApliiqError

apliiq_bp = Blueprint("apliiq", __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_shipping_address(raw: str | None) -> dict:
    """
    The shipping_address field is stored as free-text or JSON.
    Try JSON first; fall back to a plain-string address1.
    """
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except (ValueError, TypeError):
        pass
    return {"address1": raw}


def _build_apliiq_payload(order: Order) -> dict:
    """
    Map a local Order row to the Apliiq create-order payload.

    Apliiq field names are PascalCase. ProductId and ColorId are integers
    stored on the Drop as apliiq_product_id and apliiq_variant_id respectively.
    SizeId is stored as apliiq_variant_id when it refers to a size — admins
    should populate these via PATCH /api/drops/<slug>.
    """
    drop = order.drop
    addr = _parse_shipping_address(order.shipping_address)

    items = []
    for item in order.items:
        li: dict = {"Quantity": item.quantity}
        if drop and drop.apliiq_product_id:
            li["ProductId"] = int(drop.apliiq_product_id)
        if drop and drop.apliiq_variant_id:
            # apliiq_variant_id stores the Apliiq size Id
            li["SizeId"] = int(drop.apliiq_variant_id)
        items.append(li)

    return {
        "ExternalId": order.order_number,
        "Items": items,
        "ShippingAddress": {
            "Name":     order.shipping_name or "",
            "Address1": addr.get("address1", addr.get("Address1", "")),
            "Address2": addr.get("address2", addr.get("Address2", "")),
            "City":     addr.get("city",     addr.get("City", "")),
            "State":    addr.get("state",    addr.get("State", "")),
            "Zip":      addr.get("zip",      addr.get("Zip", "")),
            "Country":  addr.get("country",  addr.get("Country", "US")),
        },
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@apliiq_bp.route("/products", methods=["GET"])
@require_admin
def list_products():
    """Fetch the full Apliiq product catalog for this store."""
    try:
        products = apliiq_client.get_products()
        return jsonify({"products": products, "count": len(products)})
    except ApliiqError as e:
        return jsonify({"error": str(e)}), 502


@apliiq_bp.route("/orders", methods=["GET"])
@require_admin
def list_apliiq_orders():
    """List orders from Apliiq (paginated)."""
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    try:
        orders = apliiq_client.list_orders(page=page, per_page=per_page)
        return jsonify({"orders": orders, "page": page})
    except ApliiqError as e:
        return jsonify({"error": str(e)}), 502


@apliiq_bp.route("/orders/<int:order_id>/submit", methods=["POST"])
@require_admin
def submit_order(order_id: int):
    """
    Submit a local completed order to Apliiq for fulfillment.
    Idempotent: skips if already submitted (apliiq_order_id is set).
    """
    order = Order.query.get_or_404(order_id)

    if order.status != "completed":
        return jsonify({"error": "Order must be completed before submitting to Apliiq"}), 400

    if order.apliiq_order_id:
        return jsonify({
            "message": "Already submitted",
            "apliiq_order_id": order.apliiq_order_id,
            "apliiq_status": order.apliiq_status,
        })

    payload = _build_apliiq_payload(order)
    try:
        result = apliiq_client.create_order(payload)
    except ApliiqError as e:
        return jsonify({"error": str(e)}), 502

    order.apliiq_order_id = str(result.get("id") or result.get("order_id", ""))
    order.apliiq_status = result.get("status", "submitted")
    db.session.commit()

    return jsonify({
        "message": "Order submitted to Apliiq",
        "apliiq_order_id": order.apliiq_order_id,
        "apliiq_status": order.apliiq_status,
        "apliiq_response": result,
    })


@apliiq_bp.route("/orders/<int:order_id>/status", methods=["GET"])
@require_admin
def get_order_status(order_id: int):
    """Pull the latest fulfillment status from Apliiq and sync it locally."""
    order = Order.query.get_or_404(order_id)

    if not order.apliiq_order_id:
        return jsonify({"error": "Order has not been submitted to Apliiq yet"}), 400

    try:
        result = apliiq_client.get_order(order.apliiq_order_id)
    except ApliiqError as e:
        return jsonify({"error": str(e)}), 502

    new_status = result.get("status")
    if new_status and new_status != order.apliiq_status:
        order.apliiq_status = new_status
        # Mirror Apliiq tracking number when the order ships
        tracking = result.get("tracking_number") or result.get("tracking")
        if tracking and not order.tracking_number:
            order.tracking_number = tracking
        db.session.commit()

    return jsonify({"order_id": order_id, "apliiq_status": order.apliiq_status, "apliiq": result})


@apliiq_bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
@require_admin
def cancel_order(order_id: int):
    """Request cancellation of an order in Apliiq."""
    order = Order.query.get_or_404(order_id)

    if not order.apliiq_order_id:
        return jsonify({"error": "Order has not been submitted to Apliiq yet"}), 400

    try:
        result = apliiq_client.cancel_order(order.apliiq_order_id)
    except ApliiqError as e:
        return jsonify({"error": str(e)}), 502

    order.apliiq_status = "cancelled"
    db.session.commit()

    return jsonify({"message": "Cancellation requested", "apliiq": result})
