"""
Payout Calculator Service - Phase 4 Lite
Automated commission calculation for all partner types.
"""

from datetime import datetime, timedelta
from db import db
from db.models import (
    AffiliateAccount, AffiliateEarning,
    ReferralPartnerAccount, PartnerReferral,
    ExecutiveAccount, PayoutSchedule, CommissionPayout, PayoutLog
)
import json


class PayoutCalculator:
    """Calculates commissions and pending payouts for all partner types."""
    
    @staticmethod
    def calculate_affiliate_pending(affiliate_id):
        """
        Calculate pending commission for an affiliate.
        Includes all completed orders via referral that haven't been paid.
        """
        affiliate = AffiliateAccount.query.get(affiliate_id)
        if not affiliate:
            return 0
        
        pending_earnings = AffiliateEarning.query.filter_by(
            affiliate_id=affiliate_id,
            status="pending"
        ).all()
        
        return sum(e.commission_cents for e in pending_earnings)
    
    @staticmethod
    def calculate_referral_pending(referral_partner_id):
        """
        Calculate pending commission for a referral partner.
        Includes all invoiced deals awaiting payment.
        """
        partner = ReferralPartnerAccount.query.get(referral_partner_id)
        if not partner:
            return 0
        
        pending_referrals = PartnerReferral.query.filter(
            PartnerReferral.referral_partner_id == referral_partner_id,
            PartnerReferral.status.in_(["invoiced", "pending"])
        ).all()
        
        return sum(r.commission_cents for r in pending_referrals)
    
    @staticmethod
    def calculate_executive_pending(executive_id):
        """
        Calculate pending commission for an executive.
        Includes all invoiced deals assigned to them.
        """
        executive = ExecutiveAccount.query.get(executive_id)
        if not executive:
            return 0
        
        pending_deals = PartnerReferral.query.filter(
            PartnerReferral.executive_id == executive_id,
            PartnerReferral.status.in_(["invoiced", "pending"])
        ).all()
        
        return sum(r.commission_cents for r in pending_deals)
    
    @staticmethod
    def calculate_all_projected_earnings():
        """
        Calculate and update projected earnings for all partners.
        Projected = pending + approved payouts
        """
        affiliates = AffiliateAccount.query.all()
        for affiliate in affiliates:
            pending = PayoutCalculator.calculate_affiliate_pending(affiliate.id)
            
            # Also check for approved payouts waiting to be paid
            approved_payouts = CommissionPayout.query.filter_by(
                partner_type="affiliate",
                partner_id=affiliate.id,
                status="approved"
            ).all()
            approved = sum(p.net_amount_cents for p in approved_payouts)
            
            # Update partner's projected commission
            affiliate.pending_commission_cents = pending + approved
            db.session.add(affiliate)
        
        referral_partners = ReferralPartnerAccount.query.all()
        for partner in referral_partners:
            pending = PayoutCalculator.calculate_referral_pending(partner.id)
            approved_payouts = CommissionPayout.query.filter_by(
                partner_type="referral_partner",
                partner_id=partner.id,
                status="approved"
            ).all()
            approved = sum(p.net_amount_cents for p in approved_payouts)
            
            partner.pending_commission_cents = pending + approved
            db.session.add(partner)
        
        executives = ExecutiveAccount.query.all()
        for executive in executives:
            pending = PayoutCalculator.calculate_executive_pending(executive.id)
            approved_payouts = CommissionPayout.query.filter_by(
                partner_type="executive",
                partner_id=executive.id,
                status="approved"
            ).all()
            approved = sum(p.net_amount_cents for p in approved_payouts)
            
            executive.pending_commission_cents = pending + approved
            db.session.add(executive)
        
        db.session.commit()


class BatchProcessor:
    """Creates and processes payout batches."""
    
    @staticmethod
    def create_affiliate_batch():
        """Create a batch for all pending affiliate earnings."""
        schedule = PayoutSchedule.query.filter_by(partner_type="affiliate").first()
        if not schedule or not schedule.enabled:
            return None
        
        # Find all affiliates with pending earnings >= minimum
        affiliates_to_pay = set()
        pending_earnings = AffiliateEarning.query.filter_by(
            status="pending"
        ).all()
        
        for earning in pending_earnings:
            if earning.commission_cents >= schedule.minimum_payout_cents:
                affiliates_to_pay.add(earning.affiliate_id)
        
        if not affiliates_to_pay:
            return None
        
        # Create batch and payouts
        batch = BatchProcessor._create_batch_for_partners(
            partner_type="affiliate",
            partner_ids=list(affiliates_to_pay),
            schedule=schedule,
            earnings_query=AffiliateEarning
        )
        
        return batch
    
    @staticmethod
    def create_referral_batch():
        """Create a batch for all pending referral partner earnings."""
        schedule = PayoutSchedule.query.filter_by(partner_type="referral_partner").first()
        if not schedule or not schedule.enabled:
            return None
        
        # Find all referral partners with invoiced deals >= minimum
        partners_to_pay = set()
        pending_referrals = PartnerReferral.query.filter(
            PartnerReferral.status.in_(["invoiced", "pending"])
        ).all()
        
        for referral in pending_referrals:
            if referral.commission_cents >= schedule.minimum_payout_cents and referral.referral_partner_id:
                partners_to_pay.add(referral.referral_partner_id)
        
        if not partners_to_pay:
            return None
        
        batch = BatchProcessor._create_batch_for_partners(
            partner_type="referral_partner",
            partner_ids=list(partners_to_pay),
            schedule=schedule,
            referrals=pending_referrals
        )
        
        return batch
    
    @staticmethod
    def create_executive_batch():
        """Create a batch for all pending executive earnings (no minimum)."""
        schedule = PayoutSchedule.query.filter_by(partner_type="executive").first()
        if not schedule or not schedule.enabled:
            return None
        
        # Find all executives with pending deals
        executives_to_pay = set()
        pending_referrals = PartnerReferral.query.filter(
            PartnerReferral.status.in_(["invoiced", "pending"]),
            PartnerReferral.executive_id.isnot(None)
        ).all()
        
        for referral in pending_referrals:
            if referral.commission_cents > 0:
                executives_to_pay.add(referral.executive_id)
        
        if not executives_to_pay:
            return None
        
        batch = BatchProcessor._create_batch_for_partners(
            partner_type="executive",
            partner_ids=list(executives_to_pay),
            schedule=schedule,
            referrals=pending_referrals,
            no_minimum=True
        )
        
        return batch
    
    @staticmethod
    def _create_batch_for_partners(partner_type, partner_ids, schedule, 
                                   earnings_query=None, referrals=None, no_minimum=False):
        """Generic batch creation for any partner type."""
        from db.models import PayoutBatch, CommissionPayout
        
        batch = PayoutBatch(
            partner_type=partner_type,
            cycle_date=datetime.utcnow()
        )
        db.session.add(batch)
        db.session.flush()  # Get batch ID
        
        total_cents = 0
        payout_count = 0
        
        for partner_id in partner_ids:
            if partner_type == "affiliate":
                earnings = AffiliateEarning.query.filter_by(
                    affiliate_id=partner_id,
                    status="pending"
                ).all()
                
                partner = AffiliateAccount.query.get(partner_id)
                if not partner:
                    continue
                
                amount_cents = sum(e.commission_cents for e in earnings)
                if amount_cents < schedule.minimum_payout_cents and not no_minimum:
                    continue
                
                source_ids = [e.id for e in earnings]
                payout = CommissionPayout(
                    batch_id=batch.id,
                    partner_type=partner_type,
                    partner_id=partner_id,
                    partner_email=partner.email,
                    source_ids=json.dumps(source_ids),
                    gross_amount_cents=amount_cents,
                    payment_fee_cents=0,
                    net_amount_cents=amount_cents,
                    status="pending"
                )
                db.session.add(payout)
                total_cents += amount_cents
                payout_count += 1
                
                # Mark earnings as in-batch
                for earning in earnings:
                    earning.status = "holdable"
            
            elif partner_type in ["referral_partner", "executive"]:
                if referrals is None:
                    continue
                
                partner_referrals = [r for r in referrals if 
                    (partner_type == "referral_partner" and r.referral_partner_id == partner_id) or
                    (partner_type == "executive" and r.executive_id == partner_id)
                ]
                
                if not partner_referrals:
                    continue
                
                amount_cents = sum(r.commission_cents for r in partner_referrals)
                if amount_cents < schedule.minimum_payout_cents and not no_minimum:
                    continue
                
                if partner_type == "referral_partner":
                    partner = ReferralPartnerAccount.query.get(partner_id)
                else:
                    partner = ExecutiveAccount.query.get(partner_id)
                
                if not partner:
                    continue
                
                source_ids = [r.id for r in partner_referrals]
                payout = CommissionPayout(
                    batch_id=batch.id,
                    partner_type=partner_type,
                    partner_id=partner_id,
                    partner_email=partner.email,
                    source_ids=json.dumps(source_ids),
                    gross_amount_cents=amount_cents,
                    payment_fee_cents=0,
                    net_amount_cents=amount_cents,
                    status="pending"
                )
                db.session.add(payout)
                total_cents += amount_cents
                payout_count += 1
                
                # Mark referrals as pending payout
                for referral in partner_referrals:
                    referral.status = "pending"
        
        if payout_count == 0:
            db.session.delete(batch)
            db.session.commit()
            return None
        
        batch.total_amount_cents = total_cents
        batch.payout_count = payout_count
        
        # Log batch creation
        log = PayoutLog(
            batch_id=batch.id,
            action="batch_created",
            actor_type="system",
            details=json.dumps({
                "partner_type": partner_type,
                "payout_count": payout_count,
                "total_amount_cents": total_cents
            })
        )
        db.session.add(log)
        db.session.commit()
        
        return batch


class PayoutValidator:
    """Validates payout configurations and thresholds."""
    
    @staticmethod
    def validate_payout_config():
        """Ensure all required payout schedules are configured."""
        required_types = ["affiliate", "referral_partner", "executive"]
        missing = []
        
        for partner_type in required_types:
            if not PayoutSchedule.query.filter_by(partner_type=partner_type).first():
                missing.append(partner_type)
        
        return {
            "valid": len(missing) == 0,
            "missing_schedules": missing
        }
    
    @staticmethod
    def check_partner_meets_minimum(partner_type, partner_id):
        """Check if a partner's pending earnings meet minimum threshold."""
        schedule = PayoutSchedule.query.filter_by(partner_type=partner_type).first()
        if not schedule:
            return False
        
        pending = 0
        if partner_type == "affiliate":
            pending = PayoutCalculator.calculate_affiliate_pending(partner_id)
        elif partner_type == "referral_partner":
            pending = PayoutCalculator.calculate_referral_pending(partner_id)
        elif partner_type == "executive":
            pending = PayoutCalculator.calculate_executive_pending(partner_id)
        
        return pending >= schedule.minimum_payout_cents
