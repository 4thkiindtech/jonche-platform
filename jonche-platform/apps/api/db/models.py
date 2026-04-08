"""
apps/api/db/models.py
All database models for the Jonche Platform.

Tables:
  - admins          → platform admin accounts
  - retailers       → wholesale partner accounts
  - members         → VIP club members
  - drops           → limited release drops
  - waitlist_entries → raffle entries per drop per member
  - orders          → completed purchases
  - order_items     → line items per order
  - checkout_locks  → timed reservation holds (8 min)
  - certificates    → authenticity certificates
  - qr_campaigns    → QR tracking campaigns
  - qr_scans        → individual scan events
  - preorders       → pre-order campaign entries
  - retailer_allocations → per-drop allocations to retailers
  - notifications   → outbound email queue
"""

from datetime import datetime
import secrets
from db import db


# ── Admins ────────────────────────────────────────────────────────────────────

class Admin(db.Model):
    __tablename__ = "admins"

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name          = db.Column(db.String(100), nullable=False)
    is_superadmin = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_login    = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<Admin {self.email}>"

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "is_superadmin": self.is_superadmin,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


# ── Members (VIP Club) ────────────────────────────────────────────────────────

class Member(db.Model):
    __tablename__ = "members"

    id              = db.Column(db.Integer, primary_key=True)
    email           = db.Column(db.String(255), unique=True, nullable=False)
    password_hash   = db.Column(db.String(255), nullable=False)
    name            = db.Column(db.String(100), nullable=False)
    phone           = db.Column(db.String(30), nullable=True)
    tier            = db.Column(db.String(20), default="bronze")  # bronze/silver/gold
    lifetime_spend  = db.Column(db.Float, default=0.0)
    is_blacklisted  = db.Column(db.Boolean, default=False)
    blacklist_reason= db.Column(db.String(255), nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    last_login      = db.Column(db.DateTime, nullable=True)

    # Relationships
    orders          = db.relationship("Order", back_populates="member", lazy="dynamic")
    waitlist_entries= db.relationship("WaitlistEntry", back_populates="member", lazy="dynamic")
    certificates    = db.relationship("Certificate", back_populates="member", lazy="dynamic")
    preorders       = db.relationship("PreOrder", back_populates="member", lazy="dynamic")

    @property
    def initials(self):
        parts = self.name.split()
        return "".join(p[0].upper() for p in parts[:2])

    @property
    def computed_tier(self):
        if self.lifetime_spend >= 8000:
            return "gold"
        elif self.lifetime_spend >= 2500:
            return "silver"
        return "bronze"

    def recalculate_tier(self):
        self.tier = self.computed_tier

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "initials": self.initials,
            "phone": self.phone,
            "tier": self.tier,
            "lifetime_spend": self.lifetime_spend,
            "is_blacklisted": self.is_blacklisted,
            "created_at": self.created_at.isoformat(),
            "drops": self.orders.count(),
        }


# ── Retailers ─────────────────────────────────────────────────────────────────

class Retailer(db.Model):
    __tablename__ = "retailers"

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name          = db.Column(db.String(150), nullable=False)
    contact_name  = db.Column(db.String(100), nullable=True)
    phone         = db.Column(db.String(30), nullable=True)
    city          = db.Column(db.String(100), nullable=True)
    tier          = db.Column(db.String(20), default="basic")  # basic/select/premier
    status        = db.Column(db.String(20), default="review") # review/pending/active/suspended
    api_key       = db.Column(db.String(64), unique=True, nullable=False,
                              default=lambda: secrets.token_hex(32))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    allocations   = db.relationship("RetailerAllocation", back_populates="retailer", lazy="dynamic")

    @property
    def max_allocation(self):
        return {"premier": 50, "select": 20, "basic": 10}.get(self.tier, 10)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "contact_name": self.contact_name,
            "phone": self.phone,
            "city": self.city,
            "tier": self.tier,
            "status": self.status,
            "max_allocation": self.max_allocation,
            "created_at": self.created_at.isoformat(),
        }


# ── Drops ─────────────────────────────────────────────────────────────────────

class Drop(db.Model):
    __tablename__ = "drops"

    id              = db.Column(db.Integer, primary_key=True)
    slug            = db.Column(db.String(100), unique=True, nullable=False)
    name            = db.Column(db.String(150), nullable=False)
    colorway        = db.Column(db.String(100), nullable=False)
    sizes           = db.Column(db.String(50), nullable=False)   # e.g. "7-14"
    price           = db.Column(db.Integer, nullable=False)      # cents
    description     = db.Column(db.Text, nullable=True)
    status          = db.Column(db.String(20), default="draft")  # draft/upcoming/live/sold_out/ended
    total_units     = db.Column(db.Integer, nullable=False)
    units_reserved  = db.Column(db.Integer, default=0)          # wholesale
    drop_at         = db.Column(db.DateTime, nullable=True)      # scheduled publish time
    ends_at         = db.Column(db.DateTime, nullable=True)
    use_raffle      = db.Column(db.Boolean, default=False)
    max_per_member  = db.Column(db.Integer, default=1)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    orders          = db.relationship("Order", back_populates="drop", lazy="dynamic")
    waitlist_entries= db.relationship("WaitlistEntry", back_populates="drop", lazy="dynamic")
    checkout_locks  = db.relationship("CheckoutLock", back_populates="drop", lazy="dynamic")
    certificates    = db.relationship("Certificate", back_populates="drop", lazy="dynamic")
    allocations     = db.relationship("RetailerAllocation", back_populates="drop", lazy="dynamic")
    preorders       = db.relationship("PreOrder", back_populates="drop", lazy="dynamic")

    @property
    def price_dollars(self):
        return self.price / 100

    @property
    def units_sold(self):
        return self.orders.filter_by(status="completed").count()

    @property
    def units_available(self):
        sold = self.units_sold
        locked = self.checkout_locks.filter(
            CheckoutLock.expires_at > datetime.utcnow(),
            CheckoutLock.status == "active"
        ).count()
        return self.total_units - self.units_reserved - sold - locked

    @property
    def hype_pct(self):
        sellable = self.total_units - self.units_reserved
        if sellable <= 0:
            return 0
        return round((self.units_sold / sellable) * 100, 1)

    def to_dict(self):
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "colorway": self.colorway,
            "sizes": self.sizes,
            "price": self.price,
            "price_dollars": self.price_dollars,
            "description": self.description,
            "status": self.status,
            "total_units": self.total_units,
            "units_reserved": self.units_reserved,
            "units_sold": self.units_sold,
            "units_available": self.units_available,
            "hype_pct": self.hype_pct,
            "use_raffle": self.use_raffle,
            "max_per_member": self.max_per_member,
            "drop_at": self.drop_at.isoformat() if self.drop_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "created_at": self.created_at.isoformat(),
        }


# ── Waitlist / Raffle ─────────────────────────────────────────────────────────

class WaitlistEntry(db.Model):
    __tablename__ = "waitlist_entries"

    id          = db.Column(db.Integer, primary_key=True)
    drop_id     = db.Column(db.Integer, db.ForeignKey("drops.id"), nullable=False)
    member_id   = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    size        = db.Column(db.String(10), nullable=False)
    status      = db.Column(db.String(20), default="entered")  # entered/selected/not_selected/purchased
    selected_at = db.Column(db.DateTime, nullable=True)
    entered_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    drop        = db.relationship("Drop", back_populates="waitlist_entries")
    member      = db.relationship("Member", back_populates="waitlist_entries")

    __table_args__ = (
        db.UniqueConstraint("drop_id", "member_id", name="uq_waitlist_drop_member"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "drop_id": self.drop_id,
            "member_id": self.member_id,
            "size": self.size,
            "status": self.status,
            "entered_at": self.entered_at.isoformat(),
            "selected_at": self.selected_at.isoformat() if self.selected_at else None,
        }


# ── Orders ────────────────────────────────────────────────────────────────────

class Order(db.Model):
    __tablename__ = "orders"

    id              = db.Column(db.Integer, primary_key=True)
    order_number    = db.Column(db.String(20), unique=True, nullable=False,
                                default=lambda: f"JNC-{secrets.token_hex(4).upper()}")
    drop_id         = db.Column(db.Integer, db.ForeignKey("drops.id"), nullable=False)
    member_id       = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=True)
    retailer_id     = db.Column(db.Integer, db.ForeignKey("retailers.id"), nullable=True)
    checkout_lock_id= db.Column(db.Integer, db.ForeignKey("checkout_locks.id"), nullable=True)
    status          = db.Column(db.String(20), default="pending")
                                # pending/completed/refunded/cancelled
    total_cents     = db.Column(db.Integer, nullable=False)
    stripe_payment_intent = db.Column(db.String(255), nullable=True)
    shipping_name   = db.Column(db.String(150), nullable=True)
    shipping_address= db.Column(db.Text, nullable=True)
    shipped_at      = db.Column(db.DateTime, nullable=True)
    tracking_number = db.Column(db.String(100), nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    drop            = db.relationship("Drop", back_populates="orders")
    member          = db.relationship("Member", back_populates="orders")
    items           = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    certificate     = db.relationship("Certificate", back_populates="order", uselist=False)
    checkout_lock   = db.relationship("CheckoutLock", foreign_keys=[checkout_lock_id])

    def to_dict(self):
        return {
            "id": self.id,
            "order_number": self.order_number,
            "drop_id": self.drop_id,
            "member_id": self.member_id,
            "retailer_id": self.retailer_id,
            "checkout_lock_id": self.checkout_lock_id,
            "status": self.status,
            "total_cents": self.total_cents,
            "total_dollars": self.total_cents / 100,
            "stripe_payment_intent": self.stripe_payment_intent,
            "shipping_name": self.shipping_name,
            "shipping_address": self.shipping_address,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "tracking_number": self.tracking_number,
            "items": [i.to_dict() for i in self.items],
            "created_at": self.created_at.isoformat(),
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id          = db.Column(db.Integer, primary_key=True)
    order_id    = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    size        = db.Column(db.String(10), nullable=False)
    quantity    = db.Column(db.Integer, default=1)
    unit_price  = db.Column(db.Integer, nullable=False)  # cents

    # Relationships
    order       = db.relationship("Order", back_populates="items")

    def to_dict(self):
        return {
            "id": self.id,
            "size": self.size,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "unit_price_dollars": self.unit_price / 100,
        }


# ── Checkout Locks ────────────────────────────────────────────────────────────

class CheckoutLock(db.Model):
    __tablename__ = "checkout_locks"

    id          = db.Column(db.Integer, primary_key=True)
    drop_id     = db.Column(db.Integer, db.ForeignKey("drops.id"), nullable=False)
    member_id   = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=True)
    size        = db.Column(db.String(10), nullable=False)
    quantity    = db.Column(db.Integer, default=1)
    status      = db.Column(db.String(20), default="active")  # active/completed/expired
    expires_at  = db.Column(db.DateTime, nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    drop        = db.relationship("Drop", back_populates="checkout_locks")

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    def to_dict(self):
        return {
            "id": self.id,
            "drop_id": self.drop_id,
            "size": self.size,
            "quantity": self.quantity,
            "status": self.status,
            "expires_at": self.expires_at.isoformat(),
            "is_expired": self.is_expired,
        }


# ── Authenticity Certificates ─────────────────────────────────────────────────

class Certificate(db.Model):
    __tablename__ = "certificates"

    id              = db.Column(db.Integer, primary_key=True)
    cert_number     = db.Column(db.String(30), unique=True, nullable=False)
    drop_id         = db.Column(db.Integer, db.ForeignKey("drops.id"), nullable=False)
    order_id        = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    member_id       = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=True)
    size            = db.Column(db.String(10), nullable=False)
    run_number      = db.Column(db.Integer, nullable=False)   # e.g. 14
    total_run       = db.Column(db.Integer, nullable=False)   # e.g. 150
    verify_token    = db.Column(db.String(64), unique=True, nullable=False,
                                default=lambda: secrets.token_urlsafe(32))
    issued_at       = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    drop            = db.relationship("Drop", back_populates="certificates")
    order           = db.relationship("Order", back_populates="certificate")
    member          = db.relationship("Member", back_populates="certificates")

    def to_dict(self):
        return {
            "id": self.id,
            "cert_number": self.cert_number,
            "drop_id": self.drop_id,
            "drop_name": self.drop.name if self.drop else None,
            "order_id": self.order_id,
            "member_id": self.member_id,
            "size": self.size,
            "run_number": self.run_number,
            "total_run": self.total_run,
            "verify_token": self.verify_token,
            "issued_at": self.issued_at.isoformat(),
            "verify_url": f"/verify/{self.verify_token}",
        }


# ── QR Campaigns ──────────────────────────────────────────────────────────────

class QRCampaign(db.Model):
    __tablename__ = "qr_campaigns"

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(150), nullable=False)
    drop_id         = db.Column(db.Integer, db.ForeignKey("drops.id"), nullable=True)
    destination_url = db.Column(db.String(500), nullable=False)
    campaign_token  = db.Column(db.String(32), unique=True, nullable=False,
                                default=lambda: secrets.token_hex(16))
    status          = db.Column(db.String(20), default="active")  # active/ended
    expires_at      = db.Column(db.DateTime, nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    scans           = db.relationship("QRScan", back_populates="campaign", lazy="dynamic")

    @property
    def scan_count(self):
        return self.scans.count()

    @property
    def conversion_rate(self):
        total = self.scan_count
        if total == 0:
            return 0
        converted = self.scans.filter_by(converted=True).count()
        return round((converted / total) * 100, 1)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "drop_id": self.drop_id,
            "destination_url": self.destination_url,
            "campaign_token": self.campaign_token,
            "status": self.status,
            "scan_count": self.scan_count,
            "conversion_rate": self.conversion_rate,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
            "qr_url": f"/qr/{self.campaign_token}",
        }


class QRScan(db.Model):
    __tablename__ = "qr_scans"

    id              = db.Column(db.Integer, primary_key=True)
    campaign_id     = db.Column(db.Integer, db.ForeignKey("qr_campaigns.id"), nullable=False)
    ip_address      = db.Column(db.String(45), nullable=True)
    user_agent      = db.Column(db.String(500), nullable=True)
    converted       = db.Column(db.Boolean, default=False)
    scanned_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    campaign        = db.relationship("QRCampaign", back_populates="scans")


# ── Pre-Orders ────────────────────────────────────────────────────────────────

class PreOrder(db.Model):
    __tablename__ = "preorders"

    id              = db.Column(db.Integer, primary_key=True)
    drop_id         = db.Column(db.Integer, db.ForeignKey("drops.id"), nullable=False)
    member_id       = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=True)
    email           = db.Column(db.String(255), nullable=False)
    name            = db.Column(db.String(150), nullable=False)
    size            = db.Column(db.String(10), nullable=False)
    deposit_cents   = db.Column(db.Integer, default=0)
    stripe_payment_intent = db.Column(db.String(255), nullable=True)
    status          = db.Column(db.String(20), default="pending")
                                # pending/confirmed/fulfilled/refunded/cancelled
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    drop            = db.relationship("Drop", back_populates="preorders")
    member          = db.relationship("Member", back_populates="preorders")

    __table_args__ = (
        db.UniqueConstraint("drop_id", "email", name="uq_preorder_drop_email"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "drop_id": self.drop_id,
            "member_id": self.member_id,
            "email": self.email,
            "name": self.name,
            "size": self.size,
            "deposit_cents": self.deposit_cents,
            "deposit_dollars": self.deposit_cents / 100,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


# ── Retailer Allocations ──────────────────────────────────────────────────────

class RetailerAllocation(db.Model):
    __tablename__ = "retailer_allocations"

    id              = db.Column(db.Integer, primary_key=True)
    retailer_id     = db.Column(db.Integer, db.ForeignKey("retailers.id"), nullable=False)
    drop_id         = db.Column(db.Integer, db.ForeignKey("drops.id"), nullable=False)
    allocated_units = db.Column(db.Integer, nullable=False)
    purchased_units = db.Column(db.Integer, default=0)
    status          = db.Column(db.String(20), default="pending")  # pending/confirmed/shipped
    invoice_number  = db.Column(db.String(50), nullable=True)
    purchase_order_number = db.Column(db.String(50), nullable=True)
    shipped_at      = db.Column(db.DateTime, nullable=True)
    tracking_number = db.Column(db.String(100), nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    retailer        = db.relationship("Retailer", back_populates="allocations")
    drop            = db.relationship("Drop", back_populates="allocations")

    __table_args__ = (
        db.UniqueConstraint("retailer_id", "drop_id", name="uq_allocation_retailer_drop"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "retailer_id": self.retailer_id,
            "retailer_name": self.retailer.name if self.retailer else None,
            "drop_id": self.drop_id,
            "drop_name": self.drop.name if self.drop else None,
            "allocated_units": self.allocated_units,
            "purchased_units": self.purchased_units,
            "remaining_units": self.allocated_units - self.purchased_units,
            "status": self.status,
            "invoice_number": self.invoice_number,
            "purchase_order_number": self.purchase_order_number,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "tracking_number": self.tracking_number,
            "created_at": self.created_at.isoformat(),
        }


# ── Notifications (email queue) ───────────────────────────────────────────────

class Notification(db.Model):
    __tablename__ = "notifications"

    id              = db.Column(db.Integer, primary_key=True)
    recipient_email = db.Column(db.String(255), nullable=False)
    recipient_name  = db.Column(db.String(150), nullable=True)
    subject         = db.Column(db.String(255), nullable=False)
    body_html       = db.Column(db.Text, nullable=False)
    notif_type      = db.Column(db.String(50), nullable=False)
                                # drop_announcement/order_confirm/waitlist_result/
                                # retailer_update/cert_issued
    status          = db.Column(db.String(20), default="queued")  # queued/sent/failed
    related_id      = db.Column(db.Integer, nullable=True)        # order_id, drop_id, etc.
    sent_at         = db.Column(db.DateTime, nullable=True)
    error           = db.Column(db.Text, nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "recipient_email": self.recipient_email,
            "subject": self.subject,
            "notif_type": self.notif_type,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat(),
        }
