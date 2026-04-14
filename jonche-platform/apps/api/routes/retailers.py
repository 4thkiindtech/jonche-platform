"""apps/api/routes/retailers.py — Retailer portal endpoints (DB-backed)."""

import os
import secrets
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash
from db import db
from db.models import Retailer, RetailerAllocation, Drop, Order, OrderItem
from middleware.auth import require_admin, require_retailer, optional_auth
from services.notifications import enqueue_email

retailers_bp = Blueprint("retailers", __name__)


@retailers_bp.route("/")
@optional_auth
def list_retailers():
    """List retailers - public endpoint, can be filtered by tier."""
    tier = request.args.get("tier")
    q = Retailer.query.filter_by(status="active")  # Only show active retailers publicly
    if tier:
        q = q.filter_by(tier=tier)
    return jsonify([r.to_dict() for r in q.all()])


@retailers_bp.route("/<int:retailer_id>")
@optional_auth
def get_retailer(retailer_id):
    """Get specific retailer - public endpoint."""
    retailer = Retailer.query.get_or_404(retailer_id)
    # Only show active retailers publicly (unless authenticated as admin)
    if retailer.status != "active" and not (hasattr(g, 'current_admin') and g.current_admin):
        return jsonify({"error": "Not found"}), 404
    return jsonify(retailer.to_dict())


@retailers_bp.route("/", methods=["POST"])
@require_admin
def invite_retailer():
    data = request.get_json()
    required = ["email", "name", "password"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    if Retailer.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    retailer = Retailer(
        email=data["email"],
        password_hash=generate_password_hash(data["password"]),
        name=data["name"],
        contact_name=data.get("contact_name"),
        phone=data.get("phone"),
        city=data.get("city"),
        tier=data.get("tier", "basic"),
        status="review",
    )
    db.session.add(retailer)
    db.session.commit()
    return jsonify(retailer.to_dict()), 201


@retailers_bp.route("/<int:retailer_id>/approve", methods=["POST"])
@require_admin
def approve_retailer(retailer_id):
    retailer = Retailer.query.get_or_404(retailer_id)
    retailer.status = "active"
    db.session.commit()
    return jsonify(retailer.to_dict())


@retailers_bp.route("/me/allocations", methods=["GET"])
@require_retailer
def my_allocations():
    retailer = g.current_retailer
    allocs = RetailerAllocation.query.filter_by(retailer_id=retailer.id).all()
    return jsonify([a.to_dict() for a in allocs])


@retailers_bp.route("/revenue")
@require_admin
def revenue():
    from db.models import Order
    from sqlalchemy import func
    total = db.session.query(func.sum(Order.total_cents)).filter(
        Order.retailer_id.isnot(None),
        Order.status == "completed"
    ).scalar() or 0
    return jsonify({
        "wholesale_revenue_cents": total,
        "wholesale_revenue_dollars": total / 100,
        "active_retailers": Retailer.query.filter_by(status="active").count(),
    })


# ── Retailer workflows ────────────────────────────────────────────────────────

def _wholesale_multiplier() -> float:
    try:
        return float(os.getenv("WHOLESALE_MULTIPLIER", "0.6"))
    except ValueError:
        return 0.6


@retailers_bp.route("/allocations/<int:alloc_id>/purchase-order", methods=["POST"])
@require_retailer
def submit_purchase_order(alloc_id: int):
    """
    Retailer submits a purchase order against an allocation.
    Creates a wholesale Order record and updates purchased units.
    """
    alloc = RetailerAllocation.query.get_or_404(alloc_id)
    retailer = g.current_retailer
    if alloc.retailer_id != retailer.id:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    qty = int(data.get("quantity") or 0)
    if qty <= 0:
        return jsonify({"error": "quantity must be > 0"}), 400
    if qty > (alloc.allocated_units - alloc.purchased_units):
        return jsonify({"error": "Quantity exceeds remaining allocation"}), 409

    drop = Drop.query.get_or_404(alloc.drop_id)
    unit = int(round(drop.price * _wholesale_multiplier()))
    total = unit * qty

    if not alloc.purchase_order_number:
        alloc.purchase_order_number = data.get("purchase_order_number") or f"PO-{secrets.token_hex(3).upper()}"
    if not alloc.invoice_number:
        alloc.invoice_number = f"INV-{datetime.utcnow().year}-{secrets.token_hex(3).upper()}"

    alloc.purchased_units += qty
    alloc.status = "confirmed"

    order = Order(
        drop_id=drop.id,
        retailer_id=retailer.id,
        status="completed",
        total_cents=total,
        shipping_name=data.get("shipping_name") or retailer.name,
        shipping_address=data.get("shipping_address"),
    )
    db.session.add(order)
    db.session.flush()
    db.session.add(OrderItem(
        order_id=order.id,
        size="MIXED",
        quantity=qty,
        unit_price=unit,
    ))

    db.session.commit()

    try:
        enqueue_email(
            recipient_email=retailer.email,
            recipient_name=retailer.contact_name or retailer.name,
            subject="JONCHE Purchase Order Received",
            body_html=f"<p>PO <b>{alloc.purchase_order_number}</b> received for <b>{qty}</b> units of <b>{drop.name}</b>.</p>",
            notif_type="retailer_update",
            related_id=alloc.id,
        )
    except Exception:
        pass

    return jsonify({
        "allocation": alloc.to_dict(),
        "order": order.to_dict(),
    }), 201


@retailers_bp.route("/allocations/<int:alloc_id>/invoice", methods=["GET"])
@require_retailer
def download_invoice(alloc_id: int):
    from flask import Response

    alloc = RetailerAllocation.query.get_or_404(alloc_id)
    retailer = g.current_retailer
    if alloc.retailer_id != retailer.id:
        return jsonify({"error": "Access denied"}), 403

    drop = Drop.query.get_or_404(alloc.drop_id)
    inv = alloc.invoice_number or f"INV-{datetime.utcnow().year}-{secrets.token_hex(3).upper()}"
    alloc.invoice_number = inv
    db.session.commit()

    unit = int(round(drop.price * _wholesale_multiplier()))
    qty = alloc.purchased_units
    total = unit * qty

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:800px;margin:40px auto">
      <h2>JONCHE Wholesale Invoice</h2>
      <p><b>Invoice:</b> {inv}<br>
         <b>Retailer:</b> {retailer.name}<br>
         <b>Email:</b> {retailer.email}<br>
         <b>Date:</b> {datetime.utcnow().date().isoformat()}</p>
      <hr>
      <p><b>Drop:</b> {drop.name} ({drop.slug})</p>
      <table width="100%" cellspacing="0" cellpadding="8" border="1" style="border-collapse:collapse">
        <tr><th align="left">Item</th><th align="right">Qty</th><th align="right">Unit</th><th align="right">Total</th></tr>
        <tr>
          <td>{drop.name} (Wholesale)</td>
          <td align="right">{qty}</td>
          <td align="right">${unit/100:.2f}</td>
          <td align="right">${total/100:.2f}</td>
        </tr>
      </table>
      <p style="margin-top:16px"><b>Total Due:</b> ${total/100:.2f}</p>
    </body></html>
    """
    return Response(
        html,
        mimetype="text/html",
        headers={"Content-Disposition": f'attachment; filename="{inv}.html"'},
    )


@retailers_bp.route("/allocations/<int:alloc_id>/ship", methods=["POST"])
@require_admin
def mark_allocation_shipped(alloc_id: int):
    alloc = RetailerAllocation.query.get_or_404(alloc_id)
    data = request.get_json() or {}
    alloc.status = "shipped"
    alloc.shipped_at = datetime.utcnow()
    alloc.tracking_number = data.get("tracking_number")
    db.session.commit()
    return jsonify(alloc.to_dict())
