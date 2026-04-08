"""apps/api/routes/analytics.py — Real analytics from DB."""

from flask import Blueprint, jsonify
from sqlalchemy import func
from db import db
from db.models import Order, Drop, QRCampaign
from middleware.auth import require_admin

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/revenue")
@require_admin
def revenue():
    rows = db.session.query(
        Drop.name,
        func.sum(Order.total_cents).label("revenue"),
        func.count(Order.id).label("order_count"),
    ).join(Order, Order.drop_id == Drop.id)\
     .filter(Order.status == "completed")\
     .group_by(Drop.id)\
     .order_by(Drop.created_at.asc()).all()

    return jsonify([
        {"drop": r.name, "revenue": int((r.revenue or 0) / 100), "orders": r.order_count}
        for r in rows
    ])


@analytics_bp.route("/hype")
@require_admin
def hype():
    drops = Drop.query.filter(Drop.status.in_(["live", "upcoming", "sold_out"])).all()
    return jsonify([
        {"name": d.name, "hype_pct": d.hype_pct, "units_available": d.units_available}
        for d in drops
    ])


@analytics_bp.route("/qr-campaigns")
@require_admin
def qr_campaigns():
    campaigns = QRCampaign.query.order_by(QRCampaign.created_at.desc()).all()
    return jsonify([c.to_dict() for c in campaigns])


@analytics_bp.route("/members")
@require_admin
def member_analytics():
    from db.models import Member
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)
    return jsonify({
        "total": Member.query.count(),
        "new_this_week": Member.query.filter(Member.created_at >= week_ago).count(),
        "new_this_month": Member.query.filter(Member.created_at >= month_ago).count(),
        "by_tier": {
            "gold":   Member.query.filter_by(tier="gold").count(),
            "silver": Member.query.filter_by(tier="silver").count(),
            "bronze": Member.query.filter_by(tier="bronze").count(),
        }
    })
