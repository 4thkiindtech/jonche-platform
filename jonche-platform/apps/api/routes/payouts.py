"""
Payout Management Routes - Phase 4 Lite
Handles manual payout approval, payment recording, and earnings summaries.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from db import db
from db.models import (
    Admin, AffiliateAccount, ReferralPartnerAccount, ExecutiveAccount,
    RetailPartnerAccount, AffiliateEarning, PartnerReferral,
    PayoutSchedule, PayoutBatch, CommissionPayout, PaymentMethod, PayoutLog
)
import json

payouts_bp = Blueprint("payouts", __name__, url_prefix="/api")


# ── Partner Earning Summaries ──────────────────────────────────────────────────

@payouts_bp.route("/partners/<partner_type>/<int:partner_id>/earnings", methods=["GET"])
def get_partner_earnings(partner_type, partner_id):
    """
    Get partner's earnings summary:
    - pending: unpaid earnings not yet in a batch
    - approved: approved payouts awaiting payment
    - projected: pending + calculated future commissions
    - next_payout_date: when they'll next receive payment
    """
    try:
        partner = None
        pending_amount = 0
        approved_amount = 0
        
        if partner_type == "affiliate":
            partner = AffiliateAccount.query.get(partner_id)
            pending_earnings = AffiliateEarning.query.filter_by(
                affiliate_id=partner_id, status="pending"
            ).all()
            pending_amount = sum(e.commission_cents for e in pending_earnings)
            
        elif partner_type == "referral_partner":
            partner = ReferralPartnerAccount.query.get(partner_id)
            pending_earnings = PartnerReferral.query.filter_by(
                referral_partner_id=partner_id, status="pending"
            ).all()
            pending_amount = sum(e.commission_cents for e in pending_earnings)
            
        elif partner_type == "executive":
            partner = ExecutiveAccount.query.get(partner_id)
            pending_earnings = PartnerReferral.query.filter_by(
                executive_id=partner_id, status="pending"
            ).all()
            pending_amount = sum(e.commission_cents for e in pending_earnings)
        
        if not partner:
            return jsonify({"error": "Partner not found"}), 404
        
        # Approved payouts (in approved batches, not yet paid)
        approved_payouts = CommissionPayout.query.filter_by(
            partner_type=partner_type, partner_id=partner_id, status="approved"
        ).all()
        approved_amount = sum(p.net_amount_cents for p in approved_payouts)
        
        # Projected earnings = pending + already in system
        projected_amount = pending_amount + approved_amount + (partner.pending_commission_cents or 0)
        
        # Get payout schedule
        schedule = PayoutSchedule.query.filter_by(partner_type=partner_type).first()
        next_payout_date = calculate_next_payout_date(schedule) if schedule else None
        
        # Check minimum threshold
        schedule = PayoutSchedule.query.filter_by(partner_type=partner_type).first()
        meets_minimum = False
        if schedule and pending_amount >= schedule.minimum_payout_cents:
            meets_minimum = True
        
        return jsonify({
            "partner_id": partner_id,
            "partner_type": partner_type,
            "partner_email": partner.email,
            "pending_cents": pending_amount,
            "pending_dollars": pending_amount / 100,
            "approved_cents": approved_amount,
            "approved_dollars": approved_amount / 100,
            "projected_cents": projected_amount,
            "projected_dollars": projected_amount / 100,
            "meets_minimum": meets_minimum,
            "minimum_threshold_cents": schedule.minimum_payout_cents if schedule else 0,
            "minimum_threshold_dollars": (schedule.minimum_payout_cents / 100) if schedule else 0,
            "next_payout_date": next_payout_date.isoformat() if next_payout_date else None,
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Admin: List Pending Payouts ────────────────────────────────────────────────

@payouts_bp.route("/admin/payouts/pending", methods=["GET"])
def get_pending_payouts():
    """
    List all pending payouts for admin approval.
    Optional filters: partner_type, batch_id, date_from, date_to
    """
    try:
        admin_id = request.headers.get("X-Admin-ID")
        if not admin_id or not Admin.query.get(admin_id):
            return jsonify({"error": "Unauthorized"}), 401
        
        partner_type = request.args.get("partner_type")
        batch_id = request.args.get("batch_id")
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        
        query = CommissionPayout.query.filter_by(status="pending")
        
        if partner_type:
            query = query.filter_by(partner_type=partner_type)
        if batch_id:
            query = query.filter_by(batch_id=batch_id)
        
        if date_from:
            df = datetime.fromisoformat(date_from)
            query = query.filter(CommissionPayout.created_at >= df)
        if date_to:
            dt = datetime.fromisoformat(date_to)
            query = query.filter(CommissionPayout.created_at <= dt)
        
        payouts = query.order_by(CommissionPayout.created_at.desc()).all()
        
        return jsonify({
            "total": len(payouts),
            "payouts": [p.to_dict() for p in payouts]
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Admin: Approve Payout Batch ────────────────────────────────────────────────

@payouts_bp.route("/admin/payouts/batch/<int:batch_id>/approve", methods=["POST"])
def approve_payout_batch(batch_id):
    """
    Approve a batch of payouts for processing.
    Admin reviews and approves, then moves to payment phase.
    """
    try:
        admin_id = request.headers.get("X-Admin-ID")
        admin = Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Unauthorized"}), 401
        
        batch = PayoutBatch.query.get(batch_id)
        if not batch:
            return jsonify({"error": "Batch not found"}), 404
        
        if batch.status != "pending":
            return jsonify({"error": f"Batch cannot be approved from {batch.status} status"}), 400
        
        # Approve all payouts in batch
        payouts = CommissionPayout.query.filter_by(batch_id=batch_id).all()
        for payout in payouts:
            payout.status = "approved"
        
        # Update batch
        batch.status = "approved"
        batch.approved_by_admin_id = admin.id
        batch.approved_at = datetime.utcnow()
        
        # Log action
        log = PayoutLog(
            batch_id=batch_id,
            action="batch_approved",
            actor_type="admin",
            actor_id=admin.id,
            details=json.dumps({
                "payout_count": len(payouts),
                "total_amount_cents": batch.total_amount_cents
            })
        )
        
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "batch": batch.to_dict(),
            "payouts_approved": len(payouts)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ── Admin: Reject Batch ────────────────────────────────────────────────────────

@payouts_bp.route("/admin/payouts/batch/<int:batch_id>/reject", methods=["POST"])
def reject_payout_batch(batch_id):
    """Reject a batch (moves payouts back to pending)."""
    try:
        admin_id = request.headers.get("X-Admin-ID")
        admin = Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.get_json()
        reason = data.get("reason", "No reason provided")
        
        batch = PayoutBatch.query.get(batch_id)
        if not batch:
            return jsonify({"error": "Batch not found"}), 404
        
        if batch.status != "pending":
            return jsonify({"error": f"Batch cannot be rejected from {batch.status} status"}), 400
        
        batch.status = "rejected"
        batch.notes = reason
        
        # Log action
        log = PayoutLog(
            batch_id=batch_id,
            action="batch_rejected",
            actor_type="admin",
            actor_id=admin.id,
            details=json.dumps({"reason": reason})
        )
        
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "batch": batch.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ── Admin: Record Manual Payment ───────────────────────────────────────────────

@payouts_bp.route("/admin/payouts/<int:payout_id>/payment", methods=["POST"])
def record_payout_payment(payout_id):
    """
    Record manual payment for a payout (ACH, Zelle, Wire).
    Transitions payout from "approved" → "paid"
    """
    try:
        admin_id = request.headers.get("X-Admin-ID")
        admin = Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.get_json()
        payment_method = data.get("payment_method")  # ach/zelle/wire/check
        payment_reference = data.get("payment_reference")  # confirmation #, ref #, check #
        
        if not payment_method or not payment_reference:
            return jsonify({"error": "payment_method and payment_reference required"}), 400
        
        payout = CommissionPayout.query.get(payout_id)
        if not payout:
            return jsonify({"error": "Payout not found"}), 404
        
        if payout.status != "approved":
            return jsonify({"error": f"Payout cannot be paid from {payout.status} status"}), 400
        
        # Update payout
        payout.status = "paid"
        payout.payment_method = payment_method
        payout.payment_reference = payment_reference
        payout.paid_at = datetime.utcnow()
        
        # Log action
        log = PayoutLog(
            payout_id=payout_id,
            batch_id=payout.batch_id,
            action="payment_recorded",
            actor_type="admin",
            actor_id=admin.id,
            details=json.dumps({
                "payment_method": payment_method,
                "payment_reference": payment_reference,
                "amount_cents": payout.net_amount_cents
            })
        )
        
        db.session.add(log)
        
        # Mark related earnings/referrals as paid
        mark_source_items_paid(payout)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "payout": payout.to_dict(),
            "paid_at": payout.paid_at.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ── Admin: Create Payout Batch (Manual) ────────────────────────────────────────

@payouts_bp.route("/admin/payouts/batch/create", methods=["POST"])
def create_payout_batch():
    """
    Manually create a payout batch for a specific partner type.
    Groups all pending commissions that meet minimum threshold.
    """
    try:
        admin_id = request.headers.get("X-Admin-ID")
        admin = Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.get_json()
        partner_type = data.get("partner_type")  # affiliate, referral_partner, executive, retail_partner
        
        if not partner_type:
            return jsonify({"error": "partner_type required"}), 400
        
        schedule = PayoutSchedule.query.filter_by(partner_type=partner_type).first()
        if not schedule:
            return jsonify({"error": f"No payout schedule for {partner_type}"}), 400
        
        # Create batch
        batch = PayoutBatch(
            partner_type=partner_type,
            cycle_date=datetime.utcnow()
        )
        db.session.add(batch)
        db.session.flush()  # Get batch ID
        
        total_cents = 0
        payout_count = 0
        
        # Collect pending commissions for this partner type
        if partner_type == "affiliate":
            earnings = AffiliateEarning.query.filter_by(status="pending").all()
            for earning in earnings:
                if earning.commission_cents >= schedule.minimum_payout_cents:
                    payout = CommissionPayout(
                        batch_id=batch.id,
                        partner_type=partner_type,
                        partner_id=earning.affiliate_id,
                        partner_email=earning.affiliate.email,
                        source_ids=json.dumps([earning.id]),
                        gross_amount_cents=earning.commission_cents,
                        payment_fee_cents=0,
                        net_amount_cents=earning.commission_cents,
                        status="pending"
                    )
                    db.session.add(payout)
                    total_cents += earning.commission_cents
                    payout_count += 1
                    earning.status = "holdable"  # Mark as included in batch
        
        elif partner_type == "referral_partner":
            referrals = PartnerReferral.query.filter_by(status="invoiced").all()
            for referral in referrals:
                if referral.commission_cents >= schedule.minimum_payout_cents:
                    payout = CommissionPayout(
                        batch_id=batch.id,
                        partner_type=partner_type,
                        partner_id=referral.referral_partner_id,
                        partner_email=referral.referral_partner.email,
                        source_ids=json.dumps([referral.id]),
                        gross_amount_cents=referral.commission_cents,
                        payment_fee_cents=0,
                        net_amount_cents=referral.commission_cents,
                        status="pending"
                    )
                    db.session.add(payout)
                    total_cents += referral.commission_cents
                    payout_count += 1
                    referral.status = "pending"  # Move to pending payout
        
        elif partner_type == "executive":
            referrals = PartnerReferral.query.filter(
                PartnerReferral.executive_id.isnot(None),
                PartnerReferral.status == "invoiced"
            ).all()
            for referral in referrals:
                # Executives have no minimum
                payout = CommissionPayout(
                    batch_id=batch.id,
                    partner_type=partner_type,
                    partner_id=referral.executive_id,
                    partner_email=referral.executive.email,
                    source_ids=json.dumps([referral.id]),
                    gross_amount_cents=referral.commission_cents,
                    payment_fee_cents=0,
                    net_amount_cents=referral.commission_cents,
                    status="pending"
                )
                db.session.add(payout)
                total_cents += referral.commission_cents
                payout_count += 1
                referral.status = "pending"
        
        # Update batch
        batch.total_amount_cents = total_cents
        batch.payout_count = payout_count
        
        # Log action
        log = PayoutLog(
            batch_id=batch.id,
            action="batch_created",
            actor_type="admin",
            actor_id=admin.id,
            details=json.dumps({
                "partner_type": partner_type,
                "payout_count": payout_count,
                "total_amount_cents": total_cents
            })
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "batch": batch.to_dict(),
            "payouts_created": payout_count
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ── Admin: List Payout Batches ────────────────────────────────────────────────

@payouts_bp.route("/admin/payouts/batches", methods=["GET"])
def get_payout_batches():
    """List all payout batches with optional filtering."""
    try:
        admin_id = request.headers.get("X-Admin-ID")
        if not admin_id or not Admin.query.get(admin_id):
            return jsonify({"error": "Unauthorized"}), 401
        
        status = request.args.get("status")
        partner_type = request.args.get("partner_type")
        
        query = PayoutBatch.query
        if status:
            query = query.filter_by(status=status)
        if partner_type:
            query = query.filter_by(partner_type=partner_type)
        
        batches = query.order_by(PayoutBatch.created_at.desc()).all()
        
        return jsonify({
            "total": len(batches),
            "batches": [b.to_dict() for b in batches]
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Helper Functions ───────────────────────────────────────────────────────────

def calculate_next_payout_date(schedule):
    """Calculate next payout date based on schedule."""
    if not schedule:
        return None
    
    today = datetime.utcnow().date()
    
    if schedule.frequency == "monthly":
        if "last_business_day" in schedule.day_of_cycle:
            # Last business day of month
            next_month = today.replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1) - timedelta(days=1)
            # Back up to Monday if weekend
            while next_month.weekday() > 4:
                next_month -= timedelta(days=1)
            return next_month
    
    elif schedule.frequency == "biweekly":
        if "1st" in schedule.day_of_cycle:
            next_date = today.replace(day=1) if today.day > 1 else today
            if next_date < today:
                next_month = today.replace(day=1) + timedelta(days=32)
                next_date = next_month.replace(day=1)
            return next_date
        elif "15th" in schedule.day_of_cycle:
            next_date = today.replace(day=15) if today.day > 15 else today
            if next_date < today:
                next_month = today.replace(day=1) + timedelta(days=32)
                next_date = next_month.replace(day=15)
            return next_date
    
    elif schedule.frequency == "weekly":
        if "monday" in schedule.day_of_cycle.lower():
            days_ahead = 0 - today.weekday()  # Monday = 0
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
    
    return None


def mark_source_items_paid(payout):
    """Mark the source earnings or referrals as paid."""
    try:
        source_ids = json.loads(payout.source_ids) if payout.source_ids else []
        
        if payout.partner_type == "affiliate":
            for source_id in source_ids:
                earning = AffiliateEarning.query.get(source_id)
                if earning:
                    earning.status = "paid"
                    earning.paid_at = datetime.utcnow()
                    earning.payout_batch_id = payout.batch_id
        
        elif payout.partner_type in ["referral_partner", "executive"]:
            for source_id in source_ids:
                referral = PartnerReferral.query.get(source_id)
                if referral:
                    referral.status = "paid"
                    referral.paid_at = datetime.utcnow()
    
    except Exception as e:
        print(f"Error marking source items paid: {e}")
