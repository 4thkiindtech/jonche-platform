# Guest Order Support ────────────────────────────────────────────────────────

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
