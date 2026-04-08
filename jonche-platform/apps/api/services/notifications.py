"""
apps/api/services/notifications.py
Queue + send outbound email notifications.

Providers:
  - console (default): marks sent without delivering
  - sendgrid: requires SENDGRID_API_KEY
  - mailgun: requires MAILGUN_API_KEY + MAILGUN_DOMAIN

Common env:
  - NOTIFY_PROVIDER=console|sendgrid|mailgun
  - NOTIFY_FROM_EMAIL (default: no-reply@jonche.com)
  - NOTIFY_FROM_NAME  (default: JONCHE)
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from db import db
from db.models import Notification


def enqueue_email(
    *,
    recipient_email: str,
    subject: str,
    body_html: str,
    notif_type: str,
    recipient_name: str | None = None,
    related_id: int | None = None,
) -> Notification:
    n = Notification(
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        subject=subject,
        body_html=body_html,
        notif_type=notif_type,
        related_id=related_id,
        status="queued",
    )
    db.session.add(n)
    db.session.commit()
    return n


def _provider() -> str:
    return (os.getenv("NOTIFY_PROVIDER") or "console").strip().lower()


def _from_email() -> str:
    return (os.getenv("NOTIFY_FROM_EMAIL") or "no-reply@jonche.com").strip()


def _from_name() -> str:
    return (os.getenv("NOTIFY_FROM_NAME") or "JONCHE").strip()


def _send_console(n: Notification) -> None:
    # Dev-safe provider: do not deliver email, but allow queue to drain.
    n.status = "sent"
    n.sent_at = datetime.utcnow()


def _send_sendgrid(n: Notification) -> None:
    api_key = (os.getenv("SENDGRID_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("SENDGRID_API_KEY not configured")

    payload = {
        "personalizations": [{
            "to": [{"email": n.recipient_email, "name": n.recipient_name or ""}],
            "subject": n.subject,
        }],
        "from": {"email": _from_email(), "name": _from_name()},
        "content": [{"type": "text/html", "value": n.body_html}],
    }

    req = Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(req, timeout=12) as resp:  # noqa: S310 (explicit network call)
        if resp.status not in (200, 202):
            raise RuntimeError(f"SendGrid send failed: HTTP {resp.status}")
    n.status = "sent"
    n.sent_at = datetime.utcnow()


def _send_mailgun(n: Notification) -> None:
    api_key = (os.getenv("MAILGUN_API_KEY") or "").strip()
    domain = (os.getenv("MAILGUN_DOMAIN") or "").strip()
    if not api_key or not domain:
        raise RuntimeError("MAILGUN_API_KEY/MAILGUN_DOMAIN not configured")

    data = {
        "from": f"{_from_name()} <{_from_email()}>",
        "to": n.recipient_email,
        "subject": n.subject,
        "html": n.body_html,
    }
    body = urlencode(data).encode("utf-8")

    req = Request(
        f"https://api.mailgun.net/v3/{domain}/messages",
        data=body,
        headers={
            "Authorization": f"Basic {__basic_auth('api', api_key)}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urlopen(req, timeout=12) as resp:  # noqa: S310 (explicit network call)
        if resp.status not in (200, 202):
            raise RuntimeError(f"Mailgun send failed: HTTP {resp.status}")
    n.status = "sent"
    n.sent_at = datetime.utcnow()


def __basic_auth(user: str, password: str) -> str:
    import base64
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return token


def send_queued(*, limit: int = 25) -> dict:
    """
    Sends queued notifications. Returns summary counts.
    """
    provider = _provider()
    q = Notification.query.filter_by(status="queued").order_by(Notification.created_at.asc()).limit(limit).all()

    sent = 0
    failed = 0
    for n in q:
        try:
            if provider == "sendgrid":
                _send_sendgrid(n)
            elif provider == "mailgun":
                _send_mailgun(n)
            else:
                _send_console(n)
            sent += 1
        except (HTTPError, URLError, RuntimeError, Exception) as e:
            n.status = "failed"
            n.error = str(e)
            failed += 1
        finally:
            db.session.add(n)

    db.session.commit()
    return {"provider": provider, "attempted": len(q), "sent": sent, "failed": failed}

