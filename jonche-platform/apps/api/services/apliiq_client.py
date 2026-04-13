"""
apps/api/services/apliiq_client.py
Apliiq print-on-demand / fulfillment API client.

Authentication (HMAC-SHA256):
  Header: Authorization: x-apliiq-auth {RTS}:{SIG}:{APPID}:{NONCE}

  SIG = base64( HMAC-SHA256( APPID + RTS + NONCE + base64(body_or_empty), SHARED_SECRET ) )

Env vars:
  - APLIIQ_APP_KEY        (your App Key / APPID)
  - APLIIQ_SHARED_SECRET  (your Shared Secret)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


APLIIQ_API_BASE = "https://api.apliiq.com"

# Verified live endpoints (discovered via probe 2026-04):
#   GET  /api/product  → {"Products": [{Id, Code, SKU, Name, Sizes, Colors, Price, ...}]}
#   GET  /api/order    → list of order objects
#   POST /api/order    → create order
#   GET  /api/order/{id}
#   POST /api/order/{id}/cancel  (unverified — use Id from create response)


class ApliiqError(RuntimeError):
    pass


# ── Credentials ───────────────────────────────────────────────────────────────

def _app_key() -> str:
    key = os.getenv("APLIIQ_APP_KEY", "").strip()
    if not key:
        raise ApliiqError("APLIIQ_APP_KEY not configured")
    return key


def _shared_secret() -> str:
    secret = os.getenv("APLIIQ_SHARED_SECRET", "").strip()
    if not secret:
        raise ApliiqError("APLIIQ_SHARED_SECRET not configured")
    return secret


# ── Auth header builder ───────────────────────────────────────────────────────

def _build_auth_headers(body: str = "") -> dict[str, str]:
    """
    Build the Apliiq HMAC auth headers for a request.

    SIG = base64( HMAC-SHA256( APPID + RTS + NONCE + base64(body), SHARED_SECRET ) )
    Authorization: x-apliiq-auth {RTS}:{SIG}:{APPID}:{NONCE}
    """
    app_id = _app_key()
    secret = _shared_secret()

    rts = str(int(time.time()))
    nonce = uuid.uuid4().hex  # random unique string (no dashes)

    # base64-encode the request body (or empty string if no body)
    body_b64 = base64.b64encode(body.encode("utf-8")).decode("utf-8")

    # Concatenate fields in order: APPID + RTS + NONCE + base64(body)
    data = app_id + rts + nonce + body_b64

    # HMAC-SHA256 digest, then base64-encode it
    raw_sig = hmac.new(
        secret.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig = base64.b64encode(raw_sig).decode("utf-8")

    return {
        "Authorization": f"x-apliiq-auth {rts}:{sig}:{app_id}:{nonce}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


# ── Low-level request ─────────────────────────────────────────────────────────

def _request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{APLIIQ_API_BASE}{path}"
    body = json.dumps(payload) if payload is not None else ""
    headers = _build_auth_headers(body)

    body_bytes = body.encode("utf-8") if body else None
    req = Request(url, data=body_bytes, headers=headers, method=method.upper())

    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as e:
        msg = e.read().decode("utf-8", errors="ignore")
        raise ApliiqError(f"Apliiq HTTP {e.code}: {msg}") from e
    except URLError as e:
        raise ApliiqError(f"Apliiq request failed: {e}") from e


# ── Public API methods ────────────────────────────────────────────────────────

def get_products() -> list[dict[str, Any]]:
    """
    Fetch the Apliiq product catalog for this store.

    Response shape: {"Products": [{Id, Code, SKU, Name, Sizes, Colors, Price, ...}]}
    Each product's integer `Id` is used as `apliiq_product_id` on a Drop.
    Each size's integer `Id` is sent as `SizeId` on an order line item.
    Each color's integer `Id` is sent as `ColorId` on an order line item.
    """
    result = _request("GET", "/api/product")
    if isinstance(result, list):
        return result
    return result.get("Products", result.get("products", []))


def create_order(order_payload: dict[str, Any]) -> dict[str, Any]:
    """
    Submit an order to Apliiq for fulfillment.

    Apliiq order payload shape:
      {
        "ExternalId": "JNC-XXXX",          # your order_number
        "Items": [
          {
            "ProductId": 1386,             # Drop.apliiq_product_id (int)
            "ColorId":   50,               # Apliiq color Id (int)
            "SizeId":    7,                # Apliiq size Id (int)
            "Quantity":  1
          }
        ],
        "ShippingAddress": {
          "Name":     "Jane Doe",
          "Address1": "123 Main St",
          "Address2": "",
          "City":     "Los Angeles",
          "State":    "CA",
          "Zip":      "90001",
          "Country":  "US"
        }
      }
    """
    return _request("POST", "/api/order", order_payload)


def get_order(apliiq_order_id: str | int) -> dict[str, Any]:
    """Retrieve an Apliiq order by its Apliiq-assigned ID."""
    return _request("GET", f"/api/order/{apliiq_order_id}")


def list_orders(page: int = 1, per_page: int = 50) -> list[dict[str, Any]]:
    """List orders in Apliiq for this store."""
    result = _request("GET", f"/api/order?page={page}&per_page={per_page}")
    return result if isinstance(result, list) else result.get("orders", [])


def cancel_order(apliiq_order_id: str | int) -> dict[str, Any]:
    """Request cancellation of an Apliiq order."""
    return _request("POST", f"/api/order/{apliiq_order_id}/cancel", {})
