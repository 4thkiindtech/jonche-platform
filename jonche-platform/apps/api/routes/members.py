"""apps/api/routes/members.py — VIP member endpoints (DB-backed)."""

from flask import Blueprint, request, jsonify, g
from db import db
from db.models import Member
from middleware.auth import require_admin, require_member

members_bp = Blueprint("members", __name__)


@members_bp.route("/")
@require_admin
def list_members():
    tier = request.args.get("tier")
    q = Member.query
    if tier:
        q = q.filter_by(tier=tier)
    members = q.order_by(Member.lifetime_spend.desc()).all()
    return jsonify([m.to_dict() for m in members])


@members_bp.route("/<int:member_id>")
@require_admin
def get_member(member_id):
    member = Member.query.get_or_404(member_id)
    return jsonify(member.to_dict())


@members_bp.route("/count")
@require_admin
def count():
    all_members = Member.query.all()
    return jsonify({
        "total": len(all_members),
        "gold":   sum(1 for m in all_members if m.tier == "gold"),
        "silver": sum(1 for m in all_members if m.tier == "silver"),
        "bronze": sum(1 for m in all_members if m.tier == "bronze"),
    })


@members_bp.route("/<int:member_id>/blacklist", methods=["POST"])
@require_admin
def blacklist_member(member_id):
    member = Member.query.get_or_404(member_id)
    data = request.get_json() or {}
    member.is_blacklisted = True
    member.blacklist_reason = data.get("reason", "Policy violation")
    db.session.commit()
    return jsonify({"message": f"{member.name} blacklisted", "member": member.to_dict()})


@members_bp.route("/<int:member_id>/unblacklist", methods=["POST"])
@require_admin
def unblacklist_member(member_id):
    member = Member.query.get_or_404(member_id)
    member.is_blacklisted = False
    member.blacklist_reason = None
    db.session.commit()
    return jsonify({"message": f"{member.name} reinstated", "member": member.to_dict()})


@members_bp.route("/me", methods=["GET"])
@require_member
def my_profile():
    return jsonify(g.current_member.to_dict())
