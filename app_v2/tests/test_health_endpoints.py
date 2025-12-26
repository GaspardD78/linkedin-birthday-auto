"""
Integration tests for health check endpoints.

Tests cover:
- /health (liveness probe)
- /ready (readiness probe)
- Health check response structure
- Error handling
"""

import pytest
from fastapi.testclient import TestClient
from app_v2.main import app


@pytest.mark.integration
class TestHealthEndpoint:
    """Test /health liveness probe endpoint."""

    def test_health_endpoint_returns_200(self):
        """Test that /health endpoint returns 200 OK."""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200

    def test_health_endpoint_returns_valid_structure(self):
        """Test that /health response has correct structure."""
        client = TestClient(app)
        response = client.get("/health")

        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data

        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"

    def test_health_endpoint_timestamp_format(self):
        """Test that timestamp is ISO 8601 format."""
        client = TestClient(app)
        response = client.get("/health")

        data = response.json()
        timestamp = data["timestamp"]

        # Should be parseable as ISO 8601
        from datetime import datetime
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("Timestamp is not valid ISO 8601 format")

    def test_health_endpoint_is_fast(self):
        """Test that /health endpoint responds quickly."""
        client = TestClient(app)

        import time
        start = time.time()
        response = client.get("/health")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 1.0, "Health check took too long"


@pytest.mark.integration
class TestReadyEndpoint:
    """Test /ready readiness probe endpoint."""

    def test_ready_endpoint_returns_200_or_503(self):
        """Test that /ready endpoint returns 200 or 503."""
        client = TestClient(app)
        response = client.get("/ready")

        # Should be either ready (200) or not ready (503)
        assert response.status_code in [200, 503]

    def test_ready_endpoint_returns_valid_structure(self):
        """Test that /ready response has correct structure."""
        client = TestClient(app)
        response = client.get("/ready")

        data = response.json()

        # Required fields
        assert "status" in data
        assert "database" in data
        assert "redis" in data
        assert "dependencies" in data
        assert "timestamp" in data
        assert "version" in data

        # Status should be "ready" or "not_ready"
        assert data["status"] in ["ready", "not_ready"]

    def test_ready_endpoint_database_check(self):
        """Test that /ready checks database connectivity."""
        client = TestClient(app)
        response = client.get("/ready")

        data = response.json()

        # Database check should be present
        assert "database" in data
        db_status = data["database"]

        # Should be either "ok" or have error message
        if db_status != "ok":
            assert "error" in db_status.lower()

    def test_ready_endpoint_redis_check_optional(self):
        """Test that /ready treats Redis as optional."""
        client = TestClient(app)
        response = client.get("/ready")

        data = response.json()

        # Redis can be either ok or unavailable (not a blocking issue)
        assert data["redis"] in ["ok", "unavailable"]

        # Endpoint should still return 200 if database is ok
        if data["database"] == "ok":
            assert response.status_code == 200

    def test_ready_endpoint_timestamp_format(self):
        """Test that timestamp is ISO 8601 format."""
        client = TestClient(app)
        response = client.get("/ready")

        data = response.json()
        timestamp = data["timestamp"]

        # Should be parseable as ISO 8601
        from datetime import datetime
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("Timestamp is not valid ISO 8601 format")

    def test_ready_endpoint_dependencies_list(self):
        """Test that /ready includes dependencies list."""
        client = TestClient(app)
        response = client.get("/ready")

        data = response.json()

        # Dependencies should be a list
        assert isinstance(data["dependencies"], list)

        # Database should be in dependencies if ok
        if data["database"] == "ok":
            assert "database" in data["dependencies"]


@pytest.mark.integration
class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint_returns_200(self):
        """Test that root endpoint returns 200 OK."""
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200

    def test_root_endpoint_has_docs_link(self):
        """Test that root endpoint points to documentation."""
        client = TestClient(app)
        response = client.get("/")

        data = response.json()
        assert "docs" in data
        assert data["docs"] == "/docs"

    def test_root_endpoint_has_version(self):
        """Test that root endpoint includes version."""
        client = TestClient(app)
        response = client.get("/")

        data = response.json()
        assert "version" in data
        assert data["version"] == "2.0.0"


@pytest.mark.integration
class TestHealthCheckIntegration:
    """Integration tests for health checks together."""

    def test_both_endpoints_consistent_versions(self):
        """Test that all endpoints report same version."""
        client = TestClient(app)

        root = client.get("/").json()
        health = client.get("/health").json()
        ready = client.get("/ready").json()

        assert root["version"] == health["version"] == ready["version"] == "2.0.0"

    def test_endpoints_availability(self):
        """Test that all health check endpoints are available."""
        client = TestClient(app)

        endpoints = ["/", "/health", "/ready"]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 503], f"Endpoint {endpoint} not available"
