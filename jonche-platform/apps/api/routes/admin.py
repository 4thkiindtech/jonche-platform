"""apps/api/routes/admin.py — Admin controls (exports, overrides, allocations)."""

from __future__ import annotations

import csv
import io

from flask import Blueprint, request, jsonify, Response

from db import db
from db.models import Member, Order, PreOrder, RetailerAllocation, Retailer, Drop, PartnerApplication
from middleware.auth import require_admin
from services.notifications import enqueue_email

admin_bp = Blueprint("admin", __name__)


def _csv_response(filename: str, rows: list[dict]) -> Response:
    out = io.StringIO()
    if not rows:
        rows = [{"empty": ""}]
    writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    data = out.getvalue()
    return Response(
        data,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@admin_bp.route("/exports/members.csv", methods=["GET"])
@require_admin
def export_members():
    members = Member.query.order_by(Member.created_at.desc()).all()
    rows = [{
        "id": m.id,
        "email": m.email,
        "name": m.name,
        "tier": m.tier,
        "lifetime_spend": m.lifetime_spend,
        "is_blacklisted": m.is_blacklisted,
        "created_at": m.created_at.isoformat(),
    } for m in members]
    return _csv_response("members.csv", rows)


@admin_bp.route("/exports/orders.csv", methods=["GET"])
@require_admin
def export_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    rows = [{
        "id": o.id,
        "order_number": o.order_number,
        "drop_id": o.drop_id,
        "member_id": o.member_id,
        "retailer_id": o.retailer_id,
        "status": o.status,
        "total_cents": o.total_cents,
        "stripe_payment_intent": o.stripe_payment_intent,
        "created_at": o.created_at.isoformat(),
        "shipped_at": o.shipped_at.isoformat() if o.shipped_at else "",
        "tracking_number": o.tracking_number or "",
    } for o in orders]
    return _csv_response("orders.csv", rows)


@admin_bp.route("/exports/preorders.csv", methods=["GET"])
@require_admin
def export_preorders():
    preorders = PreOrder.query.order_by(PreOrder.created_at.desc()).all()
    rows = [{
        "id": p.id,
        "drop_id": p.drop_id,
        "member_id": p.member_id,
        "email": p.email,
        "name": p.name,
        "size": p.size,
        "deposit_cents": p.deposit_cents,
        "stripe_payment_intent": p.stripe_payment_intent or "",
        "status": p.status,
        "created_at": p.created_at.isoformat(),
    } for p in preorders]
    return _csv_response("preorders.csv", rows)


@admin_bp.route("/exports/partner_applications.csv", methods=["GET"])
@require_admin
def export_partner_applications():
    rows_db = PartnerApplication.query.order_by(PartnerApplication.created_at.desc()).all()
    rows = [{
        "id": a.id,
        "program_type": a.program_type,
        "source": a.source or "",
        "utm": a.utm or "",
        "full_name": a.full_name,
        "business_name": a.business_name or "",
        "email": a.email,
        "phone": a.phone or "",
        "website_or_social": a.website_or_social or "",
        "city": a.city or "",
        "state": a.state or "",
        "estimated_monthly_reach": a.estimated_monthly_reach or "",
        "network_type": a.network_type or "",
        "interested_in": a.interested_in or "",
        "additional_notes": a.additional_notes or "",
        "status": a.status,
        "created_at": a.created_at.isoformat(),
    } for a in rows_db]
    return _csv_response("partner_applications.csv", rows)


@admin_bp.route("/allocations/set", methods=["POST"])
@require_admin
def set_allocation():
    """
    Upsert allocation units for a retailer + drop.
    JSON: {retailer_id, drop_id, allocated_units}
    """
    data = request.get_json() or {}
    required = ["retailer_id", "drop_id", "allocated_units"]
    for f in required:
        if f not in data:
            return jsonify({"error": f"Missing field: {f}"}), 400

    retailer = Retailer.query.get_or_404(int(data["retailer_id"]))
    drop = Drop.query.get_or_404(int(data["drop_id"]))
    units = int(data["allocated_units"])
    if units < 0:
        return jsonify({"error": "allocated_units must be >= 0"}), 400

    alloc = RetailerAllocation.query.filter_by(retailer_id=retailer.id, drop_id=drop.id).first()
    created = False
    if not alloc:
        alloc = RetailerAllocation(retailer_id=retailer.id, drop_id=drop.id, allocated_units=units, status="pending")
        db.session.add(alloc)
        created = True
    else:
        alloc.allocated_units = units

    db.session.commit()

    # Notify retailer (best-effort)
    try:
        enqueue_email(
            recipient_email=retailer.email,
            recipient_name=retailer.contact_name or retailer.name,
            subject="JONCHE Allocation Updated",
            body_html=f"<p>Your allocation for <b>{drop.name}</b> is now <b>{alloc.allocated_units}</b> units.</p>",
            notif_type="retailer_update",
            related_id=alloc.id,
        )
    except Exception:
        pass

    return jsonify({"created": created, "allocation": alloc.to_dict()})
