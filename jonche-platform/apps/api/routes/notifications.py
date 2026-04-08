"""apps/api/routes/notifications.py — Admin notification queue endpoints."""

from __future__ import annotations

from flask import Blueprint, request, jsonify

from db.models import Notification
from middleware.auth import require_admin
from services.notifications import send_queued

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/", methods=["GET"])
@require_admin
def list_notifications():
    status = request.args.get("status")
    q = Notification.query
    if status:
        q = q.filter_by(status=status)
    rows = q.order_by(Notification.created_at.desc()).limit(200).all()
    return jsonify([n.to_dict() for n in rows])


@notifications_bp.route("/send", methods=["POST"])
@require_admin
def send_now():
    data = request.get_json() or {}
    limit = int(data.get("limit") or 25)
    return jsonify(send_queued(limit=limit))

