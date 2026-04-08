"""
apps/api/services/stripe_client.py
Minimal Stripe client using stdlib (no external dependencies).

Env:
  - STRIPE_SECRET_KEY
  - STRIPE_WEBHOOK_SECRET (optional but recommended)
  - STRIPE_CURRENCY (default: usd)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class StripeError(RuntimeError):
    pass


STRIPE_API_BASE = "https://api.stripe.com"


def _secret_key() -> str:
    key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not key:
        raise StripeError("STRIPE_SECRET_KEY not configured")
    return key


def _auth_header() -> str:
    # Stripe uses HTTP Basic auth with the secret key as the username and empty password,
    # but also accepts Bearer. We'll use Bearer for simplicity.
    return f"Bearer {_secret_key()}"


def _request(method: str, path: str, data: dict[str, Any] | None = None, *, idempotency_key: str | None = None) -> dict[str, Any]:
    url = f"{STRIPE_API_BASE}{path}"
    headers = {
        "Authorization": _auth_header(),
        "User-Agent": "jonche-platform/1.0",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    body = None
    if data is not None:
        encoded = urlencode(data, doseq=True).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = encoded

    req = Request(url, data=body, headers=headers, method=method.upper())
    try:
        with urlopen(req, timeout=12) as resp:
            payload = resp.read().decode("utf-8")
            return json.loads(payload) if payload else {}
    except HTTPError as e:
        msg = e.read().decode("utf-8", errors="ignore")
        raise StripeError(f"Stripe HTTP {e.code}: {msg}") from e
    except URLError as e:
        raise StripeError(f"Stripe request failed: {e}") from e


def create_payment_intent(
    *,
    amount_cents: int,
    currency: str,
    metadata: dict[str, str],
    description: str,
    receipt_email: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "amount": int(amount_cents),
        "currency": currency,
        "description": description,
        "automatic_payment_methods[enabled]": "true",
    }
    if receipt_email:
        data["receipt_email"] = receipt_email
    for k, v in (metadata or {}).items():
        data[f"metadata[{k}]"] = v
    return _request("POST", "/v1/payment_intents", data, idempotency_key=idempotency_key)


def retrieve_payment_intent(payment_intent_id: str) -> dict[str, Any]:
    return _request("GET", f"/v1/payment_intents/{payment_intent_id}")


def create_refund(*, payment_intent_id: str, amount_cents: int | None = None, reason: str | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {"payment_intent": payment_intent_id}
    if amount_cents is not None:
        data["amount"] = int(amount_cents)
    if reason:
        data["reason"] = reason
    return _request("POST", "/v1/refunds", data)


def verify_webhook_signature(payload: bytes, stripe_signature_header: str, secret: str, *, tolerance_seconds: int = 300) -> bool:
    """
    Verifies Stripe webhook signature: https://stripe.com/docs/webhooks/signatures
    """
    try:
        parts = {}
        for item in (stripe_signature_header or "").split(","):
            if "=" in item:
                k, v = item.split("=", 1)
                parts.setdefault(k.strip(), []).append(v.strip())
        timestamp = int(parts.get("t", ["0"])[0])
        signatures = parts.get("v1", [])
    except Exception:
        return False

    now = int(time.time())
    if abs(now - timestamp) > tolerance_seconds:
        return False

    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in signatures)
