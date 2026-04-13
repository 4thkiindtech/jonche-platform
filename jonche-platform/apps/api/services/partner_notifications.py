"""
apps/api/services/partner_notifications.py
Email notifications for partner ecosystem events.
Uses the existing notification queue system.
"""

import os
from datetime import datetime
from services.notifications import enqueue_email


class PartnerEmailRenderer:
    """Template renderer for partner notification emails."""
    
    @staticmethod
    def _header() -> str:
        """Common email header with branding."""
        return """
        <table width="100%" style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            <tr style="background: linear-gradient(135deg, #000 0%, #1a1a1a 100%); padding: 30px;">
                <td style="color: white; font-size: 28px; font-weight: bold;">🖤 JONCHE</td>
            </tr>
        </table>
        """
    
    @staticmethod
    def _footer() -> str:
        """Common email footer."""
        return """
        <table width="100%" style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px;">
            <tr>
                <td style="color: #999; font-size: 12px; text-align: center;">
                    <p>© 2024 Jonche Platform. All rights reserved.</p>
                    <p><a href="https://jonche.com" style="color: #ffd700; text-decoration: none;">Visit Dashboard</a> | <a href="https://jonche.com/help" style="color: #ffd700; text-decoration: none;">Help Center</a></p>
                </td>
            </tr>
        </table>
        """
    
    @staticmethod
    def application_approved(
        name: str,
        program_type: str,
        temp_password: str = None,
        login_url: str = "https://jonche.com/login"
    ) -> tuple[str, str]:
        """Application approved notification."""
        program_display = program_type.replace("_", " ").title()
        
        body_html = f"""
        {PartnerEmailRenderer._header()}
        
        <table width="100%" style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            <tr style="background: white; padding: 30px;">
                <td>
                    <h2 style="color: #000; margin: 0 0 20px 0;">✅ Welcome to {program_display}!</h2>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        Hi <strong>{name}</strong>,
                    </p>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        Great news! Your application to join the Jonche <strong>{program_display}</strong> program has been <strong>approved</strong> and is ready to activate. 🎉
                    </p>
                    
                    <div style="background: #f9f9f9; padding: 20px; border-left: 4px solid #ffd700; margin: 20px 0;">
                        <p style="color: #333; margin: 0 0 10px 0;"><strong>Your Account is Ready</strong></p>
                        <ul style="color: #666; margin: 0; padding-left: 20px;">
                            <li>Program: {program_display}</li>
                            <li>Status: <span style="color: #2e7d32; font-weight: bold;">ACTIVE</span></li>
                            <li>Joined: {datetime.utcnow().strftime('%B %d, %Y')}</li>
                        </ul>
                    </div>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 20px 0;">
                        <a href="{login_url}" style="display: inline-block; background: #000; color: white; padding: 12px 30px; border-radius: 4px; text-decoration: none; font-weight: bold;">
                            Access Your Dashboard →
                        </a>
                    </p>
                    
                    <p style="color: #666; font-size: 14px; line-height: 1.6; margin: 20px 0;">
                        Questions? Check out our <a href="https://jonche.com/partner-docs" style="color: #ffd700; text-decoration: none;">Partner Documentation</a> or contact us at support@jonche.com
                    </p>
                </td>
            </tr>
        </table>
        
        {PartnerEmailRenderer._footer()}
        """
        
        return "✅ Your Jonche Partner Application is Approved!", body_html
    
    @staticmethod
    def referral_submitted(
        partner_name: str,
        deal_title: str,
        estimated_value: int,
        commission_pct: float,
        dashboard_url: str = "https://jonche.com/dashboards/referral"
    ) -> tuple[str, str]:
        """Referral/deal submitted notification."""
        value_display = f"${estimated_value:,.0f}" if estimated_value else "TBD"
        
        body_html = f"""
        {PartnerEmailRenderer._header()}
        
        <table width="100%" style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            <tr style="background: white; padding: 30px;">
                <td>
                    <h2 style="color: #000; margin: 0 0 20px 0;">📋 Deal Submitted Successfully</h2>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        Hi <strong>{partner_name}</strong>,
                    </p>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        Your deal has been submitted and is now under review. We'll assess the opportunity and get back to you within 2-3 business days.
                    </p>
                    
                    <div style="background: #f0f9ff; padding: 20px; border-left: 4px solid #ffd700; margin: 20px 0;">
                        <p style="color: #333; margin: 0 0 15px 0;"><strong>Deal Summary</strong></p>
                        <table style="width: 100%; color: #666; font-size: 14px;">
                            <tr>
                                <td style="padding: 8px 0;"><strong>Title:</strong></td>
                                <td style="text-align: right;">{deal_title}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0;"><strong>Estimated Value:</strong></td>
                                <td style="text-align: right; font-weight: bold; color: #2e7d32;">{value_display}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0;"><strong>Your Commission:</strong></td>
                                <td style="text-align: right; font-weight: bold;">{commission_pct}%</td>
                            </tr>
                            <tr style="background: #fff; border-top: 1px solid #ddd;">
                                <td style="padding: 8px 0;"><strong>Projected Payout:</strong></td>
                                <td style="text-align: right; font-weight: bold; color: #000; font-size: 16px;">${(estimated_value * commission_pct / 100) if estimated_value else 'TBD'}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 20px 0;">
                        <a href="{dashboard_url}" style="display: inline-block; background: #000; color: white; padding: 12px 30px; border-radius: 4px; text-decoration: none; font-weight: bold;">
                            View Deal Pipeline →
                        </a>
                    </p>
                </td>
            </tr>
        </table>
        
        {PartnerEmailRenderer._footer()}
        """
        
        return "📋 Your Deal has been Submitted", body_html
    
    @staticmethod
    def deal_funded(
        partner_name: str,
        deal_title: str,
        actual_value: int,
        commission_cents: int,
        dashboard_url: str = "https://jonche.com/dashboards/referral"
    ) -> tuple[str, str]:
        """Deal funded notification."""
        value_display = f"${actual_value:,.2f}"
        commission_display = f"${commission_cents / 100:,.2f}"
        
        body_html = f"""
        {PartnerEmailRenderer._header()}
        
        <table width="100%" style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            <tr style="background: white; padding: 30px;">
                <td>
                    <h2 style="color: #2e7d32; margin: 0 0 20px 0;">🎉 Deal Funded!</h2>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        Hi <strong>{partner_name}</strong>,
                    </p>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        Excellent news! Your deal <strong>"{deal_title}"</strong> has been approved and funded. Your commission has been calculated and will be processed for payment.
                    </p>
                    
                    <div style="background: #e8f5e9; padding: 20px; border-left: 4px solid #2e7d32; margin: 20px 0; border-radius: 4px;">
                        <p style="color: #333; margin: 0 0 15px 0;"><strong>Commission Earned</strong></p>
                        <table style="width: 100%; color: #666; font-size: 14px;">
                            <tr>
                                <td style="padding: 8px 0;"><strong>Deal Value:</strong></td>
                                <td style="text-align: right;">{value_display}</td>
                            </tr>
                            <tr style="background: white; border-top: 1px solid #ddd; border-bottom: 1px solid #ddd;">
                                <td style="padding: 12px 0;"><strong style="font-size: 16px;">Your Commission:</strong></td>
                                <td style="text-align: right; font-weight: bold; color: #2e7d32; font-size: 18px;">{commission_display}</td>
                            </tr>
                        </table>
                        <p style="color: #666; font-size: 12px; margin: 10px 0 0 0;">Commission marked for payout. Standard processing takes 3-5 business days.</p>
                    </div>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 20px 0;">
                        <a href="{dashboard_url}" style="display: inline-block; background: #2e7d32; color: white; padding: 12px 30px; border-radius: 4px; text-decoration: none; font-weight: bold;">
                            View Commission Details →
                        </a>
                    </p>
                </td>
            </tr>
        </table>
        
        {PartnerEmailRenderer._footer()}
        """
        
        return "🎉 Your Deal has been Funded!", body_html
    
    @staticmethod
    def commission_approved(
        partner_name: str,
        commission_cents: int,
        reason: str = None,
        dashboard_url: str = "https://jonche.com/dashboards/earnings"
    ) -> tuple[str, str]:
        """Commission approved notification."""
        commission_display = f"${commission_cents / 100:,.2f}"
        reason_html = f"<p style='color: #666; font-size: 14px; margin: 15px 0;'><strong>Reason:</strong> {reason}</p>" if reason else ""
        
        body_html = f"""
        {PartnerEmailRenderer._header()}
        
        <table width="100%" style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            <tr style="background: white; padding: 30px;">
                <td>
                    <h2 style="color: #2e7d32; margin: 0 0 20px 0;">✅ Commission Approved</h2>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        Hi <strong>{partner_name}</strong>,
                    </p>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        Your commission has been reviewed and approved! The amount below is now scheduled for payout.
                    </p>
                    
                    <div style="background: #e8f5e9; padding: 25px; border-left: 4px solid #2e7d32; margin: 20px 0; border-radius: 4px; text-align: center;">
                        <p style="color: #666; font-size: 12px; margin: 0 0 10px 0; text-transform: uppercase; letter-spacing: 1px;">Approved Amount</p>
                        <p style="color: #2e7d32; font-size: 36px; font-weight: bold; margin: 0;">{commission_display}</p>
                    </div>
                    
                    {reason_html}
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 20px 0;">
                        <a href="{dashboard_url}" style="display: inline-block; background: #000; color: white; padding: 12px 30px; border-radius: 4px; text-decoration: none; font-weight: bold;">
                            View Earnings →
                        </a>
                    </p>
                    
                    <p style="color: #666; font-size: 14px; line-height: 1.6; margin: 20px 0;">
                        Your payout will be processed within 3-5 business days. You'll receive another email confirmation once sent.
                    </p>
                </td>
            </tr>
        </table>
        
        {PartnerEmailRenderer._footer()}
        """
        
        return "✅ Commission Approved for Payout", body_html
    
    @staticmethod
    def payout_processed(
        partner_name: str,
        payout_cents: int,
        payout_method: str = "ACH",
        transaction_id: str = None,
        dashboard_url: str = "https://jonche.com/dashboards/payouts"
    ) -> tuple[str, str]:
        """Payout processed notification."""
        payout_display = f"${payout_cents / 100:,.2f}"
        transaction_html = f"<p style='color: #666; font-size: 14px; margin: 8px 0;'><strong>Transaction ID:</strong> {transaction_id}</p>" if transaction_id else ""
        
        body_html = f"""
        {PartnerEmailRenderer._header()}
        
        <table width="100%" style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            <tr style="background: white; padding: 30px;">
                <td>
                    <h2 style="color: #2e7d32; margin: 0 0 20px 0;">💰 Payout Processed!</h2>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        Hi <strong>{partner_name}</strong>,
                    </p>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        Your payout has been successfully processed and transferred to your account!
                    </p>
                    
                    <div style="background: #e8f5e9; padding: 25px; border-left: 4px solid #2e7d32; margin: 20px 0; border-radius: 4px;">
                        <p style="color: #666; font-size: 12px; margin: 0 0 10px 0; text-transform: uppercase; letter-spacing: 1px;">Payout Details</p>
                        <table style="width: 100%; color: #333; font-size: 14px;">
                            <tr>
                                <td style="padding: 8px 0;"><strong>Amount:</strong></td>
                                <td style="text-align: right; font-weight: bold; color: #2e7d32; font-size: 18px;">{payout_display}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0;"><strong>Method:</strong></td>
                                <td style="text-align: right;">{payout_method}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0;"><strong>Processed:</strong></td>
                                <td style="text-align: right;">{datetime.utcnow().strftime('%B %d, %Y')}</td>
                            </tr>
                        </table>
                        {transaction_html}
                    </div>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 20px 0;">
                        <a href="{dashboard_url}" style="display: inline-block; background: #000; color: white; padding: 12px 30px; border-radius: 4px; text-decoration: none; font-weight: bold;">
                            View Payout History →
                        </a>
                    </p>
                    
                    <p style="color: #666; font-size: 14px; line-height: 1.6; margin: 20px 0;">
                        The transfer should appear in your account within 1-2 business days depending on your bank. Thank you for your partnership!
                    </p>
                </td>
            </tr>
        </table>
        
        {PartnerEmailRenderer._footer()}
        """
        
        return "💰 Your Payout has been Processed", body_html
    
    @staticmethod
    def announcement(
        partner_name: str,
        announcement_title: str,
        announcement_content: str,
        priority: str = "normal",
        dashboard_url: str = "https://jonche.com/dashboards/announcements"
    ) -> tuple[str, str]:
        """Announcement notification."""
        priority_color = {
            "urgent": "#f44336",
            "high": "#ff9800",
            "normal": "#2196f3",
        }.get(priority, "#2196f3")
        
        priority_badge = f"<span style='background: {priority_color}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; text-transform: uppercase;'>{priority}</span>"
        
        body_html = f"""
        {PartnerEmailRenderer._header()}
        
        <table width="100%" style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            <tr style="background: white; padding: 30px;">
                <td>
                    <div style="margin-bottom: 20px;">
                        <h2 style="color: #000; margin: 0 0 15px 0; display: inline-block;">{announcement_title}</h2>
                        <div style="display: inline-block; margin-left: 10px;">
                            {priority_badge}
                        </div>
                    </div>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        Hi <strong>{partner_name}</strong>,
                    </p>
                    
                    <div style="background: #f9f9f9; padding: 20px; border-left: 4px solid {priority_color}; margin: 20px 0; border-radius: 4px; font-size: 15px; line-height: 1.8; color: #333;">
                        {announcement_content.replace(chr(10), '<br/>')}
                    </div>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 20px 0;">
                        <a href="{dashboard_url}" style="display: inline-block; background: #000; color: white; padding: 12px 30px; border-radius: 4px; text-decoration: none; font-weight: bold;">
                            View in Dashboard →
                        </a>
                    </p>
                </td>
            </tr>
        </table>
        
        {PartnerEmailRenderer._footer()}
        """
        
        return f"📢 {announcement_title}", body_html


class PartnerNotifications:
    """Send partner notifications using the existing queue system."""
    
    @staticmethod
    def notify_application_approved(
        email: str,
        name: str,
        program_type: str,
        notif_type: str = "partner_app_approved"
    ) -> None:
        """Send notification when partner application is approved."""
        subject, body_html = PartnerEmailRenderer.application_approved(name, program_type)
        enqueue_email(
            recipient_email=email,
            recipient_name=name,
            subject=subject,
            body_html=body_html,
            notif_type=notif_type,
        )
    
    @staticmethod
    def notify_referral_submitted(
        email: str,
        partner_name: str,
        deal_title: str,
        estimated_value: int,
        commission_pct: float,
        notif_type: str = "partner_referral_submitted"
    ) -> None:
        """Send notification when referral/deal is submitted."""
        subject, body_html = PartnerEmailRenderer.referral_submitted(
            partner_name, deal_title, estimated_value, commission_pct
        )
        enqueue_email(
            recipient_email=email,
            recipient_name=partner_name,
            subject=subject,
            body_html=body_html,
            notif_type=notif_type,
        )
    
    @staticmethod
    def notify_deal_funded(
        email: str,
        partner_name: str,
        deal_title: str,
        actual_value: int,
        commission_cents: int,
        notif_type: str = "partner_deal_funded"
    ) -> None:
        """Send notification when deal is funded."""
        subject, body_html = PartnerEmailRenderer.deal_funded(
            partner_name, deal_title, actual_value, commission_cents
        )
        enqueue_email(
            recipient_email=email,
            recipient_name=partner_name,
            subject=subject,
            body_html=body_html,
            notif_type=notif_type,
        )
    
    @staticmethod
    def notify_commission_approved(
        email: str,
        partner_name: str,
        commission_cents: int,
        reason: str = None,
        notif_type: str = "partner_commission_approved"
    ) -> None:
        """Send notification when commission is approved."""
        subject, body_html = PartnerEmailRenderer.commission_approved(
            partner_name, commission_cents, reason
        )
        enqueue_email(
            recipient_email=email,
            recipient_name=partner_name,
            subject=subject,
            body_html=body_html,
            notif_type=notif_type,
        )
    
    @staticmethod
    def notify_payout_processed(
        email: str,
        partner_name: str,
        payout_cents: int,
        payout_method: str = "ACH",
        transaction_id: str = None,
        notif_type: str = "partner_payout_processed"
    ) -> None:
        """Send notification when payout is processed."""
        subject, body_html = PartnerEmailRenderer.payout_processed(
            partner_name, payout_cents, payout_method, transaction_id
        )
        enqueue_email(
            recipient_email=email,
            recipient_name=partner_name,
            subject=subject,
            body_html=body_html,
            notif_type=notif_type,
        )
    
    @staticmethod
    def notify_announcement(
        email: str,
        partner_name: str,
        announcement_title: str,
        announcement_content: str,
        priority: str = "normal",
        notif_type: str = "partner_announcement"
    ) -> None:
        """Send announcement notification."""
        subject, body_html = PartnerEmailRenderer.announcement(
            partner_name, announcement_title, announcement_content, priority
        )
        enqueue_email(
            recipient_email=email,
            recipient_name=partner_name,
            subject=subject,
            body_html=body_html,
            notif_type=notif_type,
        )
