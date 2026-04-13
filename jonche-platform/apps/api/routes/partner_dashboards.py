"""
apps/api/routes/partner_dashboards.py
API endpoints for role-based partner dashboards.
Includes auth, earnings, referrals, messages, announcements.
"""

from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

from db import db
from db.models import (
    AffiliateAccount, ReferralPartnerAccount, RetailPartnerAccount, ExecutiveAccount,
    AffiliateEarning, PartnerReferral, PartnerMessage, PartnerAnnouncement
)
from services.partner_notifications import PartnerNotifications

dashboards_bp = Blueprint("dashboards", __name__, url_prefix="/api/dashboards")


# ── Authentication Decorators ────────────────────────────────────────────────

def require_affiliate_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "affiliate_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        kwargs["affiliate_id"] = session["affiliate_id"]
        return f(*args, **kwargs)
    return decorated_function


def require_referral_partner_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "referral_partner_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        kwargs["referral_partner_id"] = session["referral_partner_id"]
        return f(*args, **kwargs)
    return decorated_function


def require_retail_partner_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "retail_partner_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        kwargs["retail_partner_id"] = session["retail_partner_id"]
        return f(*args, **kwargs)
    return decorated_function


def require_executive_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "executive_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        kwargs["executive_id"] = session["executive_id"]
        return f(*args, **kwargs)
    return decorated_function


# ────────────────────────────────────────────────────────────────────────────
# AFFILIATE CREATOR ENDPOINTS
# ────────────────────────────────────────────────────────────────────────────

@dashboards_bp.route("/affiliate/register", methods=["POST"])
def affiliate_register():
    """Register a new affiliate creator account."""
    data = request.get_json() or {}
    
    required = ["email", "password", "display_name"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Missing field: {field}"}), 400
    
    if AffiliateAccount.query.filter_by(email=data["email"].lower()).first():
        return jsonify({"error": "Email already registered"}), 409
    
    affiliate = AffiliateAccount(
        email=data["email"].lower(),
        password_hash=generate_password_hash(data["password"]),
        display_name=data["display_name"],
        bio=data.get("bio"),
        instagram_handle=data.get("instagram_handle"),
        tiktok_handle=data.get("tiktok_handle"),
        youtube_handle=data.get("youtube_handle"),
        website_url=data.get("website_url"),
        commission_rate_percent=float(data.get("commission_rate_percent", 10.0)),
    )
    
    db.session.add(affiliate)
    db.session.commit()
    
    session["affiliate_id"] = affiliate.id
    return jsonify({"message": "Registered successfully", "affiliate": affiliate.to_dict()}), 201


@dashboards_bp.route("/affiliate/login", methods=["POST"])
def affiliate_login():
    """Affiliate creator login."""
    data = request.get_json() or {}
    
    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400
    
    affiliate = AffiliateAccount.query.filter_by(email=data["email"].lower()).first()
    if not affiliate or not check_password_hash(affiliate.password_hash, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401
    
    if affiliate.status != "active":
        return jsonify({"error": "Account is not active"}), 403
    
    affiliate.last_login = datetime.utcnow()
    db.session.commit()
    
    session["affiliate_id"] = affiliate.id
    return jsonify({"message": "Logged in successfully", "affiliate": affiliate.to_dict()}), 200


@dashboards_bp.route("/affiliate/logout", methods=["POST"])
def affiliate_logout():
    """Affiliate logout."""
    session.pop("affiliate_id", None)
    return jsonify({"message": "Logged out"}), 200


@dashboards_bp.route("/affiliate/dashboard", methods=["GET"])
@require_affiliate_login
def affiliate_dashboard(affiliate_id):
    """Get affiliate dashboard summary."""
    affiliate = AffiliateAccount.query.get(affiliate_id)
    if not affiliate:
        return jsonify({"error": "Not found"}), 404
    
    # Get recent earnings
    recent_earnings = AffiliateEarning.query.filter_by(affiliate_id=affiliate_id).order_by(
        AffiliateEarning.created_at.desc()
    ).limit(5).all()
    
    return jsonify({
        "profile": affiliate.to_dict(),
        "recent_earnings": [e.to_dict() for e in recent_earnings],
        "dashboard_tabs": ["earnings", "referrals", "assets", "messages", "profile"],
    }), 200


@dashboards_bp.route("/affiliate/earnings", methods=["GET"])
@require_affiliate_login
def affiliate_earnings(affiliate_id):
    """Get affiliate earnings history."""
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    status_filter = request.args.get("status")  # pending, approved, paid
    
    query = AffiliateEarning.query.filter_by(affiliate_id=affiliate_id)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    earnings = query.order_by(AffiliateEarning.created_at.desc()).paginate(page=page, per_page=limit)
    
    return jsonify({
        "earnings": [e.to_dict() for e in earnings.items],
        "total": earnings.total,
        "pages": earnings.pages,
        "current_page": page,
    }), 200


@dashboards_bp.route("/affiliate/profile", methods=["GET", "PUT"])
@require_affiliate_login
def affiliate_profile(affiliate_id):
    """Get or update affiliate profile."""
    affiliate = AffiliateAccount.query.get(affiliate_id)
    if not affiliate:
        return jsonify({"error": "Not found"}), 404
    
    if request.method == "GET":
        return jsonify(affiliate.to_dict()), 200
    
    # PUT - update profile
    data = request.get_json() or {}
    
    # Only allow updating certain fields
    allowed_fields = ["display_name", "bio", "profile_image_url", "instagram_handle", 
                     "tiktok_handle", "youtube_handle", "website_url"]
    
    for field in allowed_fields:
        if field in data:
            setattr(affiliate, field, data[field])
    
    db.session.commit()
    return jsonify({"message": "Profile updated", "affiliate": affiliate.to_dict()}), 200


# ────────────────────────────────────────────────────────────────────────────
# REFERRAL PARTNER ENDPOINTS
# ────────────────────────────────────────────────────────────────────────────

@dashboards_bp.route("/referral-partner/register", methods=["POST"])
def referral_partner_register():
    """Register a new referral partner account."""
    data = request.get_json() or {}
    
    required = ["email", "password", "contact_name", "company_name"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Missing field: {field}"}), 400
    
    if ReferralPartnerAccount.query.filter_by(email=data["email"].lower()).first():
        return jsonify({"error": "Email already registered"}), 409
    
    partner = ReferralPartnerAccount(
        email=data["email"].lower(),
        password_hash=generate_password_hash(data["password"]),
        contact_name=data["contact_name"],
        company_name=data["company_name"],
        phone=data.get("phone"),
        city=data.get("city"),
        state=data.get("state"),
    )
    
    db.session.add(partner)
    db.session.commit()
    
    session["referral_partner_id"] = partner.id
    return jsonify({"message": "Registered successfully", "partner": partner.to_dict()}), 201


@dashboards_bp.route("/referral-partner/login", methods=["POST"])
def referral_partner_login():
    """Referral partner login."""
    data = request.get_json() or {}
    
    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400
    
    partner = ReferralPartnerAccount.query.filter_by(email=data["email"].lower()).first()
    if not partner or not check_password_hash(partner.password_hash, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401
    
    if partner.status != "active":
        return jsonify({"error": "Account is not active"}), 403
    
    partner.last_login = datetime.utcnow()
    db.session.commit()
    
    session["referral_partner_id"] = partner.id
    return jsonify({"message": "Logged in successfully", "partner": partner.to_dict()}), 200


@dashboards_bp.route("/referral-partner/logout", methods=["POST"])
def referral_partner_logout():
    """Referral partner logout."""
    session.pop("referral_partner_id", None)
    return jsonify({"message": "Logged out"}), 200


@dashboards_bp.route("/referral-partner/dashboard", methods=["GET"])
@require_referral_partner_login
def referral_partner_dashboard(referral_partner_id):
    """Get referral partner dashboard summary."""
    partner = ReferralPartnerAccount.query.get(referral_partner_id)
    if not partner:
        return jsonify({"error": "Not found"}), 404
    
    # Get recent referrals
    recent_referrals = PartnerReferral.query.filter_by(
        referral_partner_id=referral_partner_id
    ).order_by(PartnerReferral.created_at.desc()).limit(5).all()
    
    return jsonify({
        "profile": partner.to_dict(),
        "recent_referrals": [r.to_dict() for r in recent_referrals],
        "dashboard_tabs": ["deals", "pipeline", "commission", "messages", "profile"],
    }), 200


@dashboards_bp.route("/referral-partner/referrals", methods=["GET"])
@require_referral_partner_login
def referral_partner_referrals(referral_partner_id):
    """Get referral partner's deals/referrals."""
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    status_filter = request.args.get("status")
    
    query = PartnerReferral.query.filter_by(referral_partner_id=referral_partner_id)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    referrals = query.order_by(PartnerReferral.created_at.desc()).paginate(page=page, per_page=limit)
    
    return jsonify({
        "referrals": [r.to_dict() for r in referrals.items],
        "total": referrals.total,
        "pages": referrals.pages,
        "current_page": page,
    }), 200


@dashboards_bp.route("/referral-partner/submit-referral", methods=["POST"])
@require_referral_partner_login
def submit_referral(referral_partner_id):
    """Submit a new referral/deal."""
    data = request.get_json() or {}
    
    required = ["referral_type", "title", "estimated_value_cents", "commission_percent"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400
    
    referral = PartnerReferral(
        referral_partner_id=referral_partner_id,
        referral_type=data["referral_type"],
        title=data["title"],
        description=data.get("description"),
        estimated_value_cents=int(data["estimated_value_cents"]),
        commission_percent=float(data["commission_percent"]),
        status="submitted",
    )
    
    db.session.add(referral)
    
    # Update partner's deal count
    partner = ReferralPartnerAccount.query.get(referral_partner_id)
    partner.total_deals_submitted += 1
    
    db.session.flush()  # Get referral.id
    
    # Send confirmation email
    PartnerNotifications.notify_referral_submitted(
        email=partner.email,
        partner_name=partner.contact_name,
        deal_title=referral.title,
        estimated_value=referral.estimated_value_cents or 0,
        commission_pct=referral.commission_percent or 0,
    )
    
    db.session.commit()
    
    return jsonify({"message": "Referral submitted", "referral": referral.to_dict()}), 201


# ────────────────────────────────────────────────────────────────────────────
# RETAIL PARTNER ENDPOINTS
# ────────────────────────────────────────────────────────────────────────────

@dashboards_bp.route("/retail-partner/register", methods=["POST"])
def retail_partner_register():
    """Register a new retail alliance partner."""
    data = request.get_json() or {}
    
    required = ["email", "password", "store_name", "contact_name"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Missing field: {field}"}), 400
    
    if RetailPartnerAccount.query.filter_by(email=data["email"].lower()).first():
        return jsonify({"error": "Email already registered"}), 409
    
    partner = RetailPartnerAccount(
        email=data["email"].lower(),
        password_hash=generate_password_hash(data["password"]),
        store_name=data["store_name"],
        contact_name=data["contact_name"],
        phone=data.get("phone"),
        city=data.get("city"),
        state=data.get("state"),
        website_url=data.get("website_url"),
        tier=data.get("tier", "basic"),
    )
    
    db.session.add(partner)
    db.session.commit()
    
    session["retail_partner_id"] = partner.id
    return jsonify({"message": "Registered successfully", "partner": partner.to_dict()}), 201


@dashboards_bp.route("/retail-partner/login", methods=["POST"])
def retail_partner_login():
    """Retail partner login."""
    data = request.get_json() or {}
    
    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400
    
    partner = RetailPartnerAccount.query.filter_by(email=data["email"].lower()).first()
    if not partner or not check_password_hash(partner.password_hash, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401
    
    if partner.status != "active":
        return jsonify({"error": "Account is not active"}), 403
    
    partner.last_login = datetime.utcnow()
    db.session.commit()
    
    session["retail_partner_id"] = partner.id
    return jsonify({"message": "Logged in successfully", "partner": partner.to_dict()}), 200


@dashboards_bp.route("/retail-partner/logout", methods=["POST"])
def retail_partner_logout():
    """Retail partner logout."""
    session.pop("retail_partner_id", None)
    return jsonify({"message": "Logged out"}), 200


@dashboards_bp.route("/retail-partner/dashboard", methods=["GET"])
@require_retail_partner_login
def retail_partner_dashboard(retail_partner_id):
    """Get retail partner dashboard."""
    partner = RetailPartnerAccount.query.get(retail_partner_id)
    if not partner:
        return jsonify({"error": "Not found"}), 404
    
    return jsonify({
        "profile": partner.to_dict(),
        "dashboard_tabs": ["orders", "allocations", "products", "messages", "profile"],
    }), 200


# ────────────────────────────────────────────────────────────────────────────
# EXECUTIVE ENDPOINTS
# ────────────────────────────────────────────────────────────────────────────

@dashboards_bp.route("/executive/register", methods=["POST"])
def executive_register():
    """Register a new executive partner account."""
    data = request.get_json() or {}
    
    required = ["email", "password", "executive_name", "company_name"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Missing field: {field}"}), 400
    
    if ExecutiveAccount.query.filter_by(email=data["email"].lower()).first():
        return jsonify({"error": "Email already registered"}), 409
    
    executive = ExecutiveAccount(
        email=data["email"].lower(),
        password_hash=generate_password_hash(data["password"]),
        executive_name=data["executive_name"],
        company_name=data["company_name"],
        phone=data.get("phone"),
        city=data.get("city"),
        state=data.get("state"),
        territory=data.get("territory"),
    )
    
    db.session.add(executive)
    db.session.commit()
    
    session["executive_id"] = executive.id
    return jsonify({"message": "Registered successfully", "executive": executive.to_dict()}), 201


@dashboards_bp.route("/executive/login", methods=["POST"])
def executive_login():
    """Executive login."""
    data = request.get_json() or {}
    
    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400
    
    executive = ExecutiveAccount.query.filter_by(email=data["email"].lower()).first()
    if not executive or not check_password_hash(executive.password_hash, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401
    
    if executive.status != "active":
        return jsonify({"error": "Account is not active"}), 403
    
    executive.last_login = datetime.utcnow()
    db.session.commit()
    
    session["executive_id"] = executive.id
    return jsonify({"message": "Logged in successfully", "executive": executive.to_dict()}), 200


@dashboards_bp.route("/executive/logout", methods=["POST"])
def executive_logout():
    """Executive logout."""
    session.pop("executive_id", None)
    return jsonify({"message": "Logged out"}), 200


@dashboards_bp.route("/executive/dashboard", methods=["GET"])
@require_executive_login
def executive_dashboard(executive_id):
    """Get executive dashboard summary."""
    executive = ExecutiveAccount.query.get(executive_id)
    if not executive:
        return jsonify({"error": "Not found"}), 404
    
    # Get recent deals
    recent_deals = PartnerReferral.query.filter_by(
        executive_id=executive_id
    ).order_by(PartnerReferral.created_at.desc()).limit(5).all()
    
    return jsonify({
        "profile": executive.to_dict(),
        "recent_deals": [d.to_dict() for d in recent_deals],
        "dashboard_tabs": ["deals", "opportunities", "commission", "messages", "profile"],
    }), 200


# ────────────────────────────────────────────────────────────────────────────
# SHARED ENDPOINTS (Messages, Announcements)
# ────────────────────────────────────────────────────────────────────────────

@dashboards_bp.route("/messages", methods=["GET", "POST"])
def messages():
    """Get or send messages (role-agnostic)."""
    # Determine which partner type is logged in
    affiliate_id = session.get("affiliate_id")
    referral_partner_id = session.get("referral_partner_id")
    retail_partner_id = session.get("retail_partner_id")
    executive_id = session.get("executive_id")
    
    if not any([affiliate_id, referral_partner_id, retail_partner_id, executive_id]):
        return jsonify({"error": "Unauthorized"}), 401
    
    if request.method == "POST":
        data = request.get_json() or {}
        
        message = PartnerMessage(
            subject=data.get("subject"),
            body=data.get("body"),
            message_type=data.get("message_type", "general"),
            affiliate_id=affiliate_id,
            referral_partner_id=referral_partner_id,
            retail_partner_id=retail_partner_id,
            executive_id=executive_id,
            created_by_admin=False,
        )
        db.session.add(message)
        db.session.commit()
        return jsonify({"message": "Message sent", "msg": message.to_dict()}), 201
    
    # GET - retrieve messages
    query = PartnerMessage.query
    if affiliate_id:
        query = query.filter_by(affiliate_id=affiliate_id)
    elif referral_partner_id:
        query = query.filter_by(referral_partner_id=referral_partner_id)
    elif retail_partner_id:
        query = query.filter_by(retail_partner_id=retail_partner_id)
    elif executive_id:
        query = query.filter_by(executive_id=executive_id)
    
    messages_list = query.order_by(PartnerMessage.created_at.desc()).limit(50).all()
    
    return jsonify({"messages": [m.to_dict() for m in messages_list]}), 200


@dashboards_bp.route("/announcements", methods=["GET"])
def announcements():
    """Get active announcements for partner."""
    affiliate_id = session.get("affiliate_id")
    referral_partner_id = session.get("referral_partner_id")
    retail_partner_id = session.get("retail_partner_id")
    executive_id = session.get("executive_id")
    
    if not any([affiliate_id, referral_partner_id, retail_partner_id, executive_id]):
        return jsonify({"error": "Unauthorized"}), 401
    
    # Determine target group
    target_group = None
    if affiliate_id:
        target_group = "affiliates"
    elif referral_partner_id:
        target_group = "referral_partners"
    elif retail_partner_id:
        target_group = "retail_partners"
    elif executive_id:
        target_group = "executives"
    
    now = datetime.utcnow()
    announcements_list = PartnerAnnouncement.query.filter(
        PartnerAnnouncement.status == "published",
        PartnerAnnouncement.published_at <= now,
        (PartnerAnnouncement.expires_at > now) | (PartnerAnnouncement.expires_at.is_(None))
    ).filter(
        (PartnerAnnouncement.target_groups.like(f"%{target_group}%")) |
        (PartnerAnnouncement.target_groups.like("%all%"))
    ).order_by(PartnerAnnouncement.priority.desc(), PartnerAnnouncement.published_at.desc()).all()
    
    return jsonify({"announcements": [a.to_dict() for a in announcements_list]}), 200
