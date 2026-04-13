"""
apps/api/tests/test_api.py
Full test suite — DB-backed API with JWT auth.
Uses in-memory SQLite isolated per session.
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Avoid collision with apps/web/app.py which also imports as module name "app"
# when the full test suite runs.
sys.modules.pop("app", None)
from app import create_app
from db import db as _db
from db.models import Admin, Member, Retailer, Drop
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta


@pytest.fixture(scope="session")
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
    })
    with app.app_context():
        _db.create_all()
        _seed_db()
    yield app


def _seed_db():
    _db.session.add_all([
        Admin(email="admin@jonche.com",
              password_hash=generate_password_hash("adminpass"),
              name="Test Admin", is_superadmin=True),
        Member(email="member@jonche.com",
               password_hash=generate_password_hash("memberpass"),
               name="Test Member", tier="gold", lifetime_spend=9000.0),
        Retailer(email="retailer@kith.com",
                 password_hash=generate_password_hash("retailerpass"),
                 name="Kith NYC", tier="premier", status="active"),
        Drop(slug="test-drop", name="Test Drop 001", colorway="Black/Gold",
             sizes="8-12", price=32000, total_units=100, units_reserved=10,
             status="live", use_raffle=False, max_per_member=1,
             drop_at=datetime.utcnow() - timedelta(hours=1)),
        Drop(slug="raffle-drop", name="Raffle Drop 001", colorway="White/Silver",
             sizes="7-13", price=48000, total_units=50, units_reserved=5,
             status="upcoming", use_raffle=True, max_per_member=1,
             drop_at=datetime.utcnow() + timedelta(days=3)),
    ])
    _db.session.commit()


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def admin_token(client):
    r = client.post("/api/auth/admin/login",
                    json={"email": "admin@jonche.com", "password": "adminpass"})
    return r.get_json()["token"]


@pytest.fixture(scope="session")
def member_token(client):
    r = client.post("/api/auth/member/login",
                    json={"email": "member@jonche.com", "password": "memberpass"})
    return r.get_json()["token"]


def ah(token):
    return {"Authorization": f"Bearer {token}"}


# ── Health ────────────────────────────────────────────────────────────────────
def test_health(client):
    assert client.get("/api/health").status_code == 200


# ── Auth ──────────────────────────────────────────────────────────────────────
def test_admin_login(client):
    r = client.post("/api/auth/admin/login",
                    json={"email": "admin@jonche.com", "password": "adminpass"})
    assert r.status_code == 200
    assert r.get_json()["role"] == "admin"

def test_admin_login_bad_password(client):
    r = client.post("/api/auth/admin/login",
                    json={"email": "admin@jonche.com", "password": "wrong"})
    assert r.status_code == 401

def test_admin_me(client, admin_token):
    r = client.get("/api/auth/admin/me", headers=ah(admin_token))
    assert r.status_code == 200
    assert r.get_json()["email"] == "admin@jonche.com"

def test_member_register(client):
    r = client.post("/api/auth/member/register",
                    json={"email": "new@test.com", "password": "securepass", "name": "New User"})
    assert r.status_code == 201
    assert r.get_json()["member"]["tier"] == "bronze"

def test_member_register_duplicate(client):
    r = client.post("/api/auth/member/register",
                    json={"email": "member@jonche.com", "password": "x", "name": "Dup"})
    assert r.status_code == 409

def test_member_login(client):
    r = client.post("/api/auth/member/login",
                    json={"email": "member@jonche.com", "password": "memberpass"})
    assert r.status_code == 200

def test_member_login_wrong_password(client):
    r = client.post("/api/auth/member/login",
                    json={"email": "member@jonche.com", "password": "bad"})
    assert r.status_code == 401

def test_member_me(client, member_token):
    r = client.get("/api/auth/member/me", headers=ah(member_token))
    assert r.status_code == 200

def test_unauthenticated_route(client):
    assert client.get("/api/members/").status_code == 401

def test_member_cannot_access_admin_route(client, member_token):
    assert client.get("/api/members/", headers=ah(member_token)).status_code == 403


# ── Drops ─────────────────────────────────────────────────────────────────────
def test_list_drops(client, admin_token):
    r = client.get("/api/drops/", headers=ah(admin_token))
    assert r.status_code == 200
    assert len(r.get_json()) >= 2

def test_get_drop(client, admin_token):
    r = client.get("/api/drops/test-drop", headers=ah(admin_token))
    assert r.status_code == 200
    d = r.get_json()
    assert d["slug"] == "test-drop"
    assert "hype_pct" in d
    assert "units_available" in d

def test_get_drop_not_found(client, admin_token):
    assert client.get("/api/drops/nope", headers=ah(admin_token)).status_code == 404

def test_create_drop(client, admin_token):
    r = client.post("/api/drops/", headers=ah(admin_token), json={
        "slug": "brand-new-drop", "name": "Brand New", "colorway": "Red",
        "sizes": "8-12", "price": 40000, "total_units": 60,
    })
    assert r.status_code == 201
    assert r.get_json()["status"] == "draft"

def test_create_drop_duplicate_slug(client, admin_token):
    r = client.post("/api/drops/", headers=ah(admin_token), json={
        "slug": "test-drop", "name": "Dup", "colorway": "X",
        "sizes": "9", "price": 100, "total_units": 10,
    })
    assert r.status_code == 409

def test_create_drop_missing_field(client, admin_token):
    r = client.post("/api/drops/", headers=ah(admin_token), json={"name": "Incomplete"})
    assert r.status_code == 400

def test_update_drop(client, admin_token):
    r = client.patch("/api/drops/brand-new-drop", headers=ah(admin_token),
                     json={"description": "Updated"})
    assert r.status_code == 200
    assert r.get_json()["description"] == "Updated"

def test_publish_drop(client, admin_token):
    r = client.post("/api/drops/brand-new-drop/publish", headers=ah(admin_token))
    assert r.status_code == 200
    assert r.get_json()["status"] == "live"

def test_publish_already_live(client, admin_token):
    r = client.post("/api/drops/brand-new-drop/publish", headers=ah(admin_token))
    assert r.status_code == 400

def test_end_drop(client, admin_token):
    r = client.post("/api/drops/brand-new-drop/end", headers=ah(admin_token))
    assert r.status_code == 200
    assert r.get_json()["status"] == "ended"


# ── Members ───────────────────────────────────────────────────────────────────
def test_list_members(client, admin_token):
    r = client.get("/api/members/", headers=ah(admin_token))
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)

def test_member_count(client, admin_token):
    r = client.get("/api/members/count", headers=ah(admin_token))
    assert r.status_code == 200
    d = r.get_json()
    assert d["total"] == d["gold"] + d["silver"] + d["bronze"]

def test_member_my_profile(client, member_token):
    r = client.get("/api/members/me", headers=ah(member_token))
    assert r.status_code == 200

def test_blacklist_member(client, admin_token, app):
    with app.app_context():
        m = Member.query.filter_by(email="member@jonche.com").first()
        mid = m.id
    r = client.post(f"/api/members/{mid}/blacklist", headers=ah(admin_token),
                    json={"reason": "Test"})
    assert r.status_code == 200
    assert r.get_json()["member"]["is_blacklisted"] is True

def test_blacklisted_member_cannot_login(client):
    r = client.post("/api/auth/member/login",
                    json={"email": "member@jonche.com", "password": "memberpass"})
    assert r.status_code == 403

def test_unblacklist_member(client, admin_token, app):
    with app.app_context():
        m = Member.query.filter_by(email="member@jonche.com").first()
        mid = m.id
    r = client.post(f"/api/members/{mid}/unblacklist", headers=ah(admin_token))
    assert r.status_code == 200
    assert r.get_json()["member"]["is_blacklisted"] is False


# ── Retailers ─────────────────────────────────────────────────────────────────
def test_list_retailers(client, admin_token):
    r = client.get("/api/retailers/", headers=ah(admin_token))
    assert r.status_code == 200
    assert len(r.get_json()) >= 1

def test_invite_retailer(client, admin_token):
    r = client.post("/api/retailers/", headers=ah(admin_token), json={
        "email": "newstore@test.com", "name": "New Store",
        "password": "storepass123", "tier": "select",
    })
    assert r.status_code == 201
    assert r.get_json()["status"] == "review"

def test_invite_retailer_duplicate(client, admin_token):
    r = client.post("/api/retailers/", headers=ah(admin_token), json={
        "email": "retailer@kith.com", "name": "Kith Dup", "password": "x",
    })
    assert r.status_code == 409

def test_approve_retailer(client, admin_token, app):
    with app.app_context():
        r = Retailer.query.filter_by(email="newstore@test.com").first()
        rid = r.id
    res = client.post(f"/api/retailers/{rid}/approve", headers=ah(admin_token))
    assert res.status_code == 200
    assert res.get_json()["status"] == "active"


# ── Preorders ─────────────────────────────────────────────────────────────────
def test_create_preorder_public(client, app):
    with app.app_context():
        d = Drop.query.filter_by(slug="raffle-drop").first()
        did = d.id

    r = client.post("/api/preorders/", json={
        "drop_id": did,
        "email": "preorder@test.com",
        "name": "Pre Order",
        "size": "10",
        "deposit_cents": 0,
    })
    assert r.status_code == 201
    assert r.get_json()["email"] == "preorder@test.com"

    dup = client.post("/api/preorders/", json={
        "drop_id": did,
        "email": "preorder@test.com",
        "name": "Pre Order",
        "size": "10",
    })
    assert dup.status_code == 409


def test_list_preorders_admin(client, admin_token):
    r = client.get("/api/preorders/", headers=ah(admin_token))
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


# ── Waitlist ──────────────────────────────────────────────────────────────────
def test_enter_waitlist(client, member_token, app):
    with app.app_context():
        d = Drop.query.filter_by(slug="raffle-drop").first()
        did = d.id
    r = client.post(f"/api/waitlist/{did}/enter", headers=ah(member_token),
                    json={"size": "10"})
    assert r.status_code == 201
    assert r.get_json()["entry"]["status"] == "entered"

def test_enter_waitlist_duplicate(client, member_token, app):
    with app.app_context():
        d = Drop.query.filter_by(slug="raffle-drop").first()
        did = d.id
    r = client.post(f"/api/waitlist/{did}/enter", headers=ah(member_token),
                    json={"size": "10"})
    assert r.status_code == 409

def test_list_waitlist_entries(client, admin_token, app):
    with app.app_context():
        d = Drop.query.filter_by(slug="raffle-drop").first()
        did = d.id
    r = client.get(f"/api/waitlist/{did}/entries", headers=ah(admin_token))
    assert r.status_code == 200
    assert len(r.get_json()) >= 1

def test_run_raffle(client, admin_token, app):
    with app.app_context():
        d = Drop.query.filter_by(slug="raffle-drop").first()
        did = d.id
    r = client.post(f"/api/waitlist/{did}/draw", headers=ah(admin_token),
                    json={"winner_count": 1})
    assert r.status_code == 200
    assert "winners_count" in r.get_json()

def test_my_waitlist_entries(client, member_token):
    r = client.get("/api/waitlist/my-entries", headers=ah(member_token))
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


# ── Checkout Lock ─────────────────────────────────────────────────────────────
def test_create_checkout_lock(client, member_token, app):
    with app.app_context():
        d = Drop.query.filter_by(slug="test-drop").first()
        did = d.id
    r = client.post("/api/orders/lock", headers=ah(member_token),
                    json={"drop_id": did, "size": "10"})
    assert r.status_code == 201
    assert r.get_json()["lock"]["status"] == "active"
    assert r.get_json()["expires_in_seconds"] == 480


# ── Stats ─────────────────────────────────────────────────────────────────────
def test_stats_overview(client, admin_token):
    r = client.get("/api/stats/overview", headers=ah(admin_token))
    assert r.status_code == 200
    assert "revenue" in r.get_json()

def test_stats_requires_auth(client):
    assert client.get("/api/stats/overview").status_code == 401


# ── Analytics ─────────────────────────────────────────────────────────────────
def test_analytics_hype(client, admin_token):
    r = client.get("/api/analytics/hype", headers=ah(admin_token))
    assert r.status_code == 200
    assert all("hype_pct" in h for h in r.get_json())

def test_analytics_members(client, admin_token):
    r = client.get("/api/analytics/members", headers=ah(admin_token))
    assert r.status_code == 200
    d = r.get_json()
    assert "by_tier" in d
    assert d["total"] == sum(d["by_tier"].values())


# ── Certificates ──────────────────────────────────────────────────────────────
def test_issue_cert(client, admin_token, app):
    with app.app_context():
        d = Drop.query.filter_by(slug="test-drop").first()
        did = d.id
    r = client.post("/api/certificates/", headers=ah(admin_token),
                    json={"drop_id": did, "size": "10", "run_number": 1, "total_run": 100})
    assert r.status_code == 201
    assert "verify_token" in r.get_json()

def test_verify_cert_public(client, app):
    with app.app_context():
        from db.models import Certificate
        cert = Certificate.query.first()
        token = cert.verify_token if cert else None
    if token:
        r = client.get(f"/api/certificates/verify/{token}")
        assert r.status_code == 200
        assert r.get_json()["verified"] is True

def test_verify_invalid_cert(client):
    r = client.get("/api/certificates/verify/fake-token-xyz")
    assert r.status_code == 404

def test_cert_count(client, admin_token):
    r = client.get("/api/certificates/count", headers=ah(admin_token))
    assert r.status_code == 200
    assert "total_issued" in r.get_json()

def test_my_certs(client, member_token):
    r = client.get("/api/certificates/my-certs", headers=ah(member_token))
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


# ── QR Campaigns ──────────────────────────────────────────────────────────────
def test_create_qr_campaign(client, admin_token):
    r = client.post("/api/qr/", headers=ah(admin_token), json={
        "name": "Test QR", "destination_url": "https://jonche.com/drops/test-drop",
    })
    assert r.status_code == 201
    assert "campaign_token" in r.get_json()

def test_list_qr_campaigns(client, admin_token):
    r = client.get("/api/qr/", headers=ah(admin_token))
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


# ── Partner Applications ──────────────────────────────────────────────────────
def test_create_partner_application_public(client):
    r = client.post("/api/partners/apply", json={
        "program_type": "affiliate_creators",
        "source": "ig",
        "utm": {"utm_source": "instagram", "utm_campaign": "phase5"},
        "full_name": "Test Partner",
        "email": "partner@test.com",
        "business_name": "Test Biz",
        "phone": "555-0100",
        "website_or_social": "https://example.com",
        "city": "New York",
        "state": "NY",
        "estimated_monthly_reach": "50k",
        "network_type": "creators_media",
        "interested_in": ["referrals", "selling_products"],
        "additional_notes": "Hello",
    })
    assert r.status_code == 201
    d = r.get_json()
    assert d["program_type"] == "affiliate_creators"
    assert d["email"] == "partner@test.com"
    assert d["source"] == "ig"
    assert d["utm"]["utm_source"] == "instagram"
    assert "created_at" in d


def test_create_partner_application_missing_field(client):
    r = client.post("/api/partners/apply", json={"full_name": "X"})
    assert r.status_code == 400


def test_list_partner_applications_admin_only(client, admin_token, member_token):
    assert client.get("/api/partners/applications").status_code == 401
    assert client.get("/api/partners/applications", headers=ah(member_token)).status_code == 403
    r = client.get("/api/partners/applications", headers=ah(admin_token))
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_export_partner_applications_csv_admin_only(client, admin_token, member_token):
    assert client.get("/api/admin/exports/partner_applications.csv").status_code == 401
    assert client.get("/api/admin/exports/partner_applications.csv", headers=ah(member_token)).status_code == 403
    r = client.get("/api/admin/exports/partner_applications.csv", headers=ah(admin_token))
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/csv")
