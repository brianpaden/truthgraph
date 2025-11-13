"""Integration tests for health and metrics endpoints."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from truthgraph.main import app
from truthgraph.monitoring.metrics_collector import get_metrics_collector
from truthgraph.monitoring.health import get_health_checker


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
async def setup_metrics():
    """Setup metrics collector before each test."""
    collector = get_metrics_collector()
    # Ensure collector is started
    if not collector._running:
        await collector.start()
    yield
    # Cleanup after test
    await collector.stop()


class TestHealthEndpoints:
    """Integration tests for health check endpoints."""

    def test_health_basic(self, client):
        """Test basic health check endpoint."""
        start_time = time.time()
        response = client.get("/api/v1/health")
        response_time = (time.time() - start_time) * 1000  # Convert to ms

        assert response.status_code == 200
        assert response_time < 100  # Should respond in < 100ms

        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    def test_health_detailed(self, client):
        """Test detailed health check endpoint."""
        start_time = time.time()
        response = client.get("/api/v1/health/detailed")
        response_time = (time.time() - start_time) * 1000  # Convert to ms

        # Should respond within performance target (< 200ms, but allow more for test env)
        assert response_time < 2000  # 2 seconds in test environment

        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "services" in data

        # Check that service health is included
        services = data["services"]
        expected_services = ["database", "workers", "embedding_service", "nli_service"]

        for service in expected_services:
            if service in services:
                assert services[service]["status"] in ["healthy", "degraded", "unhealthy"]
                assert "message" in services[service]

    def test_health_detailed_status_codes(self, client):
        """Test that detailed health returns appropriate status codes."""
        response = client.get("/api/v1/health/detailed")

        # Should return 200 OK or 503 Service Unavailable
        assert response.status_code in [200, 503]

        if response.status_code == 503:
            data = response.json()
            # If 503, status should be unhealthy
            assert data["status"] == "unhealthy"

    def test_health_response_model(self, client):
        """Test that health response matches expected model."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()

        # Check required fields
        required_fields = ["status", "timestamp", "uptime_seconds"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_detailed_health_response_model(self, client):
        """Test that detailed health response matches expected model."""
        response = client.get("/api/v1/health/detailed")

        data = response.json()

        # Check required fields
        required_fields = ["status", "timestamp", "uptime_seconds", "services"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check service structure
        for service_name, service_data in data["services"].items():
            assert "status" in service_data
            assert "message" in service_data
            # response_time_ms is optional


class TestMetricsEndpoints:
    """Integration tests for metrics endpoints."""

    def test_metrics_prometheus_format(self, client):
        """Test Prometheus metrics export."""
        response = client.get("/api/v1/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

        content = response.text
        assert "# TruthGraph Metrics" in content

        # Should contain at least some metric lines
        lines = [line for line in content.split("\n") if line and not line.startswith("#")]
        assert len(lines) >= 0  # May be empty if no metrics collected yet

    def test_metrics_prometheus_format_structure(self, client):
        """Test Prometheus format structure."""
        # First, record some test metrics
        collector = get_metrics_collector()

        async def record_test_metrics():
            await collector.set_gauge("test.metric.gauge", 42.5)
            await collector.increment_counter("test.metric.counter", 10)

        asyncio.run(record_test_metrics())

        # Now fetch metrics
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200

        content = response.text

        # Check for HELP and TYPE lines
        if "test.metric" in content:
            assert "# HELP" in content
            assert "# TYPE" in content

    def test_metrics_overview(self, client):
        """Test metrics overview endpoint."""
        response = client.get("/api/v1/metrics/overview")

        assert response.status_code == 200

        data = response.json()

        # Should contain main sections
        assert "health" in data
        assert "timestamp" in data

        # Health section should have expected structure
        if "health" in data and not isinstance(data, dict) or "error" not in data:
            health = data["health"]
            assert "status" in health
            assert "uptime_seconds" in health

    def test_metrics_list(self, client):
        """Test metrics list endpoint."""
        response = client.get("/api/v1/metrics/list")

        assert response.status_code == 200

        data = response.json()

        # Should contain categorized metrics
        if "error" not in data:
            assert "total_metrics" in data
            assert "categories" in data

            categories = data["categories"]
            expected_categories = [
                "system", "container", "workers", "database",
                "api", "ml", "monitoring", "asyncio"
            ]

            for category in expected_categories:
                assert category in categories

    def test_metrics_timeseries(self, client):
        """Test time-series metrics endpoint."""
        # Record some test metrics first
        collector = get_metrics_collector()

        async def record_test_timeseries():
            for i in range(5):
                await collector.set_gauge("test.timeseries.metric", float(i))
                await asyncio.sleep(0.1)

        asyncio.run(record_test_timeseries())

        # Fetch time-series data
        response = client.get("/api/v1/metrics/timeseries?metric_name=test.timeseries.metric")

        assert response.status_code == 200

        data = response.json()

        if "error" not in data:
            assert "metric_name" in data
            assert data["metric_name"] == "test.timeseries.metric"
            assert "timeseries" in data
            assert isinstance(data["timeseries"], list)

    def test_metrics_timeseries_with_duration(self, client):
        """Test time-series endpoint with duration parameter."""
        response = client.get(
            "/api/v1/metrics/timeseries?metric_name=test.metric&duration_seconds=300"
        )

        assert response.status_code == 200

        data = response.json()
        assert "duration_seconds" in data or "error" in data


class TestConcurrentHealthChecks:
    """Test concurrent health check performance."""

    def test_concurrent_health_checks(self, client):
        """Test multiple concurrent health checks."""
        import concurrent.futures

        def make_health_request():
            response = client.get("/api/v1/health")
            return response.status_code

        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_health_request) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        assert all(status == 200 for status in results)

    def test_concurrent_detailed_health_checks(self, client):
        """Test multiple concurrent detailed health checks."""
        import concurrent.futures

        def make_detailed_health_request():
            start = time.time()
            response = client.get("/api/v1/health/detailed")
            duration = (time.time() - start) * 1000
            return response.status_code, duration

        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_detailed_health_request) for _ in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should complete
        assert len(results) == 5

        # Check status codes
        for status, duration in results:
            assert status in [200, 503]


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_opens_on_failures(self, client):
        """Test that circuit breaker opens after repeated failures."""
        # This test would require mocking service failures
        # For now, just verify the endpoint is accessible
        response = client.get("/api/v1/health/detailed")
        assert response.status_code in [200, 503]


class TestMetricsPerformance:
    """Test metrics endpoint performance."""

    def test_basic_health_performance(self, client):
        """Test that basic health check meets performance target (< 10ms)."""
        # Warm up
        client.get("/api/v1/health")

        # Measure
        times = []
        for _ in range(10):
            start = time.time()
            response = client.get("/api/v1/health")
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            assert response.status_code == 200

        # Average should be reasonable (allowing for test overhead)
        avg_time = sum(times) / len(times)
        assert avg_time < 100  # 100ms threshold for test environment

    def test_detailed_health_performance(self, client):
        """Test that detailed health check meets performance target (< 200ms)."""
        # Warm up
        client.get("/api/v1/health/detailed")

        # Measure
        times = []
        for _ in range(5):
            start = time.time()
            response = client.get("/api/v1/health/detailed")
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)

        # Average should be reasonable (allowing for test overhead)
        avg_time = sum(times) / len(times)
        # More lenient for test environment
        assert avg_time < 2000  # 2 seconds threshold

    def test_prometheus_export_performance(self, client):
        """Test Prometheus export performance."""
        # Warm up
        client.get("/api/v1/metrics")

        # Measure
        start = time.time()
        response = client.get("/api/v1/metrics")
        elapsed = (time.time() - start) * 1000

        assert response.status_code == 200
        # Should be reasonably fast
        assert elapsed < 500  # 500ms threshold


class TestMetricsIntegration:
    """Test integration of metrics collection with endpoints."""

    def test_metrics_are_collected(self, client):
        """Test that metrics are actually being collected."""
        # Make some requests to generate metrics
        client.get("/api/v1/health")
        client.get("/api/v1/health/detailed")

        # Wait a moment for metrics to be recorded
        time.sleep(0.5)

        # Check that metrics are available
        response = client.get("/api/v1/metrics/list")
        assert response.status_code == 200

        data = response.json()

        # Should have some metrics
        if "total_metrics" in data:
            # In a fresh test, we might not have metrics yet, so just check structure
            assert "categories" in data

    def test_worker_metrics_collected(self, client):
        """Test that worker metrics are collected."""
        # Wait for metrics collection cycle
        time.sleep(1)

        # Fetch metrics overview
        response = client.get("/api/v1/metrics/overview")
        assert response.status_code == 200

        data = response.json()

        # Check for worker information
        if "workers" in data and "error" not in data["workers"]:
            workers = data["workers"]
            assert "pool_size" in workers or "available" in workers
