"""apps/api/routes/preorders.py — Pre-order campaign endpoints (DB-backed)."""

from sqlalchemy.exc import IntegrityError
from flask import Blueprint, request, jsonify, g

from db import db
from db.models import PreOrder, Drop, Member
from middleware.auth import require_admin, require_member, decode_token, _get_token_from_request
import jwt
from services.notifications import enqueue_email

preorders_bp = Blueprint("preorders", __name__)


def _optional_member() -> Member | None:
    """Return member from JWT if present; otherwise None."""
    token = _get_token_from_request()
    if not token:
        return None
    try:
        payload = decode_token(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
    if payload.get("role") != "member":
        return None
    return Member.query.get(payload.get("sub"))


@preorders_bp.route("/", methods=["POST"])
def create_preorder():
    """
    Public endpoint to capture pre-order intent.
    If a member JWT is present and the email matches, links the preorder to the member.
    """
    data = request.get_json() or {}
    required = ["drop_id", "email", "name", "size"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    drop = Drop.query.get_or_404(int(data["drop_id"]))

    preorder = PreOrder(
        drop_id=drop.id,
        email=str(data["email"]).strip().lower(),
        name=str(data["name"]).strip(),
        size=str(data["size"]).strip(),
        deposit_cents=int(data.get("deposit_cents", 0) or 0),
        stripe_payment_intent=data.get("stripe_payment_intent"),
        status="pending",
    )

    member = _optional_member()
    if member and member.email.lower() == preorder.email:
        preorder.member_id = member.id

    db.session.add(preorder)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Already captured for this drop"}), 409

    # Email: preorder received (best-effort)
    try:
        enqueue_email(
            recipient_email=preorder.email,
            recipient_name=preorder.name,
            subject="JONCHE Preorder Received",
            body_html=f"<p>We received your preorder intent for drop <b>{drop.name}</b> (size <b>{preorder.size}</b>).</p>",
            notif_type="preorder_received",
            related_id=preorder.id,
        )
    except Exception:
        pass

    return jsonify(preorder.to_dict()), 201


@preorders_bp.route("/", methods=["GET"])
@require_admin
def list_preorders():
    drop_id = request.args.get("drop_id")
    status = request.args.get("status")
    q = PreOrder.query
    if drop_id:
        q = q.filter_by(drop_id=int(drop_id))
    if status:
        q = q.filter_by(status=status)
    rows = q.order_by(PreOrder.created_at.desc()).limit(200).all()
    return jsonify([p.to_dict() for p in rows])


@preorders_bp.route("/my", methods=["GET"])
@require_member
def my_preorders():
    rows = PreOrder.query.filter_by(member_id=g.current_member.id).order_by(
        PreOrder.created_at.desc()
    ).all()
    return jsonify([p.to_dict() for p in rows])


@preorders_bp.route("/<int:preorder_id>", methods=["PATCH"])
@require_admin
def update_preorder(preorder_id: int):
    preorder = PreOrder.query.get_or_404(preorder_id)
    data = request.get_json() or {}

    allowed = {"status", "deposit_cents", "stripe_payment_intent"}
    for k, v in data.items():
        if k not in allowed:
            continue
        if k == "deposit_cents":
            v = int(v or 0)
        setattr(preorder, k, v)

    db.session.commit()
    return jsonify(preorder.to_dict())
