"""apps/api/routes/waitlist.py — Raffle/waitlist management."""

import random
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from db import db
from db.models import WaitlistEntry, Drop, Member
from middleware.auth import require_admin, require_member
from services.notifications import enqueue_email

waitlist_bp = Blueprint("waitlist", __name__)


@waitlist_bp.route("/<int:drop_id>/enter", methods=["POST"])
@require_member
def enter_waitlist(drop_id):
    drop = Drop.query.get_or_404(drop_id)
    member = g.current_member

    if drop.status not in ("upcoming", "live"):
        return jsonify({"error": "Drop is not accepting entries"}), 400

    if not drop.use_raffle:
        return jsonify({"error": "This drop does not use a raffle"}), 400

    existing = WaitlistEntry.query.filter_by(
        drop_id=drop_id, member_id=member.id
    ).first()
    if existing:
        return jsonify({"error": "Already entered", "entry": existing.to_dict()}), 409

    data = request.get_json() or {}
    if "size" not in data:
        return jsonify({"error": "Size is required"}), 400

    entry = WaitlistEntry(
        drop_id=drop_id,
        member_id=member.id,
        size=data["size"],
        status="entered",
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({"message": "Entered successfully", "entry": entry.to_dict()}), 201


@waitlist_bp.route("/<int:drop_id>/entries", methods=["GET"])
@require_admin
def list_entries(drop_id):
    entries = WaitlistEntry.query.filter_by(drop_id=drop_id).all()
    return jsonify([e.to_dict() for e in entries])


@waitlist_bp.route("/<int:drop_id>/draw", methods=["POST"])
@require_admin
def run_raffle(drop_id):
    """Randomly select winners from entered waitlist entries."""
    drop = Drop.query.get_or_404(drop_id)
    data = request.get_json() or {}
    winner_count = data.get("winner_count", drop.units_available)

    entered = WaitlistEntry.query.filter_by(
        drop_id=drop_id, status="entered"
    ).all()

    if not entered:
        return jsonify({"error": "No entries to draw from"}), 400

    winner_count = min(winner_count, len(entered))
    winners = random.sample(entered, winner_count)
    winner_ids = {w.id for w in winners}

    now = datetime.utcnow()
    selected = []
    not_selected = []

    for entry in entered:
        if entry.id in winner_ids:
            entry.status = "selected"
            entry.selected_at = now
            selected.append(entry.to_dict())
        else:
            entry.status = "not_selected"
            not_selected.append(entry.to_dict())

    db.session.commit()

    # Email results (best-effort)
    try:
        for entry in entered:
            if not entry.member or not entry.member.email:
                continue
            if entry.status == "selected":
                subject = "JONCHE Raffle Result — You’re In"
                body = f"<p>You were selected for <b>{drop.name}</b>. Complete checkout when the drop is live.</p>"
            else:
                subject = "JONCHE Raffle Result — Not This Time"
                body = f"<p>You were not selected for <b>{drop.name}</b>. You’ll stay eligible for future drops.</p>"
            enqueue_email(
                recipient_email=entry.member.email,
                recipient_name=entry.member.name,
                subject=subject,
                body_html=body,
                notif_type="waitlist_result",
                related_id=entry.id,
            )
    except Exception:
        pass

    return jsonify({
        "winners_count": len(selected),
        "not_selected_count": len(not_selected),
        "winners": selected,
    })


@waitlist_bp.route("/my-entries", methods=["GET"])
@require_member
def my_entries():
    entries = WaitlistEntry.query.filter_by(member_id=g.current_member.id).all()
    return jsonify([e.to_dict() for e in entries])
