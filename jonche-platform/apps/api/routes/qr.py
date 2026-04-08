"""apps/api/routes/qr.py — QR campaign tracking (DB-backed)."""

from flask import Blueprint, request, jsonify, redirect, g
from db import db
from db.models import QRCampaign, QRScan
from middleware.auth import require_admin
from datetime import datetime

qr_bp = Blueprint("qr", __name__)


@qr_bp.route("/")
@require_admin
def list_campaigns():
    campaigns = QRCampaign.query.order_by(QRCampaign.created_at.desc()).all()
    return jsonify([c.to_dict() for c in campaigns])


@qr_bp.route("/<token>/scan")
def scan_redirect(token):
    """Public scan endpoint — records scan and redirects to destination."""
    campaign = QRCampaign.query.filter_by(campaign_token=token).first()
    if not campaign or campaign.status == "ended":
        return jsonify({"error": "Campaign not found or ended"}), 404

    if campaign.expires_at and datetime.utcnow() > campaign.expires_at:
        campaign.status = "ended"
        db.session.commit()
        return jsonify({"error": "Campaign expired"}), 410

    scan = QRScan(
        campaign_id=campaign.id,
        ip_address=request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr),
        user_agent=request.headers.get("User-Agent", "")[:500],
    )
    db.session.add(scan)
    db.session.commit()

    return redirect(campaign.destination_url)


@qr_bp.route("/<int:campaign_id>/convert", methods=["POST"])
def mark_converted(campaign_id):
    """Call this after a successful purchase to mark conversion."""
    data = request.get_json() or {}
    scan = QRScan.query.filter_by(
        campaign_id=campaign_id,
        ip_address=request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr),
        converted=False
    ).order_by(QRScan.scanned_at.desc()).first()

    if scan:
        scan.converted = True
        db.session.commit()

    return jsonify({"converted": True})


@qr_bp.route("/", methods=["POST"])
@require_admin
def create_campaign():
    data = request.get_json()
    required = ["name", "destination_url"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    campaign = QRCampaign(
        name=data["name"],
        destination_url=data["destination_url"],
        drop_id=data.get("drop_id"),
        expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
    )
    db.session.add(campaign)
    db.session.commit()
    return jsonify(campaign.to_dict()), 201


@qr_bp.route("/<int:campaign_id>/end", methods=["POST"])
@require_admin
def end_campaign(campaign_id):
    campaign = QRCampaign.query.get_or_404(campaign_id)
    campaign.status = "ended"
    db.session.commit()
    return jsonify(campaign.to_dict())
