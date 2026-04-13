"""
apps/api/routes/admin_partners.py
Admin endpoints for managing partner accounts, applications, and commissions.
Requires admin login.
"""

from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from sqlalchemy import func

from db import db
from db.models import (
    PartnerApplication,
    AffiliateAccount, ReferralPartnerAccount, RetailPartnerAccount, ExecutiveAccount,
    AffiliateEarning, PartnerReferral, PartnerMessage, PartnerAnnouncement,
    Admin
)
from middleware.auth import require_admin
from services.partner_notifications import PartnerNotifications

admin_partners_bp = Blueprint("admin_partners", __name__, url_prefix="/api/admin/partners")


# ────────────────────────────────────────────────────────────────────────────
# PARTNER APPLICATIONS
# ────────────────────────────────────────────────────────────────────────────

@admin_partners_bp.route("/applications", methods=["GET"])
@require_admin
def list_partner_applications():
    """Get all partner applications."""
    status_filter = request.args.get("status")  # new, contacted, approved, rejected
    program_filter = request.args.get("program")
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 50, type=int)
    
    query = PartnerApplication.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    if program_filter:
        query = query.filter_by(program_type=program_filter)
    
    apps = query.order_by(PartnerApplication.created_at.desc()).paginate(
        page=page, per_page=limit
    )
    
    return jsonify({
        "applications": [a.to_dict() for a in apps.items],
        "total": apps.total,
        "pages": apps.pages,
        "current_page": page,
    }), 200


@admin_partners_bp.route("/applications/<int:app_id>", methods=["GET", "PUT"])
@require_admin
def manage_application(app_id):
    """Get or update application status."""
    app = PartnerApplication.query.get(app_id)
    if not app:
        return jsonify({"error": "Not found"}), 404
    
    if request.method == "GET":
        return jsonify(app.to_dict()), 200
    
    # PUT - update status
    data = request.get_json() or {}
    new_status = data.get("status")  # contacted, approved, rejected
    
    if new_status not in ["new", "contacted", "approved", "rejected"]:
        return jsonify({"error": "Invalid status"}), 400
    
    app.status = new_status
    
    # Send email notification if approved
    if new_status == "approved":
        PartnerNotifications.notify_application_approved(
            email=app.email,
            name=app.full_name,
            program_type=app.program_type,
        )
    
    db.session.commit()
    
    return jsonify({"message": "Updated", "application": app.to_dict()}), 200


@admin_partners_bp.route("/applications/<int:app_id>/auto-create", methods=["POST"])
@require_admin
def auto_create_from_application(app_id):
    """Auto-create partner account from application."""
    app = PartnerApplication.query.get(app_id)
    if not app:
        return jsonify({"error": "Not found"}), 404
    
    if app.status != "approved":
        return jsonify({"error": "Application must be approved first"}), 400
    
    program_type = app.program_type  # affiliate_creators, referral_network, retail_alliance, executives
    
    try:
        if program_type == "affiliate_creators":
            account = AffiliateAccount(
                email=app.email,
                password_hash="temp",  # Admin should reset
                display_name=app.full_name,
                bio=app.additional_notes,
                website_url=app.website_or_social,
            )
            db.session.add(account)
            db.session.commit()
            return jsonify({"message": "Affiliate account created", "account": account.to_dict()}), 201
        
        elif program_type == "referral_network":
            account = ReferralPartnerAccount(
                email=app.email,
                password_hash="temp",
                contact_name=app.full_name,
                company_name=app.business_name,
                phone=app.phone,
                city=app.city,
                state=app.state,
            )
            db.session.add(account)
            db.session.commit()
            return jsonify({"message": "Referral partner account created", "account": account.to_dict()}), 201
        
        elif program_type == "retail_alliance":
            account = RetailPartnerAccount(
                email=app.email,
                password_hash="temp",
                store_name=app.business_name or app.full_name,
                contact_name=app.full_name,
                phone=app.phone,
                city=app.city,
                state=app.state,
                website_url=app.website_or_social,
            )
            db.session.add(account)
            db.session.commit()
            return jsonify({"message": "Retail partner account created", "account": account.to_dict()}), 201
        
        elif program_type == "executives":
            account = ExecutiveAccount(
                email=app.email,
                password_hash="temp",
                executive_name=app.full_name,
                company_name=app.business_name or "Unknown",
                phone=app.phone,
                city=app.city,
                state=app.state,
                territory=app.city,  # Use city as default territory
            )
            db.session.add(account)
            db.session.commit()
            return jsonify({"message": "Executive account created", "account": account.to_dict()}), 201
        
        else:
            return jsonify({"error": "Unknown program type"}), 400
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ────────────────────────────────────────────────────────────────────────────
# AFFILIATE MANAGEMENT
# ────────────────────────────────────────────────────────────────────────────

@admin_partners_bp.route("/affiliates", methods=["GET"])
@require_admin
def list_affiliates():
    """Get all affiliate accounts with performance summaries."""
    status = request.args.get("status")  # active, suspended, inactive
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 50, type=int)
    
    query = AffiliateAccount.query
    if status:
        query = query.filter_by(status=status)
    
    affiliates = query.order_by(
        AffiliateAccount.total_earnings_cents.desc()
    ).paginate(page=page, per_page=limit)
    
    return jsonify({
        "affiliates": [a.to_dict() for a in affiliates.items],
        "total": affiliates.total,
        "pages": affiliates.pages,
    }), 200


@admin_partners_bp.route("/affiliates/<int:affiliate_id>", methods=["GET", "PUT"])
@require_admin
def manage_affiliate(affiliate_id):
    """Get affiliate details or update status."""
    affiliate = AffiliateAccount.query.get(affiliate_id)
    if not affiliate:
        return jsonify({"error": "Not found"}), 404
    
    if request.method == "GET":
        # Get with earnings summary
        recent_earnings = AffiliateEarning.query.filter_by(
            affiliate_id=affiliate_id
        ).order_by(AffiliateEarning.created_at.desc()).limit(10).all()
        
        return jsonify({
            "affiliate": affiliate.to_dict(),
            "recent_earnings": [e.to_dict() for e in recent_earnings],
            "earnings_summary": {
                "pending": db.session.query(
                    func.count(AffiliateEarning.id),
                    func.sum(AffiliateEarning.commission_cents)
                ).filter_by(
                    affiliate_id=affiliate_id, status="pending"
                ).first(),
            }
        }), 200
    
    # PUT - update status or details
    data = request.get_json() or {}
    
    if "status" in data:
        if data["status"] not in ["active", "suspended", "inactive"]:
            return jsonify({"error": "Invalid status"}), 400
        affiliate.status = data["status"]
    
    if "commission_rate_percent" in data:
        affiliate.commission_rate_percent = float(data["commission_rate_percent"])
    
    db.session.commit()
    return jsonify({"message": "Updated", "affiliate": affiliate.to_dict()}), 200


@admin_partners_bp.route("/affiliates/<int:affiliate_id>/earnings", methods=["GET"])
@require_admin
def affiliate_earnings(affiliate_id):
    """Get detailed earnings for an affiliate."""
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 50, type=int)
    status_filter = request.args.get("status")
    
    query = AffiliateEarning.query.filter_by(affiliate_id=affiliate_id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    earnings = query.order_by(
        AffiliateEarning.created_at.desc()
    ).paginate(page=page, per_page=limit)
    
    return jsonify({
        "earnings": [e.to_dict() for e in earnings.items],
        "total": earnings.total,
        "pages": earnings.pages,
    }), 200


@admin_partners_bp.route("/affiliates/<int:affiliate_id>/approve-earnings", methods=["POST"])
@require_admin
def approve_affiliate_earnings(affiliate_id):
    """Approve pending earnings for an affiliate."""
    data = request.get_json() or {}
    earning_ids = data.get("earning_ids", [])
    
    if not earning_ids:
        return jsonify({"error": "No earnings specified"}), 400
    
    earnings = AffiliateEarning.query.filter(
        AffiliateEarning.id.in_(earning_ids),
        AffiliateEarning.affiliate_id == affiliate_id,
        AffiliateEarning.status == "pending"
    ).all()
    
    total_approved = 0
    for earning in earnings:
        earning.status = "approved"
        total_approved += earning.commission_cents
    
    # Update affiliate totals
    affiliate = AffiliateAccount.query.get(affiliate_id)
    affiliate.pending_earnings_cents += total_approved
    
    # Send email notification
    if total_approved > 0 and affiliate.email:
        PartnerNotifications.notify_commission_approved(
            email=affiliate.email,
            partner_name=affiliate.display_name,
            commission_cents=total_approved,
            reason=f"Approved {len(earnings)} referral earnings",
        )
    
    db.session.commit()
    
    return jsonify({
        "message": f"Approved {len(earnings)} earnings",
        "total_approved_cents": total_approved,
    }), 200


# ────────────────────────────────────────────────────────────────────────────
# REFERRAL PARTNER MANAGEMENT
# ────────────────────────────────────────────────────────────────────────────

@admin_partners_bp.route("/referral-partners", methods=["GET"])
@require_admin
def list_referral_partners():
    """Get all referral partners with pipeline summary."""
    tier = request.args.get("tier")  # bronze, silver, gold
    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 50, type=int)
    
    query = ReferralPartnerAccount.query
    if tier:
        query = query.filter_by(tier=tier)
    if status:
        query = query.filter_by(status=status)
    
    partners = query.order_by(
        ReferralPartnerAccount.total_deal_value_cents.desc()
    ).paginate(page=page, per_page=limit)
    
    return jsonify({
        "referral_partners": [p.to_dict() for p in partners.items],
        "total": partners.total,
        "pages": partners.pages,
    }), 200


@admin_partners_bp.route("/referral-partners/<int:partner_id>", methods=["GET", "PUT"])
@require_admin
def manage_referral_partner(partner_id):
    """Get or manage referral partner."""
    partner = ReferralPartnerAccount.query.get(partner_id)
    if not partner:
        return jsonify({"error": "Not found"}), 404
    
    if request.method == "GET":
        # Get with recent referrals
        recent_referrals = PartnerReferral.query.filter_by(
            referral_partner_id=partner_id
        ).order_by(PartnerReferral.created_at.desc()).limit(10).all()
        
        return jsonify({
            "partner": partner.to_dict(),
            "recent_referrals": [r.to_dict() for r in recent_referrals],
        }), 200
    
    # PUT - update
    data = request.get_json() or {}
    
    if "status" in data:
        partner.status = data["status"]
    if "tier" in data:
        partner.tier = data["tier"]
    
    db.session.commit()
    return jsonify({"message": "Updated", "partner": partner.to_dict()}), 200


@admin_partners_bp.route("/referral-partners/<int:partner_id>/referrals", methods=["GET"])
@require_admin
def partner_referrals(partner_id):
    """Get referrals/deals for a partner."""
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 50, type=int)
    status_filter = request.args.get("status")
    
    query = PartnerReferral.query.filter_by(referral_partner_id=partner_id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    referrals = query.order_by(
        PartnerReferral.created_at.desc()
    ).paginate(page=page, per_page=limit)
    
    return jsonify({
        "referrals": [r.to_dict() for r in referrals.items],
        "total": referrals.total,
    }), 200


@admin_partners_bp.route("/referrals/<int:referral_id>", methods=["GET", "PUT"])
@require_admin
def manage_referral(referral_id):
    """Update referral status (approve/reject/fund)."""
    referral = PartnerReferral.query.get(referral_id)
    if not referral:
        return jsonify({"error": "Not found"}), 404
    
    if request.method == "GET":
        return jsonify(referral.to_dict()), 200
    
    # PUT - update status
    data = request.get_json() or {}
    new_status = data.get("status")
    
    allowed_statuses = ["submitted", "under_review", "approved", "rejected", "funded", "closed", "paid"]
    if new_status and new_status not in allowed_statuses:
        return jsonify({"error": "Invalid status"}), 400
    
    if new_status:
        referral.status = new_status
    
    # Update actual value if provided
    if "actual_value_cents" in data:
        referral.actual_value_cents = int(data["actual_value_cents"])
        # Recalculate commission
        if referral.commission_percent:
            referral.commission_cents = int(referral.actual_value_cents * referral.commission_percent / 100)
    
    # Mark paid if requested
    if data.get("mark_paid"):
        referral.status = "paid"
        referral.paid_at = datetime.utcnow()
        
        # Update partner commission totals and send email
        if referral.referral_partner_id:
            partner = ReferralPartnerAccount.query.get(referral.referral_partner_id)
            partner.total_commission_cents += referral.commission_cents
            partner.pending_commission_cents -= referral.commission_cents
            
            # Send payout notification
            if partner.email:
                PartnerNotifications.notify_payout_processed(
                    email=partner.email,
                    partner_name=partner.contact_name,
                    payout_cents=referral.commission_cents,
                    payout_method="ACH",
                    transaction_id=f"DEAL-{referral.id}",
                )
    
    # Send deal funded notification when status changes to funded
    if new_status == "funded" and referral.referral_partner_id:
        partner = ReferralPartnerAccount.query.get(referral.referral_partner_id)
        if partner and partner.email:
            PartnerNotifications.notify_deal_funded(
                email=partner.email,
                partner_name=partner.contact_name,
                deal_title=referral.title or "Your Deal",
                actual_value=referral.actual_value_cents or referral.estimated_value_cents or 0,
                commission_cents=referral.commission_cents or 0,
            )
    
    db.session.commit()
    return jsonify({"message": "Updated", "referral": referral.to_dict()}), 200


# ────────────────────────────────────────────────────────────────────────────
# ANNOUNCEMENTS MANAGEMENT
# ────────────────────────────────────────────────────────────────────────────

@admin_partners_bp.route("/announcements", methods=["GET", "POST"])
@require_admin
def manage_announcements():
    """Get or create announcements."""
    if request.method == "GET":
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 50, type=int)
        status_filter = request.args.get("status")  # draft, published, archived
        
        query = PartnerAnnouncement.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        announcements = query.order_by(
            PartnerAnnouncement.published_at.desc()
        ).paginate(page=page, per_page=limit)
        
        return jsonify({
            "announcements": [a.to_dict() for a in announcements.items],
            "total": announcements.total,
        }), 200
    
    # POST - create announcement
    data = request.get_json() or {}
    
    required = ["title", "content", "target_groups"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Missing field: {field}"}), 400
    
    # Get admin ID from session
    admin_id = None  # Would come from auth middleware in production
    
    announcement = PartnerAnnouncement(
        title=data["title"],
        content=data["content"],
        target_groups=",".join(data.get("target_groups", [])),
        priority=data.get("priority", "normal"),
        status="draft",
        created_by_admin=admin_id,
    )
    
    db.session.add(announcement)
    db.session.flush()  # Get the ID
    
    # If publish flag is set, broadcast immediately
    if data.get("publish"):
        announcement.status = "published"
        announcement.published_at = datetime.utcnow()
        target_groups = data.get("target_groups", [])
        _broadcast_announcement(announcement, target_groups)
    
    db.session.commit()
    
    return jsonify({"message": "Created", "announcement": announcement.to_dict()}), 201


@admin_partners_bp.route("/announcements/<int:announcement_id>", methods=["GET", "PUT", "DELETE"])
@require_admin
def manage_announcement(announcement_id):
    """Manage specific announcement."""
    announcement = PartnerAnnouncement.query.get(announcement_id)
    if not announcement:
        return jsonify({"error": "Not found"}), 404
    
    if request.method == "GET":
        return jsonify(announcement.to_dict()), 200
    
    if request.method == "DELETE":
        db.session.delete(announcement)
        db.session.commit()
        return jsonify({"message": "Deleted"}), 200
    
    # PUT - update
    data = request.get_json() or {}
    
    if "title" in data:
        announcement.title = data["title"]
    if "content" in data:
        announcement.content = data["content"]
    if "priority" in data:
        announcement.priority = data["priority"]
    if "target_groups" in data:
        announcement.target_groups = ",".join(data["target_groups"])
    
    # Publish
    if data.get("publish"):
        announcement.status = "published"
        announcement.published_at = datetime.utcnow()
        
        # Send email notifications to target groups
        target_groups = announcement.target_groups.split(",") if announcement.target_groups else []
        _broadcast_announcement(announcement, target_groups)
    
    if data.get("expires_at"):
        announcement.expires_at = datetime.fromisoformat(data["expires_at"])
    
    db.session.commit()
    return jsonify({"message": "Updated", "announcement": announcement.to_dict()}), 200


# ────────────────────────────────────────────────────────────────────────────
# ADMIN DASHBOARD / SUMMARIES
# ────────────────────────────────────────────────────────────────────────────

@admin_partners_bp.route("/summary", methods=["GET"])
@require_admin
def admin_summary():
    """Get high-level summary of all partners."""
    total_affiliates = AffiliateAccount.query.count()
    total_referral_partners = ReferralPartnerAccount.query.count()
    total_retail_partners = RetailPartnerAccount.query.count()
    total_executives = ExecutiveAccount.query.count()
    
    # Earnings summary
    total_paid_earnings = db.session.query(func.sum(AffiliateEarning.commission_cents)).filter_by(
        status="paid"
    ).scalar() or 0
    
    total_pending_earnings = db.session.query(func.sum(AffiliateEarning.commission_cents)).filter_by(
        status="pending"
    ).scalar() or 0
    
    # Referrals summary
    total_referral_value = db.session.query(func.sum(PartnerReferral.estimated_value_cents)).scalar() or 0
    funded_referrals = PartnerReferral.query.filter_by(status="funded").count()
    
    return jsonify({
        "partners": {
            "affiliates": {
                "total": total_affiliates,
                "active": AffiliateAccount.query.filter_by(status="active").count(),
            },
            "referral_partners": {
                "total": total_referral_partners,
                "active": ReferralPartnerAccount.query.filter_by(status="active").count(),
            },
            "retail_partners": {
                "total": total_retail_partners,
                "active": RetailPartnerAccount.query.filter_by(status="active").count(),
            },
            "executives": {
                "total": total_executives,
                "active": ExecutiveAccount.query.filter_by(status="active").count(),
            },
        },
        "earnings": {
            "total_paid_cents": total_paid_earnings,
            "total_pending_cents": total_pending_earnings,
            "total_dollars": (total_paid_earnings + total_pending_earnings) / 100,
        },
        "referrals": {
            "total_value_cents": total_referral_value,
            "funded_count": funded_referrals,
        },
    }), 200


# ────────────────────────────────────────────────────────────────────────────
# ANNOUNCEMENT BROADCAST HELPER
# ────────────────────────────────────────────────────────────────────────────

def _broadcast_announcement(announcement: PartnerAnnouncement, target_groups: list) -> int:
    """Send announcement emails to target partner groups.
    
    Returns count of emails sent.
    """
    sent_count = 0
    
    # Map target groups to partner queries
    queries = {
        "affiliate_creators": AffiliateAccount.query.filter_by(status="active"),
        "referral_network": ReferralPartnerAccount.query.filter_by(status="active"),
        "retail_alliance": RetailPartnerAccount.query.filter_by(status="active"),
        "executives": ExecutiveAccount.query.filter_by(status="active"),
    }
    
    for group in target_groups:
        group = group.strip().lower() if group else ""
        if group not in queries:
            continue
        
        partners = queries[group].with_entities(
            db.func.coalesce(AffiliateAccount.email, ReferralPartnerAccount.email,
                            RetailPartnerAccount.email, ExecutiveAccount.email),
            db.func.coalesce(AffiliateAccount.display_name, ReferralPartnerAccount.contact_name,
                            RetailPartnerAccount.contact_name, ExecutiveAccount.executive_name)
        ).all()
        
        # Simpler approach: query each partner type separately
        if group == "affiliate_creators":
            for partner in AffiliateAccount.query.filter_by(status="active").all():
                PartnerNotifications.notify_announcement(
                    email=partner.email,
                    partner_name=partner.display_name,
                    announcement_title=announcement.title,
                    announcement_content=announcement.content,
                    priority=announcement.priority,
                )
                sent_count += 1
        
        elif group == "referral_network":
            for partner in ReferralPartnerAccount.query.filter_by(status="active").all():
                PartnerNotifications.notify_announcement(
                    email=partner.email,
                    partner_name=partner.contact_name,
                    announcement_title=announcement.title,
                    announcement_content=announcement.content,
                    priority=announcement.priority,
                )
                sent_count += 1
        
        elif group == "retail_alliance":
            for partner in RetailPartnerAccount.query.filter_by(status="active").all():
                PartnerNotifications.notify_announcement(
                    email=partner.email,
                    partner_name=partner.contact_name,
                    announcement_title=announcement.title,
                    announcement_content=announcement.content,
                    priority=announcement.priority,
                )
                sent_count += 1
        
        elif group == "executives":
            for partner in ExecutiveAccount.query.filter_by(status="active").all():
                PartnerNotifications.notify_announcement(
                    email=partner.email,
                    partner_name=partner.executive_name,
                    announcement_title=announcement.title,
                    announcement_content=announcement.content,
                    priority=announcement.priority,
                )
                sent_count += 1
    
    return sent_count
