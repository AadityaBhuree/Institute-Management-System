"""Tests for UI/UX enhancements, custom 404/500 error pages, and accessibility compliance."""

from fastapi.testclient import TestClient


def test_custom_404_html_error_page(client: TestClient):
    """Verify requesting a non-existent web URL returns custom glassmorphism 404 HTML page."""
    response = client.get("/non-existent-institutional-page", headers={"Accept": "text/html"})
    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "404 Page Not Located" in html
    assert "Resource Not Found" in html
    assert "Return to Dashboard" in html
    assert "Scholar Registry" in html


def test_api_404_remains_json(client: TestClient):
    """Verify requesting a non-existent API URL returns structured JSON response."""
    response = client.get("/api/non-existent-endpoint", headers={"Accept": "application/json"})
    assert response.status_code == 404
    assert "application/json" in response.headers["content-type"]
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Not Found"


def test_custom_500_html_error_page():
    """Verify that internal server exceptions return the 500 HTML error page for browsers."""
    from src.app import app

    @app.get("/test-trigger-internal-error")
    def trigger_error():
        raise RuntimeError("Simulated internal system fault")

    with TestClient(app, raise_server_exceptions=False) as tc:
        response = tc.get("/test-trigger-internal-error", headers={"Accept": "text/html"})
        assert response.status_code == 500
        assert "text/html" in response.headers["content-type"]
        html = response.text
        assert "500 Internal Server Disruption" in html
        assert "Institutional Server Disruption" in html
        assert "Retry Request" in html


def test_base_template_accessibility_and_mobile_elements(client: TestClient):
    """Verify that rendered HTML contains skip-link, ARIA landmarks, mobile drawer, and overlay."""
    response = client.get("/", headers={"Accept": "text/html"})
    assert response.status_code == 200
    html = response.text

    # Skip-to-content link
    assert 'class="skip-to-content"' in html
    assert 'href="#main-content"' in html

    # Mobile menu toggle button
    assert 'id="mobile-menu-toggle"' in html
    assert 'class="mobile-menu-btn"' in html
    assert 'aria-expanded="false"' in html
    assert 'aria-controls="app-sidebar"' in html

    # Mobile drawer overlay
    assert 'id="sidebar-overlay"' in html
    assert 'class="sidebar-overlay"' in html

    # Main content landmark
    assert 'id="main-content"' in html
    assert 'role="main"' in html

    # Sidebar ARIA labels
    assert 'id="app-sidebar"' in html
    assert 'aria-label="Sidebar Navigation"' in html
    assert 'aria-label="Institutional Navigation Menu"' in html


def test_static_assets_contain_phase4_styles_and_scripts(client: TestClient):
    """Verify that CSS and JS bundles serve mobile responsive rules, ARIA styles, and validation."""
    css_res = client.get("/static/css/style.css")
    assert css_res.status_code == 200
    css = css_res.text
    assert ".skip-to-content" in css
    assert ":focus-visible" in css
    assert ".form-control.is-invalid" in css
    assert ".form-error-inline" in css
    assert ".btn-loading" in css
    assert "@media (max-width: 1024px)" in css
    assert "@media (max-width: 768px)" in css

    js_res = client.get("/static/js/app.js")
    assert js_res.status_code == 200
    js = js_res.text
    assert "initMobileSidebar" in js
    assert "initFormValidationAndLoading" in js
    assert "setButtonLoading" in js
    assert "validateSingleField" in js


def test_api_500_error_returns_json():
    """Verify that unhandled server exceptions on API endpoints return structured JSON, not HTML."""
    from src.app import app

    @app.get("/api/test-server-error-probe")
    def trigger_api_fault():
        raise RuntimeError("Simulated unhandled API exception")

    with TestClient(app, raise_server_exceptions=False) as tc:
        response = tc.get("/api/test-server-error-probe", headers={"Accept": "application/json"})
        assert response.status_code == 500
        assert "application/json" in response.headers["content-type"]
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Internal server error"


def test_method_not_allowed_handling(client: TestClient):
    """Verify that using an unsupported HTTP method returns 405 Method Not Allowed."""
    # DELETE to GET-only health check endpoint
    res = client.delete("/api/health")
    assert res.status_code == 405
