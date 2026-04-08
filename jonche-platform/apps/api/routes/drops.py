"""apps/api/routes/drops.py — Drop management (DB-backed)."""

from datetime import datetime
from flask import Blueprint, request, jsonify, g
from db import db
from db.models import Drop
from middleware.auth import require_admin

drops_bp = Blueprint("drops", __name__)


@drops_bp.route("/")
def list_drops():
    status = request.args.get("status")
    q = Drop.query
    if status:
        q = q.filter_by(status=status)
    drops = q.order_by(Drop.created_at.desc()).all()
    return jsonify([d.to_dict() for d in drops])


@drops_bp.route("/<slug>")
def get_drop(slug):
    drop = Drop.query.filter_by(slug=slug).first()
    if not drop:
        return jsonify({"error": "Drop not found"}), 404
    return jsonify(drop.to_dict())


@drops_bp.route("/", methods=["POST"])
@require_admin
def create_drop():
    data = request.get_json()
    required = ["slug", "name", "colorway", "sizes", "price", "total_units"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    if Drop.query.filter_by(slug=data["slug"]).first():
        return jsonify({"error": "Slug already exists"}), 409

    drop = Drop(
        slug=data["slug"],
        name=data["name"],
        colorway=data["colorway"],
        sizes=data["sizes"],
        price=int(data["price"]),
        total_units=int(data["total_units"]),
        units_reserved=int(data.get("units_reserved", 0)),
        description=data.get("description"),
        use_raffle=data.get("use_raffle", False),
        max_per_member=int(data.get("max_per_member", 1)),
        drop_at=datetime.fromisoformat(data["drop_at"]) if data.get("drop_at") else None,
        ends_at=datetime.fromisoformat(data["ends_at"]) if data.get("ends_at") else None,
    )
    db.session.add(drop)
    db.session.commit()
    return jsonify(drop.to_dict()), 201


@drops_bp.route("/<slug>", methods=["PATCH"])
@require_admin
def update_drop(slug):
    drop = Drop.query.filter_by(slug=slug).first()
    if not drop:
        return jsonify({"error": "Drop not found"}), 404
    data = request.get_json()
    editable = ["name", "colorway", "sizes", "price", "total_units",
                "units_reserved", "description", "use_raffle", "max_per_member",
                "drop_at", "ends_at", "status"]
    for field in editable:
        if field in data:
            if field in ("drop_at", "ends_at") and data[field]:
                setattr(drop, field, datetime.fromisoformat(data[field]))
            else:
                setattr(drop, field, data[field])
    db.session.commit()
    return jsonify(drop.to_dict())


@drops_bp.route("/<slug>/publish", methods=["POST"])
@require_admin
def publish_drop(slug):
    drop = Drop.query.filter_by(slug=slug).first()
    if not drop:
        return jsonify({"error": "Drop not found"}), 404
    if drop.status not in ("draft", "upcoming"):
        return jsonify({"error": f"Cannot publish: status is {drop.status}"}), 400
    drop.status = "live"
    drop.drop_at = datetime.utcnow()
    db.session.commit()
    return jsonify(drop.to_dict())


@drops_bp.route("/<slug>/end", methods=["POST"])
@require_admin
def end_drop(slug):
    drop = Drop.query.filter_by(slug=slug).first()
    if not drop:
        return jsonify({"error": "Drop not found"}), 404
    drop.status = "ended"
    drop.ends_at = datetime.utcnow()
    db.session.commit()
    return jsonify(drop.to_dict())
