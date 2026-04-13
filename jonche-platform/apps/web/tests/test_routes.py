"""apps/web/tests/test_routes.py"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# Avoid collision with apps/api/app.py which also imports as module name "app"
# when the full test suite runs.
sys.modules.pop("app", None)
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def test_dashboard_loads(client):
    res = client.get('/')
    assert res.status_code == 200


def test_drops_page(client):
    res = client.get('/drops')
    assert res.status_code == 200


def test_retailers_page(client):
    res = client.get('/retailers')
    assert res.status_code == 200


def test_vip_page(client):
    res = client.get('/vip')
    assert res.status_code == 200


def test_analytics_page(client):
    res = client.get('/analytics')
    assert res.status_code == 200


def test_certificates_page(client):
    res = client.get('/certificates')
    assert res.status_code == 200


def test_health_check(client):
    res = client.get('/health')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'ok'
    assert data['app'] == 'jonche-web'
