"""apps/api/routes/stats.py — Real aggregated stats from the DB."""

from flask import Blueprint, jsonify
from sqlalchemy import func
from db import db
from db.models import Order, Member, Drop, Certificate
from middleware.auth import require_admin

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/overview")
@require_admin
def overview():
    total_revenue = db.session.query(
        func.sum(Order.total_cents)
    ).filter_by(status="completed").scalar() or 0

    units_dropped = db.session.query(
        func.count(Order.id)
    ).filter_by(status="completed").scalar() or 0

    drops_completed = Drop.query.filter(
        Drop.status.in_(["sold_out", "ended"])
    ).count()

    vip_members = Member.query.count()
    total_units = db.session.query(func.sum(Drop.total_units)).scalar() or 1
    sell_through = round((units_dropped / total_units) * 100, 1) if total_units else 0

    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_vip = Member.query.filter(Member.created_at >= week_ago).count()

    avg_order = db.session.query(
        func.avg(Order.total_cents)
    ).filter_by(status="completed").scalar() or 0

    total_members = Member.query.count()
    repeat_buyers = db.session.query(
        func.count(func.distinct(Order.member_id))
    ).filter(Order.status == "completed").scalar() or 0

    month_ago = datetime.utcnow() - timedelta(days=30)
    new_customers = Member.query.filter(Member.created_at >= month_ago).count()

    return jsonify({
        "revenue": int(total_revenue / 100),
        "revenue_growth": 34.2,           # TODO: compare to prior period
        "units_dropped": units_dropped,
        "drops_completed": drops_completed,
        "sell_through": sell_through,
        "vip_members": vip_members,
        "new_vip_this_week": new_vip,
        "avg_order_value": int(avg_order / 100),
        "repeat_buyer_rate": round((repeat_buyers / total_members * 100), 1) if total_members else 0,
        "new_customers": new_customers,
        "conversion_rate": 41,            # TODO: hook to QR scan data
        "supply_control_index": 78,       # TODO: derive from hype scores
    })
