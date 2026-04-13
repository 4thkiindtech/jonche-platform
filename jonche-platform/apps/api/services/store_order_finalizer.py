"""apps/api/services/store_order_finalizer.py — Finalize store orders after payment confirmation."""

from datetime import datetime
from db import db
from db.models import StoreOrder, InventoryItem, Notification


def finalize_store_order(store_order: "StoreOrder") -> None:
    """
    Finalize a store order after payment is confirmed.
    
    Updates:
    - Order status to 'confirmed'
    - Payment status to 'paid'
    - Deduct quantities from inventory (convert reserved to actual purchase)
    """
    store_order.status = "confirmed"
    store_order.payment_status = "paid"
    store_order.payment_completed_at = datetime.utcnow()
    
    # Deduct from inventory
    for item in store_order.items:
        if item.inventory_item_id:
            inv = InventoryItem.query.get(item.inventory_item_id)
            if inv:
                # Inventory was already reserved, just confirm it's purchased
                inv.quantity_reserved -= item.quantity
                # Total quantity already includes this, so no change to quantity_total
    
    db.session.commit()
    
    # Send confirmation email
    _send_payment_confirmation_email(store_order)


def mark_store_order_payment_failed(store_order: "StoreOrder", reason: str = None) -> None:
    """Mark a store order payment as failed and release inventory hold."""
    store_order.payment_status = "failed"
    
    # Release reserved inventory
    for item in store_order.items:
        if item.inventory_item_id:
            inv = InventoryItem.query.get(item.inventory_item_id)
            if inv:
                inv.quantity_reserved -= item.quantity
                inv.quantity_available += item.quantity
    
    db.session.commit()
    
    # Send failure notification
    _send_payment_failed_email(store_order, reason)


def _send_payment_confirmation_email(store_order: "StoreOrder") -> None:
    """Send payment confirmation email to retailer."""
    retailer = store_order.retailer
    if not retailer:
        return
    
    items_html = "".join([
        f"""
        <tr>
          <td>{item.name}</td>
          <td>{item.quantity}</td>
          <td>${item.unit_price_cents / 100:.2f}</td>
          <td>${item.quantity * item.unit_price_cents / 100:.2f}</td>
        </tr>
        """ for item in store_order.items
    ])
    
    body_html = f"""
    <h2>Order Confirmed: {store_order.order_number}</h2>
    <p>Your payment has been received and your order is confirmed.</p>
    
    <h3>Order Summary</h3>
    <table border="1" cellpadding="10" style="border-collapse: collapse;">
      <thead>
        <tr>
          <th>Item</th>
          <th>Qty</th>
          <th>Unit Price</th>
          <th>Total</th>
        </tr>
      </thead>
      <tbody>
        {items_html}
        <tr style="font-weight: bold; border-top: 2px solid #000;">
          <td colspan="3">TOTAL</td>
          <td>${store_order.total_cents / 100:.2f}</td>
        </tr>
      </tbody>
    </table>
    
    <h3>Shipping Address</h3>
    <p>
      {store_order.shipping_name}<br>
      {store_order.shipping_address}
    </p>
    
    <p>Your order will be fulfilled shortly. You'll receive tracking information when it ships.</p>
    """
    
    notification = Notification(
        recipient_email=retailer.email,
        recipient_name=retailer.name,
        subject=f"Payment Confirmed: Order {store_order.order_number}",
        body_html=body_html,
        notif_type="store_order_payment_confirmed",
        related_id=store_order.id,
    )
    
    db.session.add(notification)
    db.session.commit()


def _send_payment_failed_email(store_order: "StoreOrder", reason: str = None) -> None:
    """Send payment failed notification to retailer."""
    retailer = store_order.retailer
    if not retailer:
        return
    
    reason_text = reason or "Please try again or contact support."
    
    body_html = f"""
    <h2>Payment Failed: {store_order.order_number}</h2>
    <p>We were unable to process your payment.</p>
    
    <h3>Reason</h3>
    <p>{reason_text}</p>
    
    <h3>What Happens Now</h3>
    <p>Your order has been cancelled and your inventory has been released. You can place a new order or retry payment at any time.</p>
    
    <p>If you need assistance, please contact support.</p>
    """
    
    notification = Notification(
        recipient_email=retailer.email,
        recipient_name=retailer.name,
        subject=f"Payment Failed: Order {store_order.order_number}",
        body_html=body_html,
        notif_type="store_order_payment_failed",
        related_id=store_order.id,
    )
    
    db.session.add(notification)
    db.session.commit()
