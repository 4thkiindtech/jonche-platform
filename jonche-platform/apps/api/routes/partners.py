"""apps/api/routes/partners.py — Partner program intake endpoints (DB-backed)."""

import json

from flask import Blueprint, request, jsonify

from db import db
from db.models import PartnerApplication
from middleware.auth import require_admin
from services.notifications import enqueue_email


partners_bp = Blueprint("partners", __name__)

PROGRAM_LABELS = {
    "retail_alliance": "Retail Alliance",
    "affiliate_creators": "Affiliate Creators",
    "referral_network": "Strategic Referral Network",
    "executives": "Executives",
}


@partners_bp.route("/apply", methods=["POST"])
def apply_partner():
    """Public endpoint to capture partner program applications."""
    data = request.get_json() or {}

    required = ["program_type", "full_name", "email"]
    for field in required:
        if not (data.get(field) or "").strip():
            return jsonify({"error": f"Missing field: {field}"}), 400

    app = PartnerApplication(
        program_type=str(data["program_type"]).strip(),
        source=(str(data.get("source")).strip() if data.get("source") else None),
        utm=json.dumps(data.get("utm") or {}),
        full_name=str(data["full_name"]).strip(),
        business_name=(str(data.get("business_name")).strip() if data.get("business_name") else None),
        email=str(data["email"]).strip().lower(),
        phone=(str(data.get("phone")).strip() if data.get("phone") else None),
        website_or_social=(str(data.get("website_or_social")).strip() if data.get("website_or_social") else None),
        city=(str(data.get("city")).strip() if data.get("city") else None),
        state=(str(data.get("state")).strip() if data.get("state") else None),
        estimated_monthly_reach=(str(data.get("estimated_monthly_reach")).strip() if data.get("estimated_monthly_reach") else None),
        network_type=(str(data.get("network_type")).strip() if data.get("network_type") else None),
        interested_in=json.dumps(data.get("interested_in") or []),
        additional_notes=(str(data.get("additional_notes")).strip() if data.get("additional_notes") else None),
        status="new",
    )

    db.session.add(app)
    db.session.commit()

    # Email: application received (best-effort)
    try:
        label = PROGRAM_LABELS.get(app.program_type, app.program_type)
        enqueue_email(
            recipient_email=app.email,
            recipient_name=app.full_name,
            subject=f"Thanks for applying to the Jonche {label}",
            body_html=(
                f"<p>Thanks for applying to the Jonche <b>{label}</b> program.</p>"
                "<p>We will review your application within <b>24–48 hours</b> and follow up by email.</p>"
            ),
            notif_type="partner_application_received",
            related_id=app.id,
        )
    except Exception:
        pass

    return jsonify(app.to_dict()), 201


@partners_bp.route("/applications", methods=["GET"])
@require_admin
def list_partner_applications():
    """Admin-only listing of recent applications."""
    program_type = request.args.get("program_type")
    status = request.args.get("status")
    email = request.args.get("email")

    q = PartnerApplication.query
    if program_type:
        q = q.filter_by(program_type=program_type)
    if status:
        q = q.filter_by(status=status)
    if email:
        q = q.filter_by(email=email.strip().lower())

    rows = q.order_by(PartnerApplication.created_at.desc()).limit(200).all()
    return jsonify([r.to_dict() for r in rows])


@partners_bp.route("/applications/<int:application_id>", methods=["PATCH"])
@require_admin
def update_partner_application(application_id: int):
    """Admin-only status update."""
    row = PartnerApplication.query.get_or_404(application_id)
    data = request.get_json() or {}

    allowed = {"status"}
    for k, v in data.items():
        if k not in allowed:
            continue
        setattr(row, k, str(v).strip())

    db.session.commit()
    return jsonify(row.to_dict())
