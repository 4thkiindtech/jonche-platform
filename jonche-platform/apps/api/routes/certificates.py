"""apps/api/routes/certificates.py — Certificate endpoints (DB-backed)."""

from datetime import datetime
from flask import Blueprint, request, jsonify, g
from db import db
from db.models import Certificate, Drop
from middleware.auth import require_admin, require_member

certificates_bp = Blueprint("certificates", __name__)


@certificates_bp.route("/")
@require_admin
def list_certs():
    certs = Certificate.query.order_by(Certificate.issued_at.desc()).all()
    return jsonify([c.to_dict() for c in certs])


@certificates_bp.route("/verify/<token>")
def verify_by_token(token):
    """Public verification endpoint — no auth required."""
    cert = Certificate.query.filter_by(verify_token=token).first()
    if not cert:
        return jsonify({"verified": False, "error": "Certificate not found"}), 404
    return jsonify({"verified": True, "certificate": cert.to_dict()})


@certificates_bp.route("/<cert_number>")
def get_cert(cert_number):
    cert = Certificate.query.filter_by(cert_number=cert_number).first()
    if not cert:
        return jsonify({"error": "Certificate not found"}), 404
    return jsonify(cert.to_dict())


@certificates_bp.route("/", methods=["POST"])
@require_admin
def issue_cert():
    data = request.get_json()
    required = ["drop_id", "size", "run_number", "total_run"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    existing = Certificate.query.filter_by(drop_id=data["drop_id"]).count()
    cert = Certificate(
        cert_number=f"JNC-{datetime.utcnow().year}-{existing + 1:04d}",
        drop_id=data["drop_id"],
        member_id=data.get("member_id"),
        order_id=data.get("order_id"),
        size=data["size"],
        run_number=data["run_number"],
        total_run=data["total_run"],
    )
    db.session.add(cert)
    db.session.commit()
    return jsonify(cert.to_dict()), 201


@certificates_bp.route("/count")
@require_admin
def count():
    return jsonify({
        "total_issued": Certificate.query.count(),
        "auth_scan_rate": 99.2,
    })


@certificates_bp.route("/my-certs")
@require_member
def my_certs():
    certs = Certificate.query.filter_by(member_id=g.current_member.id).all()
    return jsonify([c.to_dict() for c in certs])
