"""Unit tests for HealthChecker and CircuitBreaker."""

import asyncio
import time

import pytest

from truthgraph.monitoring.health import (
    CircuitBreaker,
    HealthChecker,
    get_health_checker,
)
from truthgraph.monitoring.storage.models import HealthStatus, ServiceHealth


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=30)

        assert breaker.failure_threshold == 3
        assert breaker.timeout == 30
        assert breaker.failures == 0
        assert breaker.last_failure_time is None

    def test_circuit_breaker_closed_initially(self):
        """Test that circuit breaker starts closed."""
        breaker = CircuitBreaker()
        assert breaker.is_open() is False

    def test_circuit_breaker_opens_after_threshold(self):
        """Test that circuit breaker opens after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=30)

        # Record failures
        breaker.record_failure()
        assert breaker.is_open() is False  # Still closed

        breaker.record_failure()
        assert breaker.is_open() is False  # Still closed

        breaker.record_failure()
        assert breaker.is_open() is True  # Now open

    def test_circuit_breaker_success_resets(self):
        """Test that success resets the circuit breaker."""
        breaker = CircuitBreaker(failure_threshold=3)

        # Record some failures
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.failures == 2

        # Record success
        breaker.record_success()
        assert breaker.failures == 0
        assert breaker.last_failure_time is None
        assert breaker.is_open() is False

    def test_circuit_breaker_timeout_half_open(self):
        """Test that circuit breaker transitions to half-open after timeout."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=0.1)  # 100ms timeout

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.is_open() is True

        # Wait for timeout
        time.sleep(0.15)

        # Should be half-open (allow call through)
        assert breaker.is_open() is False

        # But failures are still tracked
        assert breaker.failures == 2

    def test_circuit_breaker_failure_time_tracking(self):
        """Test that circuit breaker tracks last failure time."""
        breaker = CircuitBreaker()

        assert breaker.last_failure_time is None

        before = time.time()
        breaker.record_failure()
        after = time.time()

        assert breaker.last_failure_time is not None
        assert before <= breaker.last_failure_time <= after


class TestHealthChecker:
    """Test HealthChecker functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test health checker initialization."""
        checker = HealthChecker()

        assert checker.start_time > 0
        assert len(checker.circuit_breakers) == 0

    @pytest.mark.asyncio
    async def test_get_uptime_seconds(self):
        """Test getting uptime."""
        checker = HealthChecker()

        uptime = checker.get_uptime_seconds()
        assert uptime >= 0
        assert uptime < 2  # Should be under 2 seconds

        await asyncio.sleep(0.2)  # Increased delay for reliability
        uptime2 = checker.get_uptime_seconds()
        assert uptime2 >= uptime  # Allow equal in case of rounding

    @pytest.mark.asyncio
    async def test_check_overall_health(self):
        """Test basic health check."""
        checker = HealthChecker()

        health = await checker.check_overall_health()

        assert health.status == HealthStatus.HEALTHY
        assert health.uptime_seconds >= 0

    @pytest.mark.asyncio
    async def test_check_service_healthy(self):
        """Test checking a healthy service."""
        checker = HealthChecker()

        async def healthy_check():
            return (HealthStatus.HEALTHY, "Service is healthy")

        result = await checker.check_service("test_service", healthy_check)

        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Service is healthy"
        assert result.response_time_ms is not None
        assert result.response_time_ms >= 0

    @pytest.mark.asyncio
    async def test_check_service_unhealthy(self):
        """Test checking an unhealthy service."""
        checker = HealthChecker()

        async def unhealthy_check():
            return (HealthStatus.UNHEALTHY, "Service is down")

        result = await checker.check_service("test_service", unhealthy_check)

        assert result.status == HealthStatus.UNHEALTHY
        assert result.message == "Service is down"
        assert result.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_check_service_degraded(self):
        """Test checking a degraded service."""
        checker = HealthChecker()

        async def degraded_check():
            return (HealthStatus.DEGRADED, "Service is slow")

        result = await checker.check_service("test_service", degraded_check)

        assert result.status == HealthStatus.DEGRADED
        assert result.message == "Service is slow"

    @pytest.mark.asyncio
    async def test_check_service_with_exception(self):
        """Test service check that raises an exception."""
        checker = HealthChecker()

        async def failing_check():
            raise Exception("Connection refused")

        result = await checker.check_service("test_service", failing_check)

        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection refused" in result.message
        assert result.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_check_service_circuit_breaker(self):
        """Test that circuit breaker prevents repeated checks."""
        checker = HealthChecker()

        async def failing_check():
            raise Exception("Service unavailable")

        # First 3 failures should call the function
        for _ in range(3):
            result = await checker.check_service("test_service", failing_check)
            assert result.status == HealthStatus.UNHEALTHY

        # Circuit should be open now
        result = await checker.check_service("test_service", failing_check)
        assert result.status == HealthStatus.UNHEALTHY
        assert "Circuit breaker open" in result.message
        assert result.response_time_ms is None

    @pytest.mark.asyncio
    async def test_check_service_circuit_breaker_reset(self):
        """Test that circuit breaker resets after successful check."""
        checker = HealthChecker()

        call_count = 0

        async def sometimes_failing_check():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Temporary failure")
            return (HealthStatus.HEALTHY, "Recovered")

        # First 2 calls fail
        await checker.check_service("test_service", sometimes_failing_check)
        await checker.check_service("test_service", sometimes_failing_check)

        # Third call succeeds and resets circuit breaker
        result = await checker.check_service("test_service", sometimes_failing_check)
        assert result.status == HealthStatus.HEALTHY

        # Circuit breaker should be reset
        breaker = checker._get_circuit_breaker("test_service")
        assert breaker.failures == 0

    @pytest.mark.asyncio
    async def test_aggregate_service_statuses_all_healthy(self):
        """Test status aggregation when all services are healthy."""
        checker = HealthChecker()

        services = {
            "database": ServiceHealth(status=HealthStatus.HEALTHY, message="OK"),
            "workers": ServiceHealth(status=HealthStatus.HEALTHY, message="OK"),
            "cache": ServiceHealth(status=HealthStatus.HEALTHY, message="OK"),
        }

        status = checker.aggregate_service_statuses(services)
        assert status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_aggregate_service_statuses_one_unhealthy(self):
        """Test status aggregation when one service is unhealthy."""
        checker = HealthChecker()

        services = {
            "database": ServiceHealth(status=HealthStatus.HEALTHY, message="OK"),
            "workers": ServiceHealth(status=HealthStatus.UNHEALTHY, message="Failed"),
            "cache": ServiceHealth(status=HealthStatus.HEALTHY, message="OK"),
        }

        status = checker.aggregate_service_statuses(services)
        assert status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_aggregate_service_statuses_one_degraded(self):
        """Test status aggregation when one service is degraded."""
        checker = HealthChecker()

        services = {
            "database": ServiceHealth(status=HealthStatus.HEALTHY, message="OK"),
            "workers": ServiceHealth(status=HealthStatus.DEGRADED, message="Slow"),
            "cache": ServiceHealth(status=HealthStatus.HEALTHY, message="OK"),
        }

        status = checker.aggregate_service_statuses(services)
        assert status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_aggregate_service_statuses_empty(self):
        """Test status aggregation with no services."""
        checker = HealthChecker()
        status = checker.aggregate_service_statuses({})
        assert status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_services_concurrent(self):
        """Test running multiple service checks concurrently."""
        checker = HealthChecker()

        async def fast_check():
            await asyncio.sleep(0.01)
            return (HealthStatus.HEALTHY, "Fast service OK")

        async def slow_check():
            await asyncio.sleep(0.05)
            return (HealthStatus.HEALTHY, "Slow service OK")

        checks = {
            "fast_service": fast_check,
            "slow_service": slow_check,
        }

        start_time = time.time()
        results = await checker.check_services_concurrent(checks, timeout=1.0)
        elapsed = time.time() - start_time

        # Should complete in roughly the time of the slowest check (~0.05s)
        # not the sum of all checks (~0.06s)
        assert elapsed < 0.1

        assert len(results) == 2
        assert "fast_service" in results
        assert "slow_service" in results
        assert results["fast_service"].status == HealthStatus.HEALTHY
        assert results["slow_service"].status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_services_concurrent_timeout(self):
        """Test concurrent checks with timeout."""
        checker = HealthChecker()

        async def very_slow_check():
            await asyncio.sleep(10)  # Very slow
            return (HealthStatus.HEALTHY, "Should timeout")

        checks = {"slow_service": very_slow_check}

        results = await checker.check_services_concurrent(checks, timeout=0.1)

        assert len(results) == 1
        assert results["slow_service"].status == HealthStatus.UNHEALTHY
        assert "timed out" in results["slow_service"].message.lower()

    @pytest.mark.asyncio
    async def test_check_detailed_health_no_services(self):
        """Test detailed health check with no service checks."""
        checker = HealthChecker()

        detailed = await checker.check_detailed_health()

        assert detailed.status == HealthStatus.HEALTHY
        assert detailed.uptime_seconds >= 0
        assert len(detailed.services) == 0

    @pytest.mark.asyncio
    async def test_check_detailed_health_with_services(self):
        """Test detailed health check with service checks."""
        checker = HealthChecker()

        async def db_check():
            return (HealthStatus.HEALTHY, "Database connected")

        async def worker_check():
            return (HealthStatus.DEGRADED, "3/5 workers active")

        checks = {
            "database": db_check,
            "workers": worker_check,
        }

        detailed = await checker.check_detailed_health(checks)

        assert detailed.status == HealthStatus.DEGRADED  # One service degraded
        assert detailed.uptime_seconds >= 0
        assert len(detailed.services) == 2
        assert detailed.services["database"].status == HealthStatus.HEALTHY
        assert detailed.services["workers"].status == HealthStatus.DEGRADED


class TestGetHealthChecker:
    """Test singleton instance function."""

    def test_get_health_checker_singleton(self):
        """Test that get_health_checker returns singleton."""
        # Reset global instance
        import truthgraph.monitoring.health as health_module
        health_module._health_checker_instance = None

        checker1 = get_health_checker()
        checker2 = get_health_checker()

        # Should be the same instance
        assert checker1 is checker2

    def test_get_health_checker_creates_instance(self):
        """Test that get_health_checker creates instance if needed."""
        import truthgraph.monitoring.health as health_module
        health_module._health_checker_instance = None

        checker = get_health_checker()
        assert checker is not None
        assert isinstance(checker, HealthChecker)
