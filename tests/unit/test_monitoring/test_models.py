"""Unit tests for monitoring data models."""

import time
from datetime import datetime

import pytest
from pydantic import ValidationError

from truthgraph.monitoring.storage.models import (
    DetailedHealthResponse,
    HealthResponse,
    HealthStatus,
    MetricType,
    MetricValue,
    ServiceHealth,
)


class TestMetricType:
    """Test MetricType enum."""

    def test_metric_types(self):
        """Test all metric type values."""
        assert MetricType.COUNTER == "counter"
        assert MetricType.GAUGE == "gauge"
        assert MetricType.HISTOGRAM == "histogram"


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_health_statuses(self):
        """Test all health status values."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"


class TestMetricValue:
    """Test MetricValue dataclass."""

    def test_metric_value_creation(self):
        """Test creating a metric value."""
        timestamp = time.time()
        metric = MetricValue(timestamp=timestamp, value=42.5)

        assert metric.timestamp == timestamp
        assert metric.value == 42.5
        assert metric.labels is None

    def test_metric_value_with_labels(self):
        """Test creating a metric value with labels."""
        timestamp = time.time()
        labels = {"endpoint": "/verify", "method": "POST"}
        metric = MetricValue(timestamp=timestamp, value=100.0, labels=labels)

        assert metric.timestamp == timestamp
        assert metric.value == 100.0
        assert metric.labels == labels

    def test_metric_value_frozen(self):
        """Test that MetricValue is immutable (frozen)."""
        metric = MetricValue(timestamp=time.time(), value=42.5)

        with pytest.raises(AttributeError):
            metric.value = 100.0

    def test_metric_value_slots(self):
        """Test that MetricValue uses __slots__ for memory efficiency."""
        metric = MetricValue(timestamp=time.time(), value=42.5)

        # Frozen dataclass prevents adding new attributes
        # In Python 3.13, the error type may differ, but it should still raise
        with pytest.raises((AttributeError, TypeError)):
            metric.new_attribute = "test"


class TestHealthResponse:
    """Test HealthResponse Pydantic model."""

    def test_health_response_creation(self):
        """Test creating a basic health response."""
        response = HealthResponse(status="healthy", uptime_seconds=3600)

        assert response.status == "healthy"
        assert response.uptime_seconds == 3600
        assert isinstance(response.timestamp, datetime)

    def test_health_response_validation_status(self):
        """Test status validation (only allows healthy/degraded/unhealthy)."""
        # Valid statuses
        HealthResponse(status="healthy", uptime_seconds=100)
        HealthResponse(status="degraded", uptime_seconds=100)
        HealthResponse(status="unhealthy", uptime_seconds=100)

        # Invalid status
        with pytest.raises(ValidationError):
            HealthResponse(status="invalid", uptime_seconds=100)

    def test_health_response_validation_uptime(self):
        """Test uptime validation (must be >= 0)."""
        # Valid uptime
        HealthResponse(status="healthy", uptime_seconds=0)
        HealthResponse(status="healthy", uptime_seconds=1000)

        # Invalid uptime
        with pytest.raises(ValidationError):
            HealthResponse(status="healthy", uptime_seconds=-1)

    def test_health_response_json_serialization(self):
        """Test JSON serialization."""
        response = HealthResponse(status="healthy", uptime_seconds=3600)
        json_data = response.model_dump()

        assert json_data["status"] == "healthy"
        assert json_data["uptime_seconds"] == 3600
        assert "timestamp" in json_data


class TestServiceHealth:
    """Test ServiceHealth Pydantic model."""

    def test_service_health_creation(self):
        """Test creating a service health status."""
        service = ServiceHealth(
            status="healthy", message="Connected to database", response_time_ms=15
        )

        assert service.status == "healthy"
        assert service.message == "Connected to database"
        assert service.response_time_ms == 15

    def test_service_health_without_response_time(self):
        """Test creating service health without response time."""
        service = ServiceHealth(status="unhealthy", message="Circuit breaker open")

        assert service.status == "unhealthy"
        assert service.message == "Circuit breaker open"
        assert service.response_time_ms is None

    def test_service_health_validation_status(self):
        """Test status validation."""
        # Valid statuses
        ServiceHealth(status="healthy", message="OK")
        ServiceHealth(status="degraded", message="Slow")
        ServiceHealth(status="unhealthy", message="Failed")

        # Invalid status
        with pytest.raises(ValidationError):
            ServiceHealth(status="unknown", message="Test")

    def test_service_health_validation_message(self):
        """Test message validation (must not be empty)."""
        # Valid message
        ServiceHealth(status="healthy", message="OK")

        # Invalid message (empty)
        with pytest.raises(ValidationError):
            ServiceHealth(status="healthy", message="")

    def test_service_health_validation_response_time(self):
        """Test response time validation (must be >= 0 if provided)."""
        # Valid response times
        ServiceHealth(status="healthy", message="OK", response_time_ms=0)
        ServiceHealth(status="healthy", message="OK", response_time_ms=100)

        # Invalid response time
        with pytest.raises(ValidationError):
            ServiceHealth(status="healthy", message="OK", response_time_ms=-1)


class TestDetailedHealthResponse:
    """Test DetailedHealthResponse Pydantic model."""

    def test_detailed_health_response_creation(self):
        """Test creating a detailed health response."""
        services = {
            "database": ServiceHealth(
                status="healthy", message="Connected", response_time_ms=10
            ),
            "workers": ServiceHealth(
                status="healthy", message="5/5 active", response_time_ms=5
            ),
        }

        response = DetailedHealthResponse(
            status="healthy", uptime_seconds=3600, services=services
        )

        assert response.status == "healthy"
        assert response.uptime_seconds == 3600
        assert len(response.services) == 2
        assert "database" in response.services
        assert "workers" in response.services

    def test_detailed_health_response_empty_services(self):
        """Test creating detailed health response with no services."""
        response = DetailedHealthResponse(status="healthy", uptime_seconds=100)

        assert response.status == "healthy"
        assert len(response.services) == 0

    def test_detailed_health_response_validation(self):
        """Test validation of all fields."""
        # Valid response
        DetailedHealthResponse(
            status="degraded",
            uptime_seconds=1000,
            services={
                "test": ServiceHealth(status="degraded", message="Slow response")
            },
        )

        # Invalid status
        with pytest.raises(ValidationError):
            DetailedHealthResponse(
                status="invalid", uptime_seconds=100, services={}
            )

        # Invalid uptime
        with pytest.raises(ValidationError):
            DetailedHealthResponse(
                status="healthy", uptime_seconds=-1, services={}
            )

    def test_detailed_health_response_json_serialization(self):
        """Test JSON serialization with nested services."""
        services = {
            "database": ServiceHealth(
                status="healthy", message="Connected", response_time_ms=10
            )
        }
        response = DetailedHealthResponse(
            status="healthy", uptime_seconds=3600, services=services
        )

        json_data = response.model_dump()

        assert json_data["status"] == "healthy"
        assert json_data["uptime_seconds"] == 3600
        assert "database" in json_data["services"]
        assert json_data["services"]["database"]["status"] == "healthy"
        assert json_data["services"]["database"]["response_time_ms"] == 10
