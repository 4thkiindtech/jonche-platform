/**
 * apps/web/static/js/stripe-checkout.js
 * Stripe payment processing for store orders
 */

let stripe = null;
let elements = null;

// Load Stripe (requires STRIPE_PUBLIC_KEY to be available globally)
async function initializeStripe() {
  if (!window.STRIPE_PUBLIC_KEY) {
    console.error("STRIPE_PUBLIC_KEY not configured");
    return false;
  }

  stripe = Stripe(window.STRIPE_PUBLIC_KEY);
  elements = stripe.elements();
  return true;
}

/**
 * Show payment modal for a store order
 * @param {Object} order - The store order object
 */
async function showPaymentModal(order) {
  if (!stripe) {
    const initialized = await initializeStripe();
    if (!initialized) {
      showMessage("payment-msg", "Payment system not configured", "error");
      return;
    }
  }

  const modal = document.getElementById("payment-modal");
  if (!modal) {
    console.error("Payment modal element not found");
    return;
  }

  const titleEl = document.getElementById("payment-modal-title");
  if (titleEl) {
    titleEl.textContent = `Pay for Order ${order.order_number}`;
  }

  const amountEl = document.getElementById("payment-amount");
  if (amountEl) {
    amountEl.textContent = `$${(order.total_cents / 100).toFixed(2)}`;
  }

  const orderIdInput = document.getElementById("payment-order-id");
  if (orderIdInput) {
    orderIdInput.value = order.id;
  }

  // Create fresh card element
  const cardContainer = document.getElementById("card-element");
  if (cardContainer) {
    cardContainer.innerHTML = ""; // Clear previous card
    const cardElement = elements.create("card");
    cardElement.mount("#card-element");
  }

  // Show modal
  modal.style.display = "flex";
}

async function processPayment(event) {
  event.preventDefault();

  if (!stripe || !elements) {
    showMessage("payment-msg", "Payment system not initialized", "error");
    return;
  }

  const orderId = document.getElementById("payment-order-id").value;
  if (!orderId) {
    showMessage("payment-msg", "Order ID missing", "error");
    return;
  }

  const submitBtn = document.getElementById("payment-submit-btn");
  if (submitBtn) submitBtn.disabled = true;

  try {
    // Create payment intent
    const response = await fetch(`/api/store-orders/${orderId}/payment-intent`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("retailer_token")}`,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to create payment intent");
    }

    const { client_secret } = await response.json();

    // Get card element
    const cardElement = elements.getElement("card");

    // Confirm card payment
    const result = await stripe.confirmCardPayment(client_secret, {
      payment_method: {
        card: cardElement,
        billing_details: {
          name: document.getElementById("cardholder-name")?.value || "",
        },
      },
    });

    if (result.error) {
      showMessage("payment-msg", result.error.message, "error");
      if (submitBtn) submitBtn.disabled = false;
    } else if (result.paymentIntent.status === "succeeded") {
      showMessage("payment-msg", "Payment successful! Order confirmed.", "success");

      setTimeout(() => {
        closePaymentModal();
        loadOrders();
        switchTab("orders");
      }, 1500);
    } else {
      showMessage("payment-msg", `Payment status: ${result.paymentIntent.status}`, "info");
      if (submitBtn) submitBtn.disabled = false;
    }
  } catch (error) {
    console.error("Payment error:", error);
    showMessage("payment-msg", error.message, "error");
    if (submitBtn) submitBtn.disabled = false;
  }
}

function closePaymentModal() {
  const modal = document.getElementById("payment-modal");
  if (modal) modal.style.display = "none";
}

function showMessage(elementId, message, type = "info") {
  const el = document.getElementById(elementId);
  if (!el) return;

  el.innerHTML = `<div class="message message-${type}">${message}</div>`;
  el.style.display = "block";
}
