"""
apps/api/routes/auth.py
Login endpoints for admins, members, and retailers.
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, g
from werkzeug.security import check_password_hash, generate_password_hash
from db import db
from db.models import Admin, Member, Retailer
from middleware.auth import generate_token, require_admin, require_member

auth_bp = Blueprint("auth", __name__)


# ── Admin Login ───────────────────────────────────────────────────────────────

@auth_bp.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json()
    if not data or "email" not in data or "password" not in data:
        return jsonify({"error": "Email and password required"}), 400

    admin = Admin.query.filter_by(email=data["email"]).first()
    if not admin or not check_password_hash(admin.password_hash, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    admin.last_login = datetime.utcnow()
    db.session.commit()

    token = generate_token(admin.id, "admin")
    return jsonify({
        "token": token,
        "role": "admin",
        "admin": admin.to_dict(),
    })


@auth_bp.route("/admin/me", methods=["GET"])
@require_admin
def admin_me():
    return jsonify(g.current_admin.to_dict())


# ── Member Login / Register ───────────────────────────────────────────────────

@auth_bp.route("/member/register", methods=["POST"])
def member_register():
    data = request.get_json()
    required = ["email", "password", "name"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    if Member.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    member = Member(
        email=data["email"],
        password_hash=generate_password_hash(data["password"]),
        name=data["name"],
        phone=data.get("phone"),
        tier="bronze",
        lifetime_spend=0.0,
    )
    db.session.add(member)
    db.session.commit()

    token = generate_token(member.id, "member")
    return jsonify({
        "token": token,
        "role": "member",
        "member": member.to_dict(),
    }), 201


@auth_bp.route("/member/login", methods=["POST"])
def member_login():
    data = request.get_json()
    if not data or "email" not in data or "password" not in data:
        return jsonify({"error": "Email and password required"}), 400

    member = Member.query.filter_by(email=data["email"]).first()
    if not member or not check_password_hash(member.password_hash, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    if member.is_blacklisted:
        return jsonify({"error": "Account suspended"}), 403

    member.last_login = datetime.utcnow()
    db.session.commit()

    token = generate_token(member.id, "member")
    return jsonify({
        "token": token,
        "role": "member",
        "member": member.to_dict(),
    })


@auth_bp.route("/member/me", methods=["GET"])
@require_member
def member_me():
    return jsonify(g.current_member.to_dict())


# ── Retailer Login ────────────────────────────────────────────────────────────

@auth_bp.route("/retailer/login", methods=["POST"])
def retailer_login():
    data = request.get_json()
    if not data or "email" not in data or "password" not in data:
        return jsonify({"error": "Email and password required"}), 400

    retailer = Retailer.query.filter_by(email=data["email"]).first()
    if not retailer or not check_password_hash(retailer.password_hash, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    if retailer.status not in ("active", "pending"):
        return jsonify({"error": "Account not yet approved"}), 403

    token = generate_token(retailer.id, "retailer")
    return jsonify({
        "token": token,
        "role": "retailer",
        "retailer": retailer.to_dict(),
        "api_key": retailer.api_key,
    })


# ── Password Change ───────────────────────────────────────────────────────────

@auth_bp.route("/member/change-password", methods=["POST"])
@require_member
def member_change_password():
    data = request.get_json()
    if not data or "current_password" not in data or "new_password" not in data:
        return jsonify({"error": "current_password and new_password required"}), 400

    member = g.current_member
    if not check_password_hash(member.password_hash, data["current_password"]):
        return jsonify({"error": "Current password is incorrect"}), 401

    if len(data["new_password"]) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    member.password_hash = generate_password_hash(data["new_password"])
    db.session.commit()
    return jsonify({"message": "Password updated"})
