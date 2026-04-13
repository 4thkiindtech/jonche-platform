"""
Phase 4 Lite Initialization Script
Initialize payout schedules and payment configurations.
Run this once after migrations are applied.
"""

from datetime import datetime
from db import db
from db.models import PayoutSchedule


def init_payout_schedules():
    """
    Initialize the three payout schedules:
    - Affiliates: Monthly ($100 minimum)
    - Referral Partners: Bi-weekly ($500 minimum)
    - Executives: Weekly (no minimum)
    """
    
    # Check if schedules already exist
    if PayoutSchedule.query.filter_by(partner_type="affiliate").first():
        print("Payout schedules already initialized. Skipping.")
        return
    
    # 1. Affiliate Schedule - Monthly on last business day
    affiliate_schedule = PayoutSchedule(
        partner_type="affiliate",
        frequency="monthly",
        day_of_cycle="last_business_day",
        minimum_payout_cents=10000,  # $100
        hold_period_days=0,
        enabled=True
    )
    db.session.add(affiliate_schedule)
    
    # 2. Referral Partner Schedule - Bi-weekly on 1st and 15th
    referral_schedule_1 = PayoutSchedule(
        partner_type="referral_partner",
        frequency="biweekly",
        day_of_cycle="1st",
        minimum_payout_cents=50000,  # $500
        hold_period_days=0,
        enabled=True
    )
    db.session.add(referral_schedule_1)
    
    referral_schedule_15 = PayoutSchedule(
        partner_type="referral_partner",
        frequency="biweekly",
        day_of_cycle="15th",
        minimum_payout_cents=50000,  # $500
        hold_period_days=0,
        enabled=True
    )
    db.session.add(referral_schedule_15)
    
    # 3. Executive Schedule - Weekly on Monday
    executive_schedule = PayoutSchedule(
        partner_type="executive",
        frequency="weekly",
        day_of_cycle="monday",
        minimum_payout_cents=0,  # No minimum
        hold_period_days=0,
        enabled=True
    )
    db.session.add(executive_schedule)
    
    db.session.commit()
    
    print("✓ Payout schedules initialized:")
    print("  - Affiliate: Monthly (last business day, $100 min)")
    print("  - Referral Partner: Bi-weekly (1st & 15th, $500 min)")
    print("  - Executive: Weekly (Monday, no minimum)")


if __name__ == "__main__":
    init_payout_schedules()
