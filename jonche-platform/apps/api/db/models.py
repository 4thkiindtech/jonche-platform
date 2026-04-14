"""
apps/api/db/models.py
All database models for the Jonche Platform.

Tables:
  - admins          → platform admin accounts
  - retailers       → wholesale partner accounts
  - members         → VIP club members
  - drops           → limited release drops
  - waitlist_entries → raffle entries per drop per member
  - orders          → completed purchases (guest + member orders)
  - order_items     → line items per order
  - checkout_locks  → timed reservation holds (8 min)
  - certificates    → authenticity certificates
  - qr_campaigns    → QR tracking campaigns
  - qr_scans        → individual scan events
  - preorders       → pre-order campaign entries
  - partner_applications → partner program intake submissions
  - retailer_allocations → per-drop allocations to retailers
  - notifications   → outbound email queue
  - email_subscribers → newsletter/notification opt-ins (NEW)
  - guest_order_lookup → guest order public lookup tokens (NEW)
  - order_tracking  → external fulfillment tracking data (NEW)
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
    carts           = db.relationship("Cart", foreign_keys="Cart.member_id", lazy="dynamic")

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
    # Apliiq fulfillment mapping
    apliiq_product_id = db.Column(db.String(100), nullable=True)
    apliiq_variant_id = db.Column(db.String(100), nullable=True)
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
            "apliiq_product_id": self.apliiq_product_id,
            "apliiq_variant_id": self.apliiq_variant_id,
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
    shipping_email  = db.Column(db.String(255), nullable=True)  # Guest email (no account)
    shipping_address= db.Column(db.Text, nullable=True)
    shipped_at      = db.Column(db.DateTime, nullable=True)
    tracking_number = db.Column(db.String(100), nullable=True)
    # Apliiq fulfillment
    apliiq_order_id = db.Column(db.String(100), nullable=True)
    apliiq_status   = db.Column(db.String(50), nullable=True)   # e.g. pending/in_production/shipped
    suppress_manufacturer_emails = db.Column(db.Boolean, default=True)  # Prevent manufacturers from sending emails
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
            "shipping_email": self.shipping_email,
            "shipping_address": self.shipping_address,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "tracking_number": self.tracking_number,
            "items": [i.to_dict() for i in self.items],
            "apliiq_order_id": self.apliiq_order_id,
            "apliiq_status": self.apliiq_status,
            "suppress_manufacturer_emails": self.suppress_manufacturer_emails,
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


# ── Store: Products & Commercials ────────────────────────────────────────────

class ProductCategory(db.Model):
    __tablename__ = "product_categories"

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(150), nullable=False, unique=True)
    slug            = db.Column(db.String(200), nullable=False, unique=True)
    description     = db.Column(db.Text, nullable=True)
    image_url       = db.Column(db.String(500), nullable=True)
    display_order   = db.Column(db.Integer, default=0)
    is_active       = db.Column(db.Boolean, default=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    products        = db.relationship("Product", back_populates="category", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "image_url": self.image_url,
            "display_order": self.display_order,
            "is_active": self.is_active,
            "product_count": self.products.count(),
            "created_at": self.created_at.isoformat(),
        }


class Product(db.Model):
    __tablename__ = "products"

    id              = db.Column(db.Integer, primary_key=True)
    sku             = db.Column(db.String(100), unique=True, nullable=False)
    name            = db.Column(db.String(200), nullable=False)
    slug            = db.Column(db.String(200), unique=True, nullable=False)
    description     = db.Column(db.Text, nullable=True)
    category_id     = db.Column(db.Integer, db.ForeignKey("product_categories.id"), nullable=False)
    base_price      = db.Column(db.Integer, nullable=False)  # cents
    is_available    = db.Column(db.Boolean, default=True)
    display_order   = db.Column(db.Integer, default=0)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category        = db.relationship("ProductCategory", back_populates="products")
    images          = db.relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    variants        = db.relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    cart_items      = db.relationship("CartItem", back_populates="product", cascade="all, delete-orphan")

    @property
    def price_dollars(self):
        return self.base_price / 100

    @property
    def total_quantity(self):
        return sum(v.quantity_in_stock for v in self.variants)

    @property
    def primary_image(self):
        return self.images.filter_by(is_primary=True).first() or self.images.first()

    def to_dict(self, include_variants=False):
        data = {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "base_price": self.base_price,
            "base_price_dollars": self.price_dollars,
            "is_available": self.is_available,
            "total_quantity": self.total_quantity,
            "display_order": self.display_order,
            "primary_image": self.primary_image.to_dict() if self.primary_image else None,
            "image_count": len(self.images),
            "created_at": self.created_at.isoformat(),
        }
        if include_variants:
            data["variants"] = [v.to_dict() for v in self.variants]
            data["images"] = [img.to_dict() for img in self.images]
        return data


class ProductVariant(db.Model):
    __tablename__ = "product_variants"

    id              = db.Column(db.Integer, primary_key=True)
    product_id      = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    variant_sku     = db.Column(db.String(100), unique=True, nullable=False)
    option_name     = db.Column(db.String(50), nullable=False)  # "size", "color", "material", etc.
    option_value    = db.Column(db.String(100), nullable=False)  # "M", "Blue", "Leather", etc.
    price_override  = db.Column(db.Integer, nullable=True)  # cents, null = use base_price
    quantity_in_stock = db.Column(db.Integer, default=0)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    product         = db.relationship("Product", back_populates="variants")
    cart_items      = db.relationship("CartItem", back_populates="variant")

    __table_args__ = (
        db.UniqueConstraint("product_id", "option_name", "option_value", 
                            name="uq_variant_product_option"),
    )

    @property
    def price(self):
        return self.price_override if self.price_override is not None else self.product.base_price

    @property
    def price_dollars(self):
        return self.price / 100

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "variant_sku": self.variant_sku,
            "option_name": self.option_name,
            "option_value": self.option_value,
            "price": self.price,
            "price_dollars": self.price_dollars,
            "quantity_in_stock": self.quantity_in_stock,
            "created_at": self.created_at.isoformat(),
        }


class ProductImage(db.Model):
    __tablename__ = "product_images"

    id              = db.Column(db.Integer, primary_key=True)
    product_id      = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    image_url       = db.Column(db.String(500), nullable=False)
    alt_text        = db.Column(db.String(255), nullable=True)
    is_primary      = db.Column(db.Boolean, default=False)
    display_order   = db.Column(db.Integer, default=0)
    uploaded_at     = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    product         = db.relationship("Product", back_populates="images")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "image_url": self.image_url,
            "alt_text": self.alt_text,
            "is_primary": self.is_primary,
            "display_order": self.display_order,
        }


# ── Generated Product Images (AI/Pygame Enhanced) ───────────────────────────

class GeneratedProductImage(db.Model):
    __tablename__ = "generated_product_images"

    id              = db.Column(db.Integer, primary_key=True)
    product_id      = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    image_type      = db.Column(db.String(50), nullable=False)  # 'angle', 'size_comparison', etc.
    image_url       = db.Column(db.String(500), nullable=False)
    parameters      = db.Column(db.JSON, nullable=True)  # e.g., {"angle": 45, "reference_type": "credit_card"}
    generated_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    product         = db.relationship("Product", foreign_keys=[product_id])

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "image_type": self.image_type,
            "image_url": self.image_url,
            "parameters": self.parameters,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }


class Commercial(db.Model):
    __tablename__ = "commercials"

    id              = db.Column(db.Integer, primary_key=True)
    title           = db.Column(db.String(200), nullable=False)
    description     = db.Column(db.Text, nullable=True)
    video_url       = db.Column(db.String(500), nullable=False)
    thumbnail_url   = db.Column(db.String(500), nullable=True)
    display_order   = db.Column(db.Integer, default=0)
    is_active       = db.Column(db.Boolean, default=True)
    video_duration_seconds = db.Column(db.Integer, nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "video_url": self.video_url,
            "thumbnail_url": self.thumbnail_url,
            "display_order": self.display_order,
            "is_active": self.is_active,
            "video_duration_seconds": self.video_duration_seconds,
        }


class Cart(db.Model):
    __tablename__ = "carts"

    id              = db.Column(db.Integer, primary_key=True)
    member_id       = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=True)
    session_token   = db.Column(db.String(100), unique=True, nullable=True)  # for guests
    status          = db.Column(db.String(20), default="active")  # active/completed/abandoned
    expires_at      = db.Column(db.DateTime, nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items           = db.relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

    @property
    def total_cents(self):
        return sum(item.item_total_cents for item in self.items)

    @property
    def total_dollars(self):
        return self.total_cents / 100

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items)

    def to_dict(self, include_items=True):
        data = {
            "id": self.id,
            "member_id": self.member_id,
            "item_count": self.item_count,
            "total_cents": self.total_cents,
            "total_dollars": self.total_dollars,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        return data


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id              = db.Column(db.Integer, primary_key=True)
    cart_id         = db.Column(db.Integer, db.ForeignKey("carts.id"), nullable=False)
    product_id      = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    variant_id      = db.Column(db.Integer, db.ForeignKey("product_variants.id"), nullable=True)
    quantity        = db.Column(db.Integer, default=1)
    unit_price_cents = db.Column(db.Integer, nullable=False)  # price at time of add
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    cart            = db.relationship("Cart", back_populates="items")
    product         = db.relationship("Product", back_populates="cart_items")
    variant         = db.relationship("ProductVariant", back_populates="cart_items")

    @property
    def item_total_cents(self):
        return self.unit_price_cents * self.quantity

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "variant_id": self.variant_id,
            "variant_sku": self.variant.variant_sku if self.variant else None,
            "variant_option": f"{self.variant.option_name}: {self.variant.option_value}" if self.variant else None,
            "quantity": self.quantity,
            "unit_price_cents": self.unit_price_cents,
            "unit_price_dollars": self.unit_price_cents / 100,
            "item_total_cents": self.item_total_cents,
            "item_total_dollars": self.item_total_cents / 100,
        }


# ── Warehouses ────────────────────────────────────────────────────────────────

class Warehouse(db.Model):
    __tablename__ = "warehouses"

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(150), nullable=False, unique=True)
    warehouse_type  = db.Column(db.String(50), nullable=False)  # apliiq/shoe_warehouse
    location        = db.Column(db.String(255), nullable=True)
    webhook_url     = db.Column(db.String(500), nullable=True)
    webhook_secret  = db.Column(db.String(500), nullable=True)  # For HMAC validation
    is_active       = db.Column(db.Boolean, default=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    inventory_items = db.relationship("InventoryItem", back_populates="warehouse", lazy="dynamic")
    fulfillment_events = db.relationship("FulfillmentEvent", back_populates="warehouse", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "warehouse_type": self.warehouse_type,
            "location": self.location,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }


# ── Shoe Designs (from AliveShoes) ────────────────────────────────────────────

class ShoeDesign(db.Model):
    __tablename__ = "shoe_designs"

    id              = db.Column(db.Integer, primary_key=True)
    aliveshoes_id   = db.Column(db.String(100), nullable=True, unique=True)  # AliveShoes shoe ID
    name            = db.Column(db.String(255), nullable=False)
    description     = db.Column(db.Text, nullable=True)
    design_image_url = db.Column(db.String(500), nullable=True)
    aliveshoes_url  = db.Column(db.String(500), nullable=True)  # Direct link to AliveShoes
    status          = db.Column(db.String(50), default="approved")  # approved/pending/disabled
    retail_price_cents = db.Column(db.Integer, nullable=False)  # Admin-set retail price
    markup_percentage = db.Column(db.Float, default=0.0)  # e.g. 30.0 for 30% markup
    sizes_available = db.Column(db.String(200), nullable=True)  # e.g. "7-14"
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    inventory_items = db.relationship("InventoryItem", back_populates="shoe_design", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "aliveshoes_id": self.aliveshoes_id,
            "name": self.name,
            "description": self.description,
            "design_image_url": self.design_image_url,
            "aliveshoes_url": self.aliveshoes_url,
            "status": self.status,
            "retail_price_cents": self.retail_price_cents,
            "retail_price_dollars": self.retail_price_cents / 100,
            "markup_percentage": self.markup_percentage,
            "sizes_available": self.sizes_available,
            "created_at": self.created_at.isoformat(),
        }


# ── Inventory Tracking ────────────────────────────────────────────────────────

class InventoryItem(db.Model):
    __tablename__ = "inventory_items"

    id              = db.Column(db.Integer, primary_key=True)
    warehouse_id    = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    shoe_design_id  = db.Column(db.Integer, db.ForeignKey("shoe_designs.id"), nullable=True)
    sku             = db.Column(db.String(100), nullable=False)  # Apliiq SKU or internal shoe SKU
    name            = db.Column(db.String(255), nullable=False)
    category        = db.Column(db.String(50), nullable=True)  # clothing/shoes
    quantity_available = db.Column(db.Integer, default=0)
    quantity_reserved = db.Column(db.Integer, default=0)
    quantity_total  = db.Column(db.Integer, default=0)
    unit_cost_cents = db.Column(db.Integer, nullable=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    warehouse       = db.relationship("Warehouse", back_populates="inventory_items")
    shoe_design     = db.relationship("ShoeDesign", back_populates="inventory_items")

    __table_args__ = (
        db.UniqueConstraint("warehouse_id", "sku", name="uq_inventory_warehouse_sku"),
    )


# ── Affiliate Creator Accounts ────────────────────────────────────────────────

class AffiliateAccount(db.Model):
    __tablename__ = "affiliate_accounts"

    id                      = db.Column(db.Integer, primary_key=True)
    email                   = db.Column(db.String(255), unique=True, nullable=False)
    password_hash           = db.Column(db.String(255), nullable=False)
    display_name            = db.Column(db.String(150), nullable=False)
    bio                     = db.Column(db.Text, nullable=True)
    profile_image_url       = db.Column(db.String(500), nullable=True)
    instagram_handle        = db.Column(db.String(100), nullable=True)
    tiktok_handle           = db.Column(db.String(100), nullable=True)
    youtube_handle          = db.Column(db.String(100), nullable=True)
    website_url             = db.Column(db.String(255), nullable=True)
    
    # Referral tracking
    referral_link_token     = db.Column(db.String(32), unique=True, nullable=False,
                                       default=lambda: secrets.token_urlsafe(24))
    commission_rate_percent = db.Column(db.Float, default=10.0)
    
    # Performance
    total_earnings_cents    = db.Column(db.Integer, default=0)
    pending_earnings_cents  = db.Column(db.Integer, default=0)
    total_clicks            = db.Column(db.Integer, default=0)
    total_conversions       = db.Column(db.Integer, default=0)
    
    # Status
    status                  = db.Column(db.String(20), default="active")
    verified_at             = db.Column(db.DateTime, nullable=True)
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)
    last_login              = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    earnings                = db.relationship("AffiliateEarning", back_populates="affiliate", cascade="all, delete-orphan", lazy="dynamic")
    messages                = db.relationship("PartnerMessage", foreign_keys="PartnerMessage.affiliate_id", back_populates="affiliate", lazy="dynamic")
    
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "bio": self.bio,
            "profile_image_url": self.profile_image_url,
            "instagram_handle": self.instagram_handle,
            "tiktok_handle": self.tiktok_handle,
            "youtube_handle": self.youtube_handle,
            "website_url": self.website_url,
            "referral_link": f"/ref/{self.referral_link_token}",
            "commission_rate_percent": self.commission_rate_percent,
            "total_earnings_cents": self.total_earnings_cents,
            "total_earnings_dollars": self.total_earnings_cents / 100,
            "pending_earnings_cents": self.pending_earnings_cents,
            "pending_earnings_dollars": self.pending_earnings_cents / 100,
            "total_clicks": self.total_clicks,
            "total_conversions": self.total_conversions,
            "conversion_rate": round((self.total_conversions / self.total_clicks * 100), 1) if self.total_clicks > 0 else 0,
            "status": self.status,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "created_at": self.created_at.isoformat(),
        }


# ── Referral Partner Accounts ─────────────────────────────────────────────────

class ReferralPartnerAccount(db.Model):
    __tablename__ = "referral_partner_accounts"

    id                      = db.Column(db.Integer, primary_key=True)
    email                   = db.Column(db.String(255), unique=True, nullable=False)
    password_hash           = db.Column(db.String(255), nullable=False)
    contact_name            = db.Column(db.String(150), nullable=False)
    company_name            = db.Column(db.String(200), nullable=True)
    phone                   = db.Column(db.String(30), nullable=True)
    city                    = db.Column(db.String(100), nullable=True)
    state                   = db.Column(db.String(50), nullable=True)
    
    # Performance tracking
    total_deals_submitted   = db.Column(db.Integer, default=0)
    total_deals_funded      = db.Column(db.Integer, default=0)
    projected_commission_cents = db.Column(db.Integer, default=0)
    total_commission_cents  = db.Column(db.Integer, default=0)
    pending_commission_cents = db.Column(db.Integer, default=0)
    
    # Tier & Status
    tier                    = db.Column(db.String(20), default="bronze")
    status                  = db.Column(db.String(20), default="active")
    verified_at             = db.Column(db.DateTime, nullable=True)
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)
    last_login              = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    referrals               = db.relationship("PartnerReferral", back_populates="referral_partner", cascade="all, delete-orphan", lazy="dynamic")
    messages                = db.relationship("PartnerMessage", foreign_keys="PartnerMessage.referral_partner_id", back_populates="referral_partner", lazy="dynamic")
    
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "contact_name": self.contact_name,
            "company_name": self.company_name,
            "phone": self.phone,
            "city": self.city,
            "state": self.state,
            "total_deals_submitted": self.total_deals_submitted,
            "total_deals_funded": self.total_deals_funded,
            "funding_success_rate": round((self.total_deals_funded / self.total_deals_submitted * 100), 1) if self.total_deals_submitted > 0 else 0,
            "projected_commission_cents": self.projected_commission_cents,
            "projected_commission_dollars": self.projected_commission_cents / 100,
            "total_commission_cents": self.total_commission_cents,
            "total_commission_dollars": self.total_commission_cents / 100,
            "pending_commission_cents": self.pending_commission_cents,
            "pending_commission_dollars": self.pending_commission_cents / 100,
            "tier": self.tier,
            "status": self.status,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "created_at": self.created_at.isoformat(),
        }


# ── Retail Alliance Partner Accounts ──────────────────────────────────────────

class RetailPartnerAccount(db.Model):
    __tablename__ = "retail_partner_accounts"

    id                      = db.Column(db.Integer, primary_key=True)
    retailer_id             = db.Column(db.Integer, db.ForeignKey("retailers.id"), nullable=True)
    email                   = db.Column(db.String(255), unique=True, nullable=False)
    password_hash           = db.Column(db.String(255), nullable=False)
    store_name              = db.Column(db.String(200), nullable=False)
    contact_name            = db.Column(db.String(150), nullable=False)
    phone                   = db.Column(db.String(30), nullable=True)
    city                    = db.Column(db.String(100), nullable=True)
    state                   = db.Column(db.String(50), nullable=True)
    website_url             = db.Column(db.String(255), nullable=True)
    
    # Allocation & Order tracking
    total_allocations       = db.Column(db.Integer, default=0)
    total_purchased_units   = db.Column(db.Integer, default=0)
    pending_orders          = db.Column(db.Integer, default=0)
    
    # Status
    tier                    = db.Column(db.String(20), default="basic")
    status                  = db.Column(db.String(20), default="active")
    verified_at             = db.Column(db.DateTime, nullable=True)
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)
    last_login              = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    retailer                = db.relationship("Retailer", foreign_keys=[retailer_id])
    messages                = db.relationship("PartnerMessage", foreign_keys="PartnerMessage.retail_partner_id", back_populates="retail_partner", lazy="dynamic")
    
    def to_dict(self):
        return {
            "id": self.id,
            "retailer_id": self.retailer_id,
            "email": self.email,
            "store_name": self.store_name,
            "contact_name": self.contact_name,
            "phone": self.phone,
            "city": self.city,
            "state": self.state,
            "website_url": self.website_url,
            "total_allocations": self.total_allocations,
            "total_purchased_units": self.total_purchased_units,
            "pending_orders": self.pending_orders,
            "tier": self.tier,
            "status": self.status,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "created_at": self.created_at.isoformat(),
        }


# ── Executive Partner Accounts ────────────────────────────────────────────────

class ExecutiveAccount(db.Model):
    __tablename__ = "executive_accounts"

    id                      = db.Column(db.Integer, primary_key=True)
    email                   = db.Column(db.String(255), unique=True, nullable=False)
    password_hash           = db.Column(db.String(255), nullable=False)
    executive_name          = db.Column(db.String(150), nullable=False)
    company_name            = db.Column(db.String(200), nullable=False)
    phone                   = db.Column(db.String(30), nullable=True)
    city                    = db.Column(db.String(100), nullable=True)
    state                   = db.Column(db.String(50), nullable=True)
    
    # Territory & Performance
    territory               = db.Column(db.String(100), nullable=True)
    total_deal_value_cents  = db.Column(db.Integer, default=0)
    total_commission_cents  = db.Column(db.Integer, default=0)
    pending_commission_cents = db.Column(db.Integer, default=0)
    
    # Status
    status                  = db.Column(db.String(20), default="active")
    verified_at             = db.Column(db.DateTime, nullable=True)
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)
    last_login              = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    deals                   = db.relationship("PartnerReferral", foreign_keys="PartnerReferral.executive_id", back_populates="executive", lazy="dynamic")
    messages                = db.relationship("PartnerMessage", foreign_keys="PartnerMessage.executive_id", back_populates="executive", lazy="dynamic")
    
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "executive_name": self.executive_name,
            "company_name": self.company_name,
            "phone": self.phone,
            "city": self.city,
            "state": self.state,
            "territory": self.territory,
            "total_deal_value_cents": self.total_deal_value_cents,
            "total_deal_value_dollars": self.total_deal_value_cents / 100,
            "total_commission_cents": self.total_commission_cents,
            "total_commission_dollars": self.total_commission_cents / 100,
            "pending_commission_cents": self.pending_commission_cents,
            "pending_commission_dollars": self.pending_commission_cents / 100,
            "status": self.status,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "created_at": self.created_at.isoformat(),
        }


# ── Affiliate Earnings Tracking ───────────────────────────────────────────────

class AffiliateEarning(db.Model):
    __tablename__ = "affiliate_earnings"

    id                      = db.Column(db.Integer, primary_key=True)
    affiliate_id            = db.Column(db.Integer, db.ForeignKey("affiliate_accounts.id"), nullable=False)
    order_id                = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    referral_source         = db.Column(db.String(50), nullable=False)
    order_value_cents       = db.Column(db.Integer, nullable=False)
    commission_rate_percent = db.Column(db.Float, nullable=False)
    commission_cents        = db.Column(db.Integer, nullable=False)
    status                  = db.Column(db.String(20), default="pending")
    paid_at                 = db.Column(db.DateTime, nullable=True)
    payout_batch_id         = db.Column(db.String(100), nullable=True)
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    affiliate               = db.relationship("AffiliateAccount", back_populates="earnings")
    order                   = db.relationship("Order", foreign_keys=[order_id])
    
    def to_dict(self):
        return {
            "id": self.id,
            "affiliate_id": self.affiliate_id,
            "order_id": self.order_id,
            "referral_source": self.referral_source,
            "order_value_cents": self.order_value_cents,
            "order_value_dollars": self.order_value_cents / 100,
            "commission_rate_percent": self.commission_rate_percent,
            "commission_cents": self.commission_cents,
            "commission_dollars": self.commission_cents / 100,
            "status": self.status,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "payout_batch_id": self.payout_batch_id,
            "created_at": self.created_at.isoformat(),
        }


# ── Partner Referrals (Deals, Bulk Orders, Funding) ───────────────────────────

class PartnerReferral(db.Model):
    __tablename__ = "partner_referrals"

    id                      = db.Column(db.Integer, primary_key=True)
    referral_partner_id     = db.Column(db.Integer, db.ForeignKey("referral_partner_accounts.id"), nullable=True)
    executive_id            = db.Column(db.Integer, db.ForeignKey("executive_accounts.id"), nullable=True)
    referral_type           = db.Column(db.String(50), nullable=False)
    title                   = db.Column(db.String(255), nullable=False)
    description             = db.Column(db.Text, nullable=True)
    
    # Deal value tracking
    estimated_value_cents   = db.Column(db.Integer, nullable=False)
    actual_value_cents      = db.Column(db.Integer, nullable=True)
    commission_percent      = db.Column(db.Float, nullable=False)
    commission_cents        = db.Column(db.Integer, default=0)
    
    # Status
    status                  = db.Column(db.String(30), default="submitted")
    submitted_at            = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at               = db.Column(db.DateTime, nullable=True)
    paid_at                 = db.Column(db.DateTime, nullable=True)
    notes                   = db.Column(db.Text, nullable=True)
    
    # Relationships
    referral_partner        = db.relationship("ReferralPartnerAccount", back_populates="referrals")
    executive               = db.relationship("ExecutiveAccount", foreign_keys=[executive_id], back_populates="deals")
    
    def to_dict(self):
        return {
            "id": self.id,
            "referral_partner_id": self.referral_partner_id,
            "executive_id": self.executive_id,
            "referral_type": self.referral_type,
            "title": self.title,
            "description": self.description,
            "estimated_value_cents": self.estimated_value_cents,
            "estimated_value_dollars": self.estimated_value_cents / 100,
            "actual_value_cents": self.actual_value_cents,
            "actual_value_dollars": (self.actual_value_cents / 100) if self.actual_value_cents else None,
            "commission_percent": self.commission_percent,
            "commission_cents": self.commission_cents,
            "commission_dollars": self.commission_cents / 100,
            "status": self.status,
            "submitted_at": self.submitted_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "notes": self.notes,
        }


# ── Partner Messages (Inbox) ──────────────────────────────────────────────────

class PartnerMessage(db.Model):
    __tablename__ = "partner_messages"

    id                      = db.Column(db.Integer, primary_key=True)
    affiliate_id            = db.Column(db.Integer, db.ForeignKey("affiliate_accounts.id"), nullable=True)
    referral_partner_id     = db.Column(db.Integer, db.ForeignKey("referral_partner_accounts.id"), nullable=True)
    retail_partner_id       = db.Column(db.Integer, db.ForeignKey("retail_partner_accounts.id"), nullable=True)
    executive_id            = db.Column(db.Integer, db.ForeignKey("executive_accounts.id"), nullable=True)
    
    subject                 = db.Column(db.String(255), nullable=False)
    body                    = db.Column(db.Text, nullable=False)
    message_type            = db.Column(db.String(30), default="general")
    
    read_at                 = db.Column(db.DateTime, nullable=True)
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_admin        = db.Column(db.Boolean, default=True)
    
    # Relationships
    affiliate               = db.relationship("AffiliateAccount", foreign_keys=[affiliate_id], back_populates="messages")
    referral_partner        = db.relationship("ReferralPartnerAccount", foreign_keys=[referral_partner_id], back_populates="messages")
    retail_partner          = db.relationship("RetailPartnerAccount", foreign_keys=[retail_partner_id], back_populates="messages")
    executive               = db.relationship("ExecutiveAccount", foreign_keys=[executive_id], back_populates="messages")
    
    def to_dict(self):
        return {
            "id": self.id,
            "subject": self.subject,
            "body": self.body,
            "message_type": self.message_type,
            "is_read": self.read_at is not None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat(),
            "from_admin": self.created_by_admin,
        }


# ── Partner Announcements ─────────────────────────────────────────────────────

class PartnerAnnouncement(db.Model):
    __tablename__ = "partner_announcements"

    id                      = db.Column(db.Integer, primary_key=True)
    title                   = db.Column(db.String(255), nullable=False)
    content                 = db.Column(db.Text, nullable=False)
    target_groups           = db.Column(db.String(200), nullable=False)
    priority                = db.Column(db.String(20), default="normal")
    status                  = db.Column(db.String(20), default="draft")
    published_at            = db.Column(db.DateTime, nullable=True)
    expires_at              = db.Column(db.DateTime, nullable=True)
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_admin        = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "target_groups": self.target_groups.split(','),
            "priority": self.priority,
            "status": self.status,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
        }

    def to_dict(self):
        return {
            "id": self.id,
            "warehouse_id": self.warehouse_id,
            "warehouse_name": self.warehouse.name if self.warehouse else None,
            "shoe_design_id": self.shoe_design_id,
            "shoe_design_name": self.shoe_design.name if self.shoe_design else None,
            "sku": self.sku,
            "name": self.name,
            "category": self.category,
            "quantity_available": self.quantity_available,
            "quantity_reserved": self.quantity_reserved,
            "quantity_total": self.quantity_total,
            "unit_cost_cents": self.unit_cost_cents,
            "unit_cost_dollars": self.unit_cost_cents / 100,
            "created_at": self.created_at.isoformat(),
        }


# ── Store Orders (Retailer purchases) ─────────────────────────────────────────

class StoreOrder(db.Model):
    __tablename__ = "store_orders"

    id              = db.Column(db.Integer, primary_key=True)
    order_number    = db.Column(db.String(30), unique=True, nullable=False,
                                default=lambda: f"STORE-{secrets.token_hex(4).upper()}")
    retailer_id     = db.Column(db.Integer, db.ForeignKey("retailers.id"), nullable=False)
    warehouse_id    = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    order_type      = db.Column(db.String(50), nullable=False)  # apliiq/custom_shoes
    status          = db.Column(db.String(20), default="pending")
                                # pending/confirmed/in_fulfillment/shipped/completed/cancelled
    total_cents     = db.Column(db.Integer, nullable=False)
    shipping_name   = db.Column(db.String(150), nullable=True)
    shipping_address= db.Column(db.Text, nullable=True)
    tracking_number = db.Column(db.String(100), nullable=True)
    fulfillment_status = db.Column(db.String(50), nullable=True)  # Maps to warehouse status
    apliiq_order_id = db.Column(db.String(100), nullable=True)    # If order type is apliiq
    # Payment fields
    stripe_payment_intent = db.Column(db.String(255), nullable=True)
    payment_status  = db.Column(db.String(50), default="unpaid")  # unpaid/pending/paid/failed/refunded
    payment_completed_at = db.Column(db.DateTime, nullable=True)
    invoice_url     = db.Column(db.String(500), nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    retailer        = db.relationship("Retailer", foreign_keys=[retailer_id])
    warehouse       = db.relationship("Warehouse")
    items           = db.relationship("StoreOrderItem", back_populates="store_order", cascade="all, delete-orphan")
    fulfillment_event = db.relationship("FulfillmentEvent", back_populates="store_order", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "order_number": self.order_number,
            "retailer_id": self.retailer_id,
            "warehouse_id": self.warehouse_id,
            "order_type": self.order_type,
            "status": self.status,
            "total_cents": self.total_cents,
            "total_dollars": self.total_cents / 100,
            "shipping_name": self.shipping_name,
            "shipping_address": self.shipping_address,
            "tracking_number": self.tracking_number,
            "fulfillment_status": self.fulfillment_status,
            "apliiq_order_id": self.apliiq_order_id,
            "stripe_payment_intent": self.stripe_payment_intent,
            "payment_status": self.payment_status,
            "payment_completed_at": self.payment_completed_at.isoformat() if self.payment_completed_at else None,
            "invoice_url": self.invoice_url,
            "items": [i.to_dict() for i in self.items],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# ── Store Order Items ─────────────────────────────────────────────────────────

class StoreOrderItem(db.Model):
    __tablename__ = "store_order_items"

    id              = db.Column(db.Integer, primary_key=True)
    store_order_id  = db.Column(db.Integer, db.ForeignKey("store_orders.id"), nullable=False)
    shoe_design_id  = db.Column(db.Integer, db.ForeignKey("shoe_designs.id"), nullable=True)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey("inventory_items.id"), nullable=True)
    sku             = db.Column(db.String(100), nullable=False)
    name            = db.Column(db.String(255), nullable=False)
    size            = db.Column(db.String(20), nullable=True)
    quantity        = db.Column(db.Integer, default=1)
    unit_price_cents = db.Column(db.Integer, nullable=False)

    # Relationships
    store_order     = db.relationship("StoreOrder", back_populates="items")
    shoe_design     = db.relationship("ShoeDesign", foreign_keys=[shoe_design_id])
    inventory_item  = db.relationship("InventoryItem", foreign_keys=[inventory_item_id])

    def to_dict(self):
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "size": self.size,
            "quantity": self.quantity,
            "unit_price_cents": self.unit_price_cents,
            "unit_price_dollars": self.unit_price_cents / 100,
            "total_cents": self.unit_price_cents * self.quantity,
            "total_dollars": (self.unit_price_cents * self.quantity) / 100,
        }


# ── Fulfillment Events (Webhook tracking) ─────────────────────────────────────

class FulfillmentEvent(db.Model):
    __tablename__ = "fulfillment_events"

    id              = db.Column(db.Integer, primary_key=True)
    store_order_id  = db.Column(db.Integer, db.ForeignKey("store_orders.id"), nullable=False)
    warehouse_id    = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    status          = db.Column(db.String(50), nullable=False)  # success/pending/failed/shipped
    tracking_company = db.Column(db.String(100), nullable=True)
    tracking_numbers = db.Column(db.String(500), nullable=True)  # JSON array
    line_items      = db.Column(db.Text, nullable=True)         # JSON
    webhook_payload = db.Column(db.Text, nullable=True)         # Store raw payload for audit
    hmac_valid      = db.Column(db.Boolean, default=False)
    received_at     = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    store_order     = db.relationship("StoreOrder", back_populates="fulfillment_event")
    warehouse       = db.relationship("Warehouse", back_populates="fulfillment_events")

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "store_order_id": self.store_order_id,
            "warehouse_id": self.warehouse_id,
            "status": self.status,
            "tracking_company": self.tracking_company,
            "tracking_numbers": json.loads(self.tracking_numbers) if self.tracking_numbers else [],
            "hmac_valid": self.hmac_valid,
            "received_at": self.received_at.isoformat(),
        }


# ── Partner Applications (Public intake) ──────────────────────────────────────

class PartnerApplication(db.Model):
    __tablename__ = "partner_applications"

    id                     = db.Column(db.Integer, primary_key=True)
    program_type            = db.Column(db.String(60), nullable=False)  # retail_alliance/affiliate_creators/referral_network/executives
    source                 = db.Column(db.String(80), nullable=True)  # e.g. web/ig/tt/email/partner
    utm                    = db.Column(db.Text, nullable=True)  # JSON dict
    full_name               = db.Column(db.String(120), nullable=False)
    business_name           = db.Column(db.String(150), nullable=True)
    email                   = db.Column(db.String(255), nullable=False)
    phone                   = db.Column(db.String(50), nullable=True)
    website_or_social       = db.Column(db.String(255), nullable=True)
    city                    = db.Column(db.String(100), nullable=True)
    state                   = db.Column(db.String(50), nullable=True)
    estimated_monthly_reach = db.Column(db.String(50), nullable=True)
    network_type            = db.Column(db.String(80), nullable=True)
    interested_in           = db.Column(db.Text, nullable=True)  # JSON array
    additional_notes        = db.Column(db.Text, nullable=True)

    status                  = db.Column(db.String(30), default="new")  # new/contacted/approved/rejected
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "program_type": self.program_type,
            "source": self.source,
            "utm": json.loads(self.utm) if self.utm else {},
            "full_name": self.full_name,
            "business_name": self.business_name,
            "email": self.email,
            "phone": self.phone,
            "website_or_social": self.website_or_social,
            "city": self.city,
            "state": self.state,
            "estimated_monthly_reach": self.estimated_monthly_reach,
            "network_type": self.network_type,
            "interested_in": json.loads(self.interested_in) if self.interested_in else [],
            "additional_notes": self.additional_notes,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


# ── Phase 4 Lite: Payout Infrastructure ──────────────────────────────────────

class PayoutSchedule(db.Model):
    """Defines payout schedule rules for each partner type."""
    __tablename__ = "payout_schedules"

    id                      = db.Column(db.Integer, primary_key=True)
    partner_type            = db.Column(db.String(50), nullable=False, unique=True)
                                # affiliate/referral_partner/retail_partner/executive
    frequency               = db.Column(db.String(20), nullable=False)
                                # monthly/biweekly/weekly
    day_of_cycle            = db.Column(db.String(100), nullable=False)
                                # "last_business_day", "1st", "15th", "monday"
    minimum_payout_cents    = db.Column(db.Integer, default=0)
    hold_period_days        = db.Column(db.Integer, default=0)
    enabled                 = db.Column(db.Boolean, default=True)
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at              = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "partner_type": self.partner_type,
            "frequency": self.frequency,
            "day_of_cycle": self.day_of_cycle,
            "minimum_payout_cents": self.minimum_payout_cents,
            "minimum_payout_dollars": self.minimum_payout_cents / 100,
            "hold_period_days": self.hold_period_days,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class PayoutBatch(db.Model):
    """Groups commissions for a single payout cycle."""
    __tablename__ = "payout_batches"

    id                      = db.Column(db.Integer, primary_key=True)
    batch_number            = db.Column(db.String(50), unique=True, nullable=False,
                                        default=lambda: f"BATCH-{secrets.token_hex(6).upper()}")
    partner_type            = db.Column(db.String(50), nullable=False)
    cycle_date              = db.Column(db.DateTime, nullable=False)
    total_amount_cents      = db.Column(db.Integer, default=0)
    payout_count            = db.Column(db.Integer, default=0)
    status                  = db.Column(db.String(20), default="pending")
                                # pending/approved/rejected/paid/failed
    approved_by_admin_id    = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=True)
    approved_at             = db.Column(db.DateTime, nullable=True)
    paid_at                 = db.Column(db.DateTime, nullable=True)
    notes                   = db.Column(db.Text, nullable=True)
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    payouts                 = db.relationship("CommissionPayout", back_populates="batch", lazy="dynamic")
    approved_by_admin       = db.relationship("Admin", foreign_keys=[approved_by_admin_id])

    def to_dict(self):
        return {
            "id": self.id,
            "batch_number": self.batch_number,
            "partner_type": self.partner_type,
            "cycle_date": self.cycle_date.isoformat(),
            "total_amount_cents": self.total_amount_cents,
            "total_amount_dollars": self.total_amount_cents / 100,
            "payout_count": self.payout_count,
            "status": self.status,
            "approved_by_admin_id": self.approved_by_admin_id,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }


class CommissionPayout(db.Model):
    """Individual payout to a partner (manual approval required)."""
    __tablename__ = "commission_payouts"

    id                      = db.Column(db.Integer, primary_key=True)
    batch_id                = db.Column(db.Integer, db.ForeignKey("payout_batches.id"), nullable=False)
    partner_type            = db.Column(db.String(50), nullable=False)
    partner_id              = db.Column(db.Integer, nullable=False)  # affiliate_id, referral_partner_id, etc.
    partner_email           = db.Column(db.String(255), nullable=False)
    source_ids              = db.Column(db.String(500), nullable=True)  # JSON array of earning/referral IDs
    gross_amount_cents      = db.Column(db.Integer, nullable=False)
    payment_fee_cents       = db.Column(db.Integer, default=0)  # ACH fee, processing fee, etc.
    net_amount_cents        = db.Column(db.Integer, nullable=False)
    status                  = db.Column(db.String(20), default="pending")
                                # pending/approved/paid/rejected/failed
    payment_method          = db.Column(db.String(50), nullable=True)
                                # stripe/ach/zelle/wire
    payment_reference       = db.Column(db.String(255), nullable=True)  # ACH confirmation, wire ref, etc.
    paid_at                 = db.Column(db.DateTime, nullable=True)
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    batch                   = db.relationship("PayoutBatch", back_populates="payouts")

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "partner_type": self.partner_type,
            "partner_id": self.partner_id,
            "partner_email": self.partner_email,
            "source_ids": json.loads(self.source_ids) if self.source_ids else [],
            "gross_amount_cents": self.gross_amount_cents,
            "gross_amount_dollars": self.gross_amount_cents / 100,
            "payment_fee_cents": self.payment_fee_cents,
            "payment_fee_dollars": self.payment_fee_cents / 100,
            "net_amount_cents": self.net_amount_cents,
            "net_amount_dollars": self.net_amount_cents / 100,
            "status": self.status,
            "payment_method": self.payment_method,
            "payment_reference": self.payment_reference,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "created_at": self.created_at.isoformat(),
        }


class PaymentMethod(db.Model):
    """Stores partner payment routing details (ACH, Zelle, Wire, etc.)."""
    __tablename__ = "payment_methods"

    id                      = db.Column(db.Integer, primary_key=True)
    partner_type            = db.Column(db.String(50), nullable=False)
    partner_id              = db.Column(db.Integer, nullable=False)
    method_type             = db.Column(db.String(50), nullable=False)
                                # stripe_connect/ach/zelle/wire/check
    
    # ACH / Wire fields
    recipient_name          = db.Column(db.String(255), nullable=True)
    bank_name               = db.Column(db.String(255), nullable=True)
    account_type            = db.Column(db.String(20), nullable=True)  # checking/savings
    routing_number          = db.Column(db.String(20), nullable=True)
    account_number_last4    = db.Column(db.String(4), nullable=True)  # Last 4 digits for display
    account_number_encrypted = db.Column(db.String(500), nullable=True)  # Encrypted full account# (AES)
    
    # Zelle fields
    zelle_email_or_phone    = db.Column(db.String(255), nullable=True)
    
    # Stripe Connect
    stripe_connect_account_id = db.Column(db.String(255), nullable=True)
    
    # Status
    is_primary              = db.Column(db.Boolean, default=True)
    verified                = db.Column(db.Boolean, default=False)
    verified_at             = db.Column(db.DateTime, nullable=True)
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("partner_type", "partner_id", "method_type", name="uq_payment_method"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "partner_type": self.partner_type,
            "partner_id": self.partner_id,
            "method_type": self.method_type,
            "recipient_name": self.recipient_name,
            "bank_name": self.bank_name,
            "account_type": self.account_type,
            "account_number_last4": self.account_number_last4,
            "zelle_email_or_phone": self.zelle_email_or_phone,
            "is_primary": self.is_primary,
            "verified": self.verified,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "created_at": self.created_at.isoformat(),
        }


class PayoutLog(db.Model):
    """Immutable audit log for all payout operations."""
    __tablename__ = "payout_logs"

    id                      = db.Column(db.Integer, primary_key=True)
    batch_id                = db.Column(db.Integer, db.ForeignKey("payout_batches.id"), nullable=True)
    payout_id               = db.Column(db.Integer, db.ForeignKey("commission_payouts.id"), nullable=True)
    action                  = db.Column(db.String(50), nullable=False)
                                # batch_created/batch_approved/batch_rejected
                                # payout_calculated/payout_approved/payout_paid
                                # payment_recorded/payment_failed
    details                 = db.Column(db.Text, nullable=True)  # JSON with details
    actor_type              = db.Column(db.String(50), nullable=True)  # admin/system/partner
    actor_id                = db.Column(db.Integer, nullable=True)
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    batch                   = db.relationship("PayoutBatch", foreign_keys=[batch_id])
    payout                  = db.relationship("CommissionPayout", foreign_keys=[payout_id])

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "payout_id": self.payout_id,
            "action": self.action,
            "details": json.loads(self.details) if self.details else {},
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "created_at": self.created_at.isoformat(),
        }


# ── Guest Order Support ───────────────────────────────────────────────────────
# IMPORTANT: Communication Flow
# Jonche is the sole communicator with customers.
# - External partners (manufacturers, UPS, etc.) send data via API
# - Jonche processes and sends emails/notifications to customers
# - Suppress manufacturer emails with suppress_manufacturer_emails flag

class EmailSubscriber(db.Model):
    __tablename__ = "email_subscribers"

    id              = db.Column(db.Integer, primary_key=True)
    email           = db.Column(db.String(255), unique=True, nullable=False)
    subscribed      = db.Column(db.Boolean, default=True)
    category        = db.Column(db.String(50), default="newsletter")  # newsletter/promotional/order_updates
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "subscribed": self.subscribed,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
        }


class GuestOrderLookup(db.Model):
    """Track guest orders with public lookup token"""
    __tablename__ = "guest_order_lookup"

    id              = db.Column(db.Integer, primary_key=True)
    order_id        = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    lookup_token    = db.Column(db.String(64), unique=True, nullable=False,
                                default=lambda: secrets.token_urlsafe(32))
    guest_email     = db.Column(db.String(255), nullable=False)  # For verification
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    order           = db.relationship("Order")

    def to_dict(self):
        return {
            "lookup_token": self.lookup_token,
            "order_id": self.order_id,
            "created_at": self.created_at.isoformat(),
        }


class OrderTracking(db.Model):
    """Track order status from external fulfillment partners"""
    __tablename__ = "order_tracking"

    id              = db.Column(db.Integer, primary_key=True)
    order_id        = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    source          = db.Column(db.String(50), nullable=False)  # apliiq/manufacturer/distributor/email_parse
    status          = db.Column(db.String(50), nullable=False)  # pending/in_production/shipped/delivered
    tracking_number = db.Column(db.String(100), nullable=True)
    tracking_company = db.Column(db.String(50), nullable=True)  # UPS/FedEx/USPS
    shipping_date   = db.Column(db.DateTime, nullable=True)
    delivery_date   = db.Column(db.DateTime, nullable=True)
    metadata        = db.Column(db.Text, nullable=True)  # JSON extra data
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order           = db.relationship("Order")

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "order_id": self.order_id,
            "source": self.source,
            "status": self.status,
            "tracking_number": self.tracking_number,
            "tracking_company": self.tracking_company,
            "shipping_date": self.shipping_date.isoformat() if self.shipping_date else None,
            "delivery_date": self.delivery_date.isoformat() if self.delivery_date else None,
            "metadata": json.loads(self.metadata) if self.metadata else None,
            "created_at": self.created_at.isoformat(),
        }
