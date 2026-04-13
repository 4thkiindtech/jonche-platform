/**
 * apps/web/static/js/retailer_portal.js
 * Retailer Portal with order management, inventory view, and custom orders
 */

const API = "http://localhost:5001/api";
let currentRetailer = null;
let selectedWarehouse = null;
let selectedItems = [];
let allWarehouses = [];
let allInventory = [];

// ─ Initialization ────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  await loadRetailerInfo();
  await loadWarehouses();
  await loadOrders();
  await loadInventory();
  setupEventListeners();
  loadAllocations(); // Legacy allocations
});

// ─ Event Listeners ───────────────────────────────────────────────────────

function setupEventListeners() {
  // Tab switching
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const tab = e.target.dataset.tab;
      switchTab(tab);
    });
  });

  // Order filter
  if (document.getElementById("order-filter")) {
    document.getElementById("order-filter").addEventListener("change", loadOrders);
  }
  if (document.getElementById("warehouse-filter")) {
    document.getElementById("warehouse-filter").addEventListener("change", loadInventory);
  }
  if (document.getElementById("category-filter")) {
    document.getElementById("category-filter").addEventListener("change", loadInventory);
  }

  // Custom order flow
  if (document.getElementById("add-item-btn")) {
    document.getElementById("add-item-btn").addEventListener("click", addSelectedItems);
  }
  if (document.getElementById("submit-order-btn")) {
    document.getElementById("submit-order-btn").addEventListener("click", submitCustomOrder);
  }
  if (document.getElementById("cancel-order-btn")) {
    document.getElementById("cancel-order-btn").addEventListener("click", resetOrderForm);
  }

  // Modal
  if (document.getElementById("close-modal")) {
    document.getElementById("close-modal").addEventListener("click", closeModal);
  }
}

function switchTab(tabName) {
  // Hide all tabs
  document.querySelectorAll(".tab-content").forEach((tab) => {
    tab.style.display = "none";
  });

  // Deactivate all buttons
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.remove("active");
  });

  // Show selected tab
  const tabEl = document.getElementById(`tab-${tabName}`);
  if (tabEl) {
    tabEl.style.display = "block";
  }

  // Activate button
  document.querySelector(`[data-tab="${tabName}"]`).classList.add("active");

  // Refresh data if needed
  if (tabName === "orders") loadOrders();
  if (tabName === "inventory") loadInventory();
  if (tabName === "allocations") loadAllocations();
}

// ─ API Calls ─────────────────────────────────────────────────────────────

async function loadRetailerInfo() {
  try {
    const response = await fetch("/api/retailers/me", {
      headers: { Authorization: `Bearer ${localStorage.getItem("retailer_token")}` },
    });
    const retailer = await response.json();
    currentRetailer = retailer;
    const infoEl = document.getElementById("retailer-info");
    if (infoEl) {
      infoEl.innerHTML = `
        <strong>${retailer.name}</strong><br>
        <small>${retailer.email}</small>
      `;
    }
  } catch (error) {
    console.error("Error loading retailer info:", error);
  }
}

async function loadWarehouses() {
  try {
    const response = await fetch(`${API}/warehouses`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("retailer_token")}` },
    });
    if (!response.ok) throw new Error("Failed to load warehouses");
    allWarehouses = await response.json();
    
    // Load all inventory
    for (const warehouse of allWarehouses) {
      try {
        const invResponse = await fetch(`${API}/warehouses/${warehouse.id}/inventory`);
        if (invResponse.ok) {
          const invItems = await invResponse.json();
          allInventory = allInventory.concat(invItems);
        }
      } catch (e) {
        console.error(`Error loading inventory for warehouse ${warehouse.id}:`, e);
      }
    }
    
    renderWarehouseOptions();
  } catch (error) {
    console.error("Error loading warehouses:", error);
  }
}

async function loadOrders() {
  try {
    const status = document.getElementById("order-filter")?.value;
    let url = `${API}/store-orders/my-orders`;
    if (status) url += `?status=${status}`;

    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${localStorage.getItem("retailer_token")}` },
    });
    if (!response.ok) throw new Error("Failed to load orders");
    const orders = await response.json();

    if (orders.length === 0) {
      const msgEl = document.getElementById("orders-msg");
      if (msgEl) msgEl.innerHTML = '<div class="muted">No orders found</div>';
      const listEl = document.getElementById("orders-list");
      if (listEl) listEl.innerHTML = "";
      return;
    }

    const msgEl = document.getElementById("orders-msg");
    if (msgEl) msgEl.innerHTML = "";
    const listEl = document.getElementById("orders-list");
    if (listEl) {
      listEl.innerHTML = orders
        .map((order) => renderOrderCard(order))
        .join("");

      // Add click handlers
      orders.forEach((order) => {
        document
          .querySelector(`[data-order-id="${order.id}"]`)
          ?.addEventListener("click", () => showOrderDetail(order));
      });
    }
  } catch (error) {
    console.error("Error loading orders:", error);
    const msgEl = document.getElementById("orders-msg");
    if (msgEl) msgEl.innerHTML = '<div style="color:red;">Error loading orders</div>';
  }
}

async function loadInventory() {
  try {
    const warehouseType = document.getElementById("warehouse-filter")?.value;
    let filtered = [...allInventory];

    if (warehouseType) {
      filtered = filtered.filter((item) => {
        const warehouse = allWarehouses.find((w) => w.id === item.warehouse_id);
        return warehouse?.warehouse_type === warehouseType;
      });
    }

    const category = document.getElementById("category-filter")?.value;
    if (category) {
      filtered = filtered.filter((item) => item.category === category);
    }

    if (filtered.length === 0) {
      const msgEl = document.getElementById("inventory-msg");
      if (msgEl) msgEl.innerHTML = '<div class="muted">No inventory items found</div>';
      const listEl = document.getElementById("inventory-list");
      if (listEl) listEl.innerHTML = "";
      return;
    }

    const msgEl = document.getElementById("inventory-msg");
    if (msgEl) msgEl.innerHTML = "";
    const listEl = document.getElementById("inventory-list");
    if (listEl) {
      listEl.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>SKU</th>
              <th>Name</th>
              <th>Warehouse</th>
              <th>Available</th>
              <th>Category</th>
              <th>Cost/Unit</th>
            </tr>
          </thead>
          <tbody>
            ${filtered
              .map(
                (item) => `
              <tr>
                <td><code style="background:#f0f0f0;padding:2px 4px;border-radius:2px;">${item.sku}</code></td>
                <td>${item.name}</td>
                <td>${allWarehouses.find((w) => w.id === item.warehouse_id)?.name || "Unknown"}</td>
                <td><strong>${item.quantity_available}</strong></td>
                <td>${item.category}</td>
                <td>$${(item.unit_cost_cents / 100).toFixed(2)}</td>
              </tr>
            `
              )
              .join("")}
          </tbody>
        </table>
      `;
    }
  } catch (error) {
    console.error("Error loading inventory:", error);
  }
}

// Legacy allocation loading
async function loadAllocations() {
  const root = document.getElementById('retailer-allocations');
  const msg = document.getElementById('retailer-msg');
  if (!root || !msg) return;

  msg.textContent = 'Loading…';
  try {
    const response = await fetch("/api/retailers/me/allocations");
    const allocs = await response.json();
    if (!allocs) {
      msg.textContent = 'Unable to load allocations. Please re-login.';
      return;
    }

    root.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Drop</th>
            <th>Allocated</th>
            <th>Purchased</th>
            <th>Remaining</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${allocs
            .map(
              (alloc) => `
            <tr>
              <td>${alloc.drop_name}</td>
              <td>${alloc.allocated_units}</td>
              <td>${alloc.purchased_units}</td>
              <td><strong>${alloc.remaining_units}</strong></td>
              <td><span class="status-badge status-${alloc.status}">${alloc.status}</span></td>
            </tr>
          `
            )
            .join("")}
        </tbody>
      </table>
    `;
    msg.textContent = '';
  } catch (error) {
    console.error("Error loading allocations:", error);
    msg.textContent = 'Error loading allocations';
  }
}

// ─ Render Functions ─────────────────────────────────────────────────────

function renderOrderCard(order) {
  return `
    <div class="order-card" data-order-id="${order.id}" style="cursor:pointer;">
      <div style="display:flex;justify-content:space-between;align-items:start;">
        <div>
          <h4 style="margin:0 0 8px 0;">${order.order_number}</h4>
          <p style="margin:0 0 4px 0;font-size:0.9em;color:#666;">
            <strong>${order.order_type === "custom_shoes" ? "🦶 Custom Shoes" : "👕 Apliiq"}</strong>
          </p>
          <p style="margin:0;font-size:0.85em;color:#999;">
            ${new Date(order.created_at).toLocaleDateString()}
          </p>
        </div>
        <div style="text-align:right;">
          <p style="margin:0 0 8px 0;font-size:1.1em;font-weight:600;">$${(order.total_cents / 100).toFixed(2)}</p>
          <span class="status-badge status-${order.status}">${order.status}</span>
        </div>
      </div>
      ${order.tracking_number ? `<p style="margin:8px 0 0 0;font-size:0.85em;"><strong>Tracking:</strong> ${order.tracking_number}</p>` : ""}
    </div>
  `;
}

function renderWarehouseOptions() {
  const container = document.getElementById("warehouse-options");
  if (!container) return;
  
  container.innerHTML = allWarehouses
    .map(
      (warehouse) => `
    <div class="warehouse-card" data-warehouse-id="${warehouse.id}" style="flex:1;">
      <strong>${warehouse.name}</strong><br>
      <small style="color:#666;">${warehouse.warehouse_type === "apliiq" ? "Clothing & POD" : "Custom Shoes"}</small>
    </div>
  `
    )
    .join("");

  // Add click handlers
  document.querySelectorAll(".warehouse-card").forEach((card) => {
    card.addEventListener("click", () => selectWarehouse(card));
  });
}

// ─ Custom Order Flow ────────────────────────────────────────────────────

function selectWarehouse(card) {
  // Remove previous selection
  document.querySelectorAll(".warehouse-card").forEach((c) => {
    c.classList.remove("selected");
    c.style.borderBottom = "";
  });

  // Select this warehouse
  card.classList.add("selected");
  selectedWarehouse = parseInt(card.dataset.warehouseId);
  selectedItems = [];
  updateOrderSummary();

  // Load items for this warehouse
  const warehouse = allWarehouses.find((w) => w.id === selectedWarehouse);
  const items = allInventory.filter((i) => i.warehouse_id === selectedWarehouse);

  const itemSelector = document.getElementById("item-selector");
  const noMsg = document.getElementById("no-warehouse-msg");

  if (items.length === 0) {
    if (itemSelector) itemSelector.style.display = "none";
    if (noMsg) noMsg.innerHTML = '<div class="muted">No items available in this warehouse</div>';
    return;
  }

  if (noMsg) noMsg.style.display = "none";
  if (itemSelector) itemSelector.style.display = "block";

  const itemsHtml = items
    .map(
      (item) => `
    <div class="item-row">
      <input type="checkbox" data-item-id="${item.id}" data-sku="${item.sku}" data-name="${item.name}" data-unit-price="${item.unit_cost_cents}">
      <div style="flex:1;">
        <strong>${item.name}</strong><br>
        <small style="color:#666;">SKU: ${item.sku} | Available: ${item.quantity_available}</small>
      </div>
      <div style="text-align:right;font-size:0.9em;">
        $${(item.unit_cost_cents / 100).toFixed(2)}/unit
      </div>
    </div>
  `
    )
    .join("");

  const availItemsEl = document.getElementById("available-items");
  if (availItemsEl) availItemsEl.innerHTML = itemsHtml;
}

function addSelectedItems() {
  const checkboxes = document.querySelectorAll("#available-items input[type='checkbox']:checked");

  checkboxes.forEach((checkbox) => {
    const itemId = parseInt(checkbox.dataset.itemId);
    const sku = checkbox.dataset.sku;
    const name = checkbox.dataset.name;
    const unitPrice = parseInt(checkbox.dataset.unitPrice);

    if (!selectedItems.find((item) => item.sku === sku)) {
      selectedItems.push({
        inventory_item_id: itemId,
        sku,
        name,
        unit_price_cents: unitPrice,
        quantity: 1,
      });
    }
  });

  updateOrderSummary();
  const availItemsEl = document.getElementById("available-items");
  if (availItemsEl) availItemsEl.innerHTML = "";
  const itemSelectorEl = document.getElementById("item-selector");
  if (itemSelectorEl) itemSelectorEl.style.display = "none";
}

function updateOrderSummary() {
  const summaryEl = document.getElementById("order-summary");
  if (!summaryEl) return;

  if (selectedItems.length === 0) {
    summaryEl.innerHTML = '<div class="muted">No items selected</div>';
    return;
  }

  let totalCents = 0;
  const itemsHtml = selectedItems
    .map((item) => {
      const itemTotal = item.unit_price_cents * item.quantity;
      totalCents += itemTotal;
      return `
      <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee;">
        <div>
          <strong>${item.name}</strong> (${item.sku})<br>
          <small>$${(item.unit_price_cents / 100).toFixed(2)} × 
          <input type="number" class="qty-input" data-sku="${item.sku}" value="${item.quantity}" min="1" max="100" style="width:50px;padding:4px;">
          </small>
        </div>
        <div style="font-weight:600;">$${(itemTotal / 100).toFixed(2)}</div>
      </div>
    `;
    })
    .join("");

  summaryEl.innerHTML = `
    <div style="background:#fff;border:1px solid #ddd;border-radius:4px;padding:12px;">
      ${itemsHtml}
      <div style="display:flex;justify-content:space-between;padding:12px 0;border-top:2px solid #ddd;margin-top:8px;font-size:1.1em;font-weight:600;">
        <span>Total:</span>
        <span>$${(totalCents / 100).toFixed(2)}</span>
      </div>
    </div>
  `;

  // Add quantity change handlers
  document.querySelectorAll(".qty-input").forEach((input) => {
    input.addEventListener("change", (e) => {
      const sku = e.target.dataset.sku;
      const item = selectedItems.find((i) => i.sku === sku);
      if (item) item.quantity = parseInt(e.target.value) || 1;
      updateOrderSummary();
    });
  });
}

async function submitCustomOrder() {
  if (!selectedWarehouse || selectedItems.length === 0) {
    showMessage("order-msg", "Please select a warehouse and items", "error");
    return;
  }

  const shippingName = document.getElementById("shipping-name")?.value?.trim();
  const shippingAddress = document.getElementById("shipping-address")?.value?.trim();

  if (!shippingName || !shippingAddress) {
    showMessage("order-msg", "Please enter shipping information", "error");
    return;
  }

  const payload = {
    warehouse_id: selectedWarehouse,
    order_type: allWarehouses.find((w) => w.id === selectedWarehouse)?.warehouse_type === "apliiq" ? "apliiq" : "custom_shoes",
    items: selectedItems.map((item) => ({
      inventory_item_id: item.inventory_item_id,
      quantity: item.quantity,
    })),
    shipping_name: shippingName,
    shipping_address: shippingAddress,
  };

  try {
    const response = await fetch(`${API}/store-orders/place-order`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("retailer_token")}`,
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) throw new Error("Failed to submit order");

    const order = await response.json();
    showMessage("order-msg", `Order ${order.order_number} created! Processing payment...`, "success");
    
    // Show payment modal
    setTimeout(() => {
      showPaymentModal(order);
    }, 1000);
  } catch (error) {
    console.error("Error submitting order:", error);
    showMessage("order-msg", "Error creating order", "error");
  }
}

function resetOrderForm() {
  selectedWarehouse = null;
  selectedItems = [];
  document.querySelectorAll(".warehouse-card").forEach((c) => c.classList.remove("selected"));
  const shippingNameEl = document.getElementById("shipping-name");
  if (shippingNameEl) shippingNameEl.value = "";
  const shippingAddrEl = document.getElementById("shipping-address");
  if (shippingAddrEl) shippingAddrEl.value = "";
  const orderMsgEl = document.getElementById("order-msg");
  if (orderMsgEl) orderMsgEl.innerHTML = "";
  const summaryEl = document.getElementById("order-summary");
  if (summaryEl) summaryEl.innerHTML = '<div class="muted">No items selected</div>';
  const itemSelectorEl = document.getElementById("item-selector");
  if (itemSelectorEl) itemSelectorEl.style.display = "none";
  const availItemsEl = document.getElementById("available-items");
  if (availItemsEl) availItemsEl.innerHTML = "";
}

// ─ Order Detail Modal ───────────────────────────────────────────────────

function showOrderDetail(order) {
  const modalTitle = document.getElementById("modal-title");
  const modalContent = document.getElementById("modal-content");

  if (modalTitle) modalTitle.textContent = `Order ${order.order_number}`;

  const itemsHtml = order.items
    .map(
      (item) => `
    <tr>
      <td>${item.sku}</td>
      <td>${item.name}</td>
      <td>${item.quantity}</td>
      <td>$${(item.unit_price_cents / 100).toFixed(2)}</td>
      <td>$${(item.total_cents / 100).toFixed(2)}</td>
    </tr>
  `
    )
    .join("");

  if (modalContent) {
    modalContent.innerHTML = `
      <div style="margin-bottom:16px;">
        <p><strong>Order Number:</strong> ${order.order_number}</p>
        <p><strong>Status:</strong> <span class="status-badge status-${order.status}">${order.status}</span></p>
        <p><strong>Payment Status:</strong> <span class="status-badge status-${order.payment_status}">${order.payment_status}</span></p>
        <p><strong>Type:</strong> ${order.order_type === "custom_shoes" ? "🦶 Custom Shoes" : "👕 Apliiq"}</p>
        <p><strong>Total:</strong> <strong style="font-size:1.2em;">$${(order.total_cents / 100).toFixed(2)}</strong></p>
        <p><strong>Created:</strong> ${new Date(order.created_at).toLocaleString()}</p>
        ${order.payment_completed_at ? `<p><strong>Payment Date:</strong> ${new Date(order.payment_completed_at).toLocaleString()}</p>` : ""}
        ${order.tracking_number ? `<p><strong>Tracking:</strong> ${order.tracking_number}</p>` : ""}
        ${order.invoice_url ? `<p><strong>Invoice:</strong> <a href="${order.invoice_url}" target="_blank">View Invoice</a></p>` : ""}
        ${order.status === "pending" && order.payment_status === "unpaid" ? `<button onclick="showPaymentModal(${JSON.stringify(order).replace(/"/g, '&quot;')})" style="margin-top:12px;padding:8px 16px;background:#000;color:#fff;border:none;border-radius:4px;cursor:pointer;">Pay Now</button>` : ""}
      </div>

      <h4 style="margin:16px 0 8px 0;">Items</h4>
      <table>
        <thead>
          <tr>
            <th>SKU</th>
            <th>Name</th>
            <th>Qty</th>
            <th>Unit Price</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          ${itemsHtml}
        </tbody>
      </table>

      <h4 style="margin:16px 0 8px 0;">Shipping</h4>
      <p style="margin:0;">
        <strong>${order.shipping_name}</strong><br>
        <small>${order.shipping_address}</small>
      </p>
    `;
  }

  const modal = document.getElementById("order-detail-modal");
  if (modal) modal.style.display = "flex";
}

function closeModal() {
  const modal = document.getElementById("order-detail-modal");
  if (modal) modal.style.display = "none";
}

// ─ Utility Functions ────────────────────────────────────────────────────

function showMessage(elementId, message, type) {
  const el = document.getElementById(elementId);
  if (el) {
    el.innerHTML = `<div style="color:${type === "error" ? "red" : "green"};padding:8px;border-radius:4px;">${message}</div>`;
  }
}
