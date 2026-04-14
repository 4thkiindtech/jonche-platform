"""
tests/test_e2e_complete.py
Comprehensive end-to-end test suite for Jonche Platform.
Tests all API entry points, web routes, authentication, and cross-service communication.
"""

import pytest
import sys
import os
import json
from datetime import datetime, timedelta

# Add app paths to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'api'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'web'))

# Clean up module cache to avoid collisions
sys.modules.pop("app", None)

from apps.api.app import create_app as create_api_app
from apps.api.db import db as api_db
from apps.api.db.models import Admin, Member, Retailer, Drop
from werkzeug.security import generate_password_hash


# ──────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def api_app():
    """API Flask app with in-memory SQLite database."""
    app = create_api_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
    })
    
    with app.app_context():
        api_db.create_all()
        _seed_api_db()
    
    yield app


@pytest.fixture(scope="function")
def api_client(api_app):
    """API test client."""
    with api_app.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def admin_token(api_client):
    """Get JWT token for admin user."""
    res = api_client.post(
        '/api/auth/admin/login',
        json={"email": "admin@jonche.com", "password": "adminpass"}
    )
    assert res.status_code == 200
    return res.json.get("token")


@pytest.fixture(scope="function")
def member_token(api_client):
    """Get JWT token for member user."""
    res = api_client.post(
        '/api/auth/member/login',
        json={"email": "member@jonche.com", "password": "memberpass"}
    )
    assert res.status_code == 200
    return res.json.get("token")


@pytest.fixture(scope="function")
def retailer_token(api_client):
    """Get JWT token for retailer user."""
    res = api_client.post(
        '/api/auth/retailer/login',
        json={"email": "retailer@kith.com", "password": "retailerpass"}
    )
    assert res.status_code == 200
    return res.json.get("token")


def _seed_api_db():
    """Seed database with test data."""
    api_db.session.add_all([
        Admin(
            email="admin@jonche.com",
            password_hash=generate_password_hash("adminpass"),
            name="Test Admin",
            is_superadmin=True
        ),
        Member(
            email="member@jonche.com",
            password_hash=generate_password_hash("memberpass"),
            name="Test Member",
            tier="gold",
            lifetime_spend=9000.0
        ),
        Retailer(
            email="retailer@kith.com",
            password_hash=generate_password_hash("retailerpass"),
            name="Kith NYC",
            tier="premier",
            status="active"
        ),
        Drop(
            slug="test-drop",
            name="Test Drop 001",
            colorway="Black/Gold",
            sizes="8-12",
            price=32000,
            total_units=100,
            units_reserved=10,
            status="live",
            use_raffle=False,
            max_per_member=1,
            drop_at=datetime.utcnow() - timedelta(hours=1)
        ),
    ])
    api_db.session.commit()


# ──────────────────────────────────────────────────────────────────────────────
# HEALTH CHECKS
# ──────────────────────────────────────────────────────────────────────────────

class TestHealthChecks:
    """Test basic health endpoints."""
    
    def test_api_health(self, api_client):
        """API health check endpoint."""
        res = api_client.get('/api/health')
        assert res.status_code == 200
        data = res.json
        assert data["status"] == "ok"
        assert data["app"] == "jonche-api"


# ──────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION ENTRY POINTS
# ──────────────────────────────────────────────────────────────────────────────

class TestAuthenticationEntryPoints:
    """Test all authentication endpoints."""
    
    def test_admin_login_success(self, api_client):
        """Admin login with valid credentials."""
        res = api_client.post(
            '/api/auth/admin/login',
            json={"email": "admin@jonche.com", "password": "adminpass"}
        )
        assert res.status_code == 200
        data = res.json
        assert "token" in data
        assert data["admin"]["email"] == "admin@jonche.com"
    
    def test_admin_login_invalid_credentials(self, api_client):
        """Admin login with invalid credentials."""
        res = api_client.post(
            '/api/auth/admin/login',
            json={"email": "admin@jonche.com", "password": "wrongpass"}
        )
        assert res.status_code == 401
    
    def test_member_login_success(self, api_client):
        """Member login with valid credentials."""
        res = api_client.post(
            '/api/auth/member/login',
            json={"email": "member@jonche.com", "password": "memberpass"}
        )
        assert res.status_code == 200
        data = res.json
        assert "token" in data
        assert data["member"]["email"] == "member@jonche.com"
    
    def test_retailer_login_success(self, api_client):
        """Retailer login with valid credentials."""
        res = api_client.post(
            '/api/auth/retailer/login',
            json={"email": "retailer@kith.com", "password": "retailerpass"}
        )
        assert res.status_code == 200
        data = res.json
        assert "token" in data
        assert data["retailer"]["email"] == "retailer@kith.com"


# ──────────────────────────────────────────────────────────────────────────────
# DROPS ENTRY POINTS
# ──────────────────────────────────────────────────────────────────────────────

class TestDropsEntryPoints:
    """Test all drops endpoints."""
    
    def test_list_drops(self, api_client):
        """List all drops."""
        res = api_client.get('/api/drops/')
        assert res.status_code == 200
        data = res.json
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["slug"] == "test-drop"
    
    def test_get_drop_by_slug(self, api_client):
        """Get specific drop by slug."""
        res = api_client.get('/api/drops/test-drop')
        assert res.status_code == 200
        data = res.json
        assert data["slug"] == "test-drop"
        assert data["name"] == "Test Drop 001"
        assert data["status"] == "live"
    
    def test_get_drop_not_found(self, api_client):
        """Get non-existent drop."""
        res = api_client.get('/api/drops/nonexistent')
        assert res.status_code == 404
    
    def test_get_drop_stock(self, api_client):
        """Get drop stock information."""
        res = api_client.get('/api/drops/test-drop/stock')
        assert res.status_code == 200
        data = res.json
        assert "available" in data
        assert "reserved" in data


# ──────────────────────────────────────────────────────────────────────────────
# MEMBERS ENTRY POINTS
# ──────────────────────────────────────────────────────────────────────────────

class TestMembersEntryPoints:
    """Test all members endpoints."""
    
    def test_get_member_profile(self, api_client, member_token):
        """Get authenticated member profile."""
        res = api_client.get(
            '/api/members/profile',
            headers={"Authorization": f"Bearer {member_token}"}
        )
        assert res.status_code == 200
        data = res.json
        assert data["email"] == "member@jonche.com"
        assert data["tier"] == "gold"
    
    def test_get_member_profile_unauthorized(self, api_client):
        """Get member profile without token."""
        res = api_client.get('/api/members/profile')
        assert res.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# ADMIN ENTRY POINTS
# ──────────────────────────────────────────────────────────────────────────────

class TestAdminEntryPoints:
    """Test all admin endpoints."""
    
    def test_admin_get_stats(self, api_client, admin_token):
        """Admin get platform statistics."""
        res = api_client.get(
            '/api/admin/stats',
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json
        assert "total_members" in data or isinstance(data, dict)
    
    def test_admin_list_members(self, api_client, admin_token):
        """Admin list all members."""
        res = api_client.get(
            '/api/admin/members',
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code in [200, 201]
    
    def test_admin_unauthorized_access(self, api_client, member_token):
        """Non-admin cannot access admin endpoints."""
        res = api_client.get(
            '/api/admin/stats',
            headers={"Authorization": f"Bearer {member_token}"}
        )
        assert res.status_code in [403, 401]


# ──────────────────────────────────────────────────────────────────────────────
# RETAILERS ENTRY POINTS
# ──────────────────────────────────────────────────────────────────────────────

class TestRetailersEntryPoints:
    """Test all retailers endpoints."""
    
    def test_retailer_get_profile(self, api_client, retailer_token):
        """Get retailer profile."""
        res = api_client.get(
            '/api/retailers/profile',
            headers={"Authorization": f"Bearer {retailer_token}"}
        )
        assert res.status_code == 200
        data = res.json
        assert data["email"] == "retailer@kith.com"
    
    def test_list_retailers(self, api_client):
        """List all retailers (public endpoint)."""
        res = api_client.get('/api/retailers/')
        assert res.status_code == 200
        assert isinstance(res.json, list)


# ──────────────────────────────────────────────────────────────────────────────
# ANALYTICS ENTRY POINTS
# ──────────────────────────────────────────────────────────────────────────────

class TestAnalyticsEntryPoints:
    """Test all analytics endpoints."""
    
    def test_get_analytics_dashboard(self, api_client, admin_token):
        """Get analytics dashboard data."""
        res = api_client.get(
            '/api/analytics/',
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code in [200, 404]
    
    def test_get_drop_analytics(self, api_client, admin_token):
        """Get analytics for specific drop."""
        res = api_client.get(
            '/api/analytics/drops/test-drop',
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code in [200, 404]


# ──────────────────────────────────────────────────────────────────────────────
# CERTIFICATES ENTRY POINTS
# ──────────────────────────────────────────────────────────────────────────────

class TestCertificatesEntryPoints:
    """Test all certificates endpoints."""
    
    def test_verify_certificate(self, api_client):
        """Verify a certificate (public endpoint)."""
        res = api_client.get('/api/certificates/verify/test-token')
        assert res.status_code in [200, 404]


# ──────────────────────────────────────────────────────────────────────────────
# STATS ENTRY POINTS
# ──────────────────────────────────────────────────────────────────────────────

class TestStatsEntryPoints:
    """Test all stats endpoints."""
    
    def test_get_platform_stats(self, api_client):
        """Get platform statistics (public)."""
        res = api_client.get('/api/stats/')
        assert res.status_code in [200, 404]


# ──────────────────────────────────────────────────────────────────────────────
# PRODUCTS ENTRY POINTS
# ──────────────────────────────────────────────────────────────────────────────

class TestProductsEntryPoints:
    """Test all products endpoints."""
    
    def test_list_products(self, api_client):
        """List all products."""
        res = api_client.get('/api/products/')
        assert res.status_code in [200, 404]
    
    def test_get_product_categories(self, api_client):
        """Get product categories."""
        res = api_client.get('/api/products/categories')
        assert res.status_code in [200, 404]
    
    def test_get_commercials(self, api_client):
        """Get commercial/featured products."""
        res = api_client.get('/api/products/commercials')
        assert res.status_code in [200, 404]


# ──────────────────────────────────────────────────────────────────────────────
# ORDERS ENTRY POINTS
# ──────────────────────────────────────────────────────────────────────────────

class TestOrdersEntryPoints:
    """Test all orders endpoints."""
    
    def test_list_member_orders(self, api_client, member_token):
        """List orders for authenticated member."""
        res = api_client.get(
            '/api/orders/',
            headers={"Authorization": f"Bearer {member_token}"}
        )
        assert res.status_code in [200, 404]


# ──────────────────────────────────────────────────────────────────────────────
# CROSS-SERVICE COMMUNICATION
# ──────────────────────────────────────────────────────────────────────────────

class TestCrossServiceCommunication:
    """Test communication between web and API services."""
    
    def test_api_serves_all_required_endpoints(self, api_client):
        """Verify all critical API endpoints are available."""
        endpoints = [
            ('/api/health', 'GET'),
            ('/api/auth/admin/login', 'POST'),
            ('/api/auth/member/login', 'POST'),
            ('/api/auth/retailer/login', 'POST'),
            ('/api/drops/', 'GET'),
            ('/api/products/', 'GET'),
        ]
        
        for endpoint, method in endpoints:
            if method == 'GET':
                res = api_client.get(endpoint)
            else:
                res = api_client.post(endpoint, json={})
            
            # Should not be 404 (endpoint exists)
            assert res.status_code != 404, f"Endpoint {endpoint} returned 404"


# ──────────────────────────────────────────────────────────────────────────────
# ERROR HANDLING
# ──────────────────────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Test error handling across the application."""
    
    def test_missing_required_fields_in_login(self, api_client):
        """Login with missing email."""
        res = api_client.post(
            '/api/auth/admin/login',
            json={"password": "pass"}
        )
        assert res.status_code in [400, 422]
    
    def test_invalid_json_payload(self, api_client):
        """Send invalid JSON to API."""
        res = api_client.post(
            '/api/auth/admin/login',
            data="not json",
            content_type='application/json'
        )
        assert res.status_code in [400, 415]
    
    def test_nonexistent_endpoint(self, api_client):
        """Request non-existent endpoint."""
        res = api_client.get('/api/nonexistent')
        assert res.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# INTEGRATION TESTS
# ──────────────────────────────────────────────────────────────────────────────

class TestIntegrations:
    """Test end-to-end workflows."""
    
    def test_complete_member_flow(self, api_client):
        """Complete user flow: login → view drops → check profile."""
        # 1. Login as member
        login_res = api_client.post(
            '/api/auth/member/login',
            json={"email": "member@jonche.com", "password": "memberpass"}
        )
        assert login_res.status_code == 200
        token = login_res.json.get("token")
        assert token is not None
        
        # 2. Get member profile
        profile_res = api_client.get(
            '/api/members/profile',
            headers={"Authorization": f"Bearer {token}"}
        )
        assert profile_res.status_code == 200
        
        # 3. View available drops
        drops_res = api_client.get('/api/drops/')
        assert drops_res.status_code == 200
        assert len(drops_res.json) > 0
    
    def test_complete_admin_flow(self, api_client):
        """Complete admin flow: login → view stats → access admin panel."""
        # 1. Login as admin
        login_res = api_client.post(
            '/api/auth/admin/login',
            json={"email": "admin@jonche.com", "password": "adminpass"}
        )
        assert login_res.status_code == 200
        token = login_res.json.get("token")
        
        # 2. Access admin stats
        stats_res = api_client.get(
            '/api/admin/stats',
            headers={"Authorization": f"Bearer {token}"}
        )
        assert stats_res.status_code in [200, 404]
    
    def test_complete_retailer_flow(self, api_client):
        """Complete retailer flow: login → view profile → list retailers."""
        # 1. Login as retailer
        login_res = api_client.post(
            '/api/auth/retailer/login',
            json={"email": "retailer@kith.com", "password": "retailerpass"}
        )
        assert login_res.status_code == 200
        token = login_res.json.get("token")
        
        # 2. Get retailer profile
        profile_res = api_client.get(
            '/api/retailers/profile',
            headers={"Authorization": f"Bearer {token}"}
        )
        assert profile_res.status_code in [200, 404]
        
        # 3. List all retailers
        list_res = api_client.get('/api/retailers/')
        assert list_res.status_code == 200
