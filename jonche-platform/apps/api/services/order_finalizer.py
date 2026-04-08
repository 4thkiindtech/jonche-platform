"""
apps/api/services/order_finalizer.py
Finalize orders when Stripe confirms payment (webhook-driven).
"""

from __future__ import annotations

from datetime import datetime

from db import db
from db.models import Order, CheckoutLock, Certificate, Member, Drop
from services.notifications import enqueue_email


def finalize_order(order: Order) -> dict:
    """
    Marks order completed, completes lock, updates member tier/spend,
    issues certificate, and enqueues emails. Returns dict with order+certificate.
    """
    if order.status == "completed":
        return {"order": order, "certificate": order.certificate}

    order.status = "completed"

    # Complete checkout lock if present
    if getattr(order, "checkout_lock_id", None):
        lock = CheckoutLock.query.get(order.checkout_lock_id)
        if lock and lock.status == "active" and not lock.is_expired:
            lock.status = "completed"

    # Update member lifetime spend and tier
    if order.member_id:
        member = Member.query.get(order.member_id)
        if member:
            member.lifetime_spend += (order.total_cents / 100)
            member.recalculate_tier()

    # Issue certificate if missing
    cert = order.certificate
    if not cert and order.drop_id:
        drop = Drop.query.get(order.drop_id)
        existing_certs = Certificate.query.filter_by(drop_id=order.drop_id).count()
        size = order.items[0].size if order.items else "N/A"
        cert = Certificate(
            cert_number=f"JNC-{datetime.utcnow().year}-{existing_certs + 1:04d}",
            drop_id=order.drop_id,
            order_id=order.id,
            member_id=order.member_id,
            size=size,
            run_number=existing_certs + 1,
            total_run=(drop.total_units if drop else existing_certs + 1),
        )
        db.session.add(cert)

    db.session.commit()

    # Enqueue emails (best-effort)
    try:
        if order.member and order.member.email:
            enqueue_email(
                recipient_email=order.member.email,
                recipient_name=order.member.name,
                subject=f"JONCHE Order Confirmed — {order.order_number}",
                body_html=_order_confirm_html(order, cert),
                notif_type="order_confirm",
                related_id=order.id,
            )
        if cert and order.member and order.member.email:
            enqueue_email(
                recipient_email=order.member.email,
                recipient_name=order.member.name,
                subject=f"JONCHE Authenticity Certificate — {cert.cert_number}",
                body_html=_cert_html(cert),
                notif_type="cert_issued",
                related_id=cert.id,
            )
    except Exception:
        pass

    return {"order": order, "certificate": cert}


def mark_refunded(order: Order) -> Order:
    if order.status != "refunded":
        order.status = "refunded"
        db.session.commit()
    return order


def _order_confirm_html(order: Order, cert: Certificate | None) -> str:
    verify_url = f"/verify/{cert.verify_token}" if cert else ""
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:640px">
      <h2>Order Confirmed</h2>
      <p>Order: <b>{order.order_number}</b></p>
      <p>Total: <b>${order.total_cents/100:.2f}</b></p>
      <p>Status: <b>{order.status}</b></p>
      {f'<p>Certificate verify: <a href=\"{verify_url}\">{verify_url}</a></p>' if verify_url else ''}
    </div>
    """


def _cert_html(cert: Certificate) -> str:
    verify_url = f"/verify/{cert.verify_token}"
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:640px">
      <h2>Authenticity Certificate Issued</h2>
      <p>Certificate: <b>{cert.cert_number}</b></p>
      <p>Verify: <a href="{verify_url}">{verify_url}</a></p>
      <p>Size: <b>{cert.size}</b> • Run <b>{cert.run_number}/{cert.total_run}</b></p>
    </div>
    """

