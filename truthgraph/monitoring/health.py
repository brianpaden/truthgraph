"""Health check system with circuit breaker pattern.

This module provides health checking capabilities for the TruthGraph system,
including circuit breaker pattern to prevent cascading failures and hammering
unhealthy services.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine

from truthgraph.monitoring.storage.models import (
    DetailedHealthResponse,
    HealthResponse,
    HealthStatus,
    ServiceHealth,
)

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker to prevent repeated calls to failing services.

    Implements the circuit breaker pattern:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Failure threshold exceeded, calls fail fast
    - HALF_OPEN: After timeout, allow test call through

    Attributes:
        failure_threshold: Number of consecutive failures before opening
        timeout: Seconds to wait before transitioning to half-open
        failures: Current consecutive failure count
        last_failure_time: Timestamp of most recent failure

    Example:
        >>> breaker = CircuitBreaker(failure_threshold=3, timeout=30)
        >>> if breaker.is_open():
        ...     return ServiceHealth(status="unhealthy", message="Circuit breaker open")
        >>> try:
        ...     result = await check_service()
        ...     breaker.record_success()
        ... except Exception:
        ...     breaker.record_failure()
    """

    def __init__(self, failure_threshold: int = 3, timeout: int = 30):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Consecutive failures before opening circuit
            timeout: Seconds before attempting to close circuit again
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time: float | None = None

    def is_open(self) -> bool:
        """Check if circuit breaker is open (blocking calls).

        Returns:
            True if circuit is open and should block calls, False otherwise.

        The circuit automatically transitions to half-open state after the
        timeout period, allowing a test call through.
        """
        if self.failures >= self.failure_threshold:
            if self.last_failure_time and (time.time() - self.last_failure_time) < self.timeout:
                return True
            # Timeout elapsed, reset to half-open (allow one call through)
            # Keep failure count but allow call - if it fails, circuit stays open
        return False

    def record_success(self) -> None:
        """Record successful service call.

        Resets failure count and closes the circuit.
        """
        self.failures = 0
        self.last_failure_time = None

    def record_failure(self) -> None:
        """Record failed service call.

        Increments failure count and updates last failure time.
        Opens circuit if threshold is exceeded.
        """
        self.failures += 1
        self.last_failure_time = time.time()


class HealthChecker:
    """Centralized health checking service for TruthGraph.

    Provides health check capabilities with:
    - Circuit breaker pattern to prevent cascading failures
    - Concurrent health checks for performance
    - Response time tracking
    - Status aggregation logic

    This is the basic framework for 4.7a. Feature 4.7b will add
    actual service monitors (database, Docker, workers, etc.).

    Attributes:
        start_time: Unix timestamp when health checker was initialized
        circuit_breakers: Per-service circuit breakers

    Example:
        >>> checker = HealthChecker()
        >>> health = await checker.check_overall_health()
        >>> detailed = await checker.check_detailed_health()
    """

    def __init__(self):
        """Initialize health checker."""
        self.start_time = time.time()
        self.circuit_breakers: dict[str, CircuitBreaker] = {}

    def get_uptime_seconds(self) -> int:
        """Get application uptime in seconds.

        Returns:
            Number of seconds since health checker was initialized.
        """
        return int(time.time() - self.start_time)

    def _get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for a service.

        Args:
            service_name: Name of the service to get breaker for

        Returns:
            CircuitBreaker instance for the service.
        """
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker()
        return self.circuit_breakers[service_name]

    async def check_service(
        self,
        service_name: str,
        check_func: Callable[[], Coroutine[Any, Any, tuple[HealthStatus, str]]],
    ) -> ServiceHealth:
        """Check health of a single service with circuit breaker protection.

        Args:
            service_name: Name of service being checked
            check_func: Async function that returns (status, message)

        Returns:
            ServiceHealth with status, message, and response time.

        Example:
            >>> async def check_db():
            ...     # Perform database health check
            ...     return (HealthStatus.HEALTHY, "Connected")
            >>> health = await checker.check_service("database", check_db)
        """
        breaker = self._get_circuit_breaker(service_name)

        # Circuit breaker open - fail fast
        if breaker.is_open():
            logger.warning(f"Circuit breaker open for service: {service_name}")
            return ServiceHealth(
                status=HealthStatus.UNHEALTHY,
                message="Circuit breaker open (too many failures)",
                response_time_ms=None,
            )

        # Perform health check with timing
        start_time = time.time()
        try:
            status, message = await check_func()
            response_time_ms = int((time.time() - start_time) * 1000)

            # Record success
            breaker.record_success()

            return ServiceHealth(status=status, message=message, response_time_ms=response_time_ms)

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            breaker.record_failure()
            logger.error(f"Health check failed for {service_name}: {e}", exc_info=True)

            return ServiceHealth(
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                response_time_ms=response_time_ms,
            )

    async def check_services_concurrent(
        self,
        service_checks: dict[str, Callable[[], Coroutine[Any, Any, tuple[HealthStatus, str]]]],
        timeout: float = 5.0,
    ) -> dict[str, ServiceHealth]:
        """Run multiple service health checks concurrently.

        Args:
            service_checks: Dictionary mapping service names to check functions
            timeout: Maximum seconds to wait for all checks (default 5.0)

        Returns:
            Dictionary mapping service names to ServiceHealth results.

        Example:
            >>> checks = {
            ...     "database": check_db,
            ...     "workers": check_workers,
            ... }
            >>> results = await checker.check_services_concurrent(checks)
        """
        # Create tasks for all checks
        tasks = {
            name: asyncio.create_task(self.check_service(name, check_func))
            for name, check_func in service_checks.items()
        }

        # Wait for all with timeout
        try:
            done, pending = await asyncio.wait(
                tasks.values(), timeout=timeout, return_when=asyncio.ALL_COMPLETED
            )

            # Cancel any pending tasks
            for task in pending:
                task.cancel()

            # Collect results
            results = {}
            for name, task in tasks.items():
                if task in done:
                    try:
                        results[name] = await task
                    except Exception as e:
                        logger.error(f"Error getting result for {name}: {e}")
                        results[name] = ServiceHealth(
                            status=HealthStatus.UNHEALTHY,
                            message=f"Error: {str(e)}",
                            response_time_ms=None,
                        )
                else:
                    # Task timed out
                    results[name] = ServiceHealth(
                        status=HealthStatus.UNHEALTHY,
                        message="Health check timed out",
                        response_time_ms=None,
                    )

            return results

        except Exception as e:
            logger.error(f"Error running concurrent health checks: {e}", exc_info=True)
            # Return unhealthy status for all services on error
            return {
                name: ServiceHealth(
                    status=HealthStatus.UNHEALTHY,
                    message=f"Concurrent check error: {str(e)}",
                    response_time_ms=None,
                )
                for name in service_checks.keys()
            }

    def aggregate_service_statuses(self, services: dict[str, ServiceHealth]) -> HealthStatus:
        """Aggregate individual service statuses into overall health.

        Aggregation logic:
        - All services healthy → HEALTHY
        - Any service unhealthy → UNHEALTHY
        - Otherwise (some degraded) → DEGRADED

        Args:
            services: Dictionary of service health statuses

        Returns:
            Aggregated overall health status.

        Example:
            >>> services = {
            ...     "database": ServiceHealth(status="healthy", message="OK"),
            ...     "workers": ServiceHealth(status="degraded", message="3/5 active"),
            ... }
            >>> status = checker.aggregate_service_statuses(services)
            >>> assert status == HealthStatus.DEGRADED
        """
        if not services:
            return HealthStatus.HEALTHY

        statuses = [s.status for s in services.values()]

        # Any unhealthy → overall unhealthy
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY

        # Any degraded → overall degraded
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED

        # All healthy
        return HealthStatus.HEALTHY

    async def check_overall_health(self) -> HealthResponse:
        """Perform basic health check.

        Returns basic liveness check without checking dependencies.
        This is used for /health endpoint - should always return healthy
        if the API is responsive.

        Returns:
            HealthResponse with status and uptime.

        Example:
            >>> health = await checker.check_overall_health()
            >>> assert health.status == "healthy"
        """
        return HealthResponse(status=HealthStatus.HEALTHY, uptime_seconds=self.get_uptime_seconds())

    async def check_detailed_health(
        self,
        service_checks: dict[str, Callable[[], Coroutine[Any, Any, tuple[HealthStatus, str]]]]
        | None = None,
    ) -> DetailedHealthResponse:
        """Perform detailed health check with service dependencies.

        Runs health checks for all registered services concurrently and
        aggregates the results.

        Args:
            service_checks: Optional dictionary of service check functions.
                           If None, returns basic health only.

        Returns:
            DetailedHealthResponse with overall status and per-service health.

        Example:
            >>> checks = {
            ...     "database": check_db,
            ...     "workers": check_workers,
            ... }
            >>> detailed = await checker.check_detailed_health(checks)
        """
        # If no service checks provided, return basic health
        if not service_checks:
            return DetailedHealthResponse(
                status=HealthStatus.HEALTHY,
                uptime_seconds=self.get_uptime_seconds(),
                services={},
            )

        # Run all service checks concurrently
        service_results = await self.check_services_concurrent(service_checks)

        # Aggregate overall status
        overall_status = self.aggregate_service_statuses(service_results)

        return DetailedHealthResponse(
            status=overall_status,
            uptime_seconds=self.get_uptime_seconds(),
            services=service_results,
        )


# Singleton instance for dependency injection
_health_checker_instance: HealthChecker | None = None


def get_health_checker() -> HealthChecker:
    """Get or create the singleton HealthChecker instance.

    Use this function for FastAPI dependency injection to ensure
    the same health checker instance is used throughout the application.

    Returns:
        Singleton HealthChecker instance.

    Example:
        In FastAPI route:
        >>> from fastapi import Depends
        >>> @app.get("/health")
        >>> async def health(checker: HealthChecker = Depends(get_health_checker)):
        ...     return await checker.check_overall_health()
    """
    global _health_checker_instance
    if _health_checker_instance is None:
        _health_checker_instance = HealthChecker()
    return _health_checker_instance
