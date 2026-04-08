"""
apps/api/middleware/auth.py
JWT-based auth decorators for admin, member, and retailer routes.
"""

import os
import jwt
from functools import wraps
from datetime import datetime, timedelta
from flask import request, jsonify, g

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
JWT_EXPIRY_HOURS = 24


# ── Token generation ──────────────────────────────────────────────────────────

def generate_token(subject_id: int, role: str) -> str:
    """Generate a signed JWT for admin, member, or retailer."""
    payload = {
        "sub": subject_id,
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])


def _get_token_from_request() -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return (
        request.cookies.get("jonche_token")
        or request.cookies.get("jonche_admin_token")
        or request.cookies.get("jonche_retailer_token")
        or request.cookies.get("jonche_member_token")
    )


# ── Decorators ────────────────────────────────────────────────────────────────

def require_admin(f):
    """Restrict route to authenticated admins only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _get_token_from_request()
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        try:
            payload = decode_token(token)
            if payload.get("role") != "admin":
                return jsonify({"error": "Admin access required"}), 403
            from db.models import Admin
            admin = Admin.query.get(payload["sub"])
            if not admin:
                return jsonify({"error": "Admin not found"}), 401
            g.current_admin = admin
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated


def require_member(f):
    """Restrict route to authenticated VIP members."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _get_token_from_request()
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        try:
            payload = decode_token(token)
            if payload.get("role") not in ("member", "admin"):
                return jsonify({"error": "Member access required"}), 403
            from db.models import Member
            member = Member.query.get(payload["sub"])
            if not member:
                return jsonify({"error": "Member not found"}), 401
            if member.is_blacklisted:
                return jsonify({"error": "Account suspended"}), 403
            g.current_member = member
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated


def require_retailer(f):
    """Restrict route to authenticated retailers (via API key or JWT)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Try API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            from db.models import Retailer
            retailer = Retailer.query.filter_by(api_key=api_key, status="active").first()
            if retailer:
                g.current_retailer = retailer
                return f(*args, **kwargs)

        # Fall back to JWT
        token = _get_token_from_request()
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        try:
            payload = decode_token(token)
            if payload.get("role") not in ("retailer", "admin"):
                return jsonify({"error": "Retailer access required"}), 403
            from db.models import Retailer
            retailer = Retailer.query.get(payload["sub"])
            if not retailer or retailer.status != "active":
                return jsonify({"error": "Retailer account inactive"}), 403
            g.current_retailer = retailer
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return jsonify({"error": "Invalid or expired token"}), 401
        return f(*args, **kwargs)
    return decorated


def require_admin_or_member(f):
    """Allow either admins or members."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _get_token_from_request()
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        try:
            payload = decode_token(token)
            role = payload.get("role")
            if role == "admin":
                from db.models import Admin
                g.current_admin = Admin.query.get(payload["sub"])
            elif role == "member":
                from db.models import Member
                member = Member.query.get(payload["sub"])
                if not member or member.is_blacklisted:
                    return jsonify({"error": "Account not found or suspended"}), 403
                g.current_member = member
            else:
                return jsonify({"error": "Access denied"}), 403
            g.current_role = role
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return jsonify({"error": "Invalid or expired token"}), 401
        return f(*args, **kwargs)
    return decorated
