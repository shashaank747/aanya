"""
Automated tests verifying frontend assets, PWA manifest, and service worker delivery.
"""
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


def test_root_index_html():
    """Verify root / serves HTML with 'Meet Aanya' title."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Meet Aanya" in response.text


def test_index_html_alias():
    """Verify /index.html serves the same welcome page."""
    response = client.get("/index.html")
    assert response.status_code == 200
    assert "Meet Aanya" in response.text


def test_pwa_manifest():
    """Verify /manifest.json is served with correct mime type and keys."""
    response = client.get("/manifest.json")
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["short_name"] == "Aanya"
    assert manifest["start_url"] == "/"
    assert manifest["display"] == "standalone"
    assert len(manifest["icons"]) >= 2


def test_service_worker():
    """Verify /service-worker.js is served and contains strict no-API cache rule."""
    response = client.get("/service-worker.js")
    assert response.status_code == 200
    assert "javascript" in response.headers.get("content-type", "")
    # Verify strict no-cache rule for API
    assert "url.pathname.startsWith('/api/')" in response.text


def test_static_assets_css_and_js():
    """Verify styles.css and app.js are served correctly and include health tracker components."""
    css_res = client.get("/static/css/styles.css")
    assert css_res.status_code == 200
    assert "health-stats-grid" in css_res.text

    js_res = client.get("/static/js/app.js")
    assert js_res.status_code == 200
    assert "checkHealth" in js_res.text
    assert "loadDailyHealthSummary" in js_res.text
    assert "loadHealthProfile" in js_res.text


def test_index_html_contains_health_tracker():
    """Verify index.html includes the Health Tracker tab, view, and modals."""
    response = client.get("/")
    assert response.status_code == 200
    assert "tabBtnHealth" in response.text
    assert "viewHealth" in response.text
    assert "healthProfileModal" in response.text
    assert "mealModal" in response.text



def test_static_icons():
    """Verify PNG and SVG icons exist and are served."""
    icon_192 = client.get("/static/icons/icon-192.png")
    assert icon_192.status_code == 200
    assert "image/png" in icon_192.headers.get("content-type", "")

    icon_svg = client.get("/static/icons/icon.svg")
    assert icon_svg.status_code == 200
