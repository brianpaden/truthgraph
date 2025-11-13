"""Health and metrics API endpoints.

Provides comprehensive monitoring endpoints for system health, metrics export,
and operational dashboard data.
"""

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from truthgraph.monitoring.collectors.process_stats import ProcessStatsCollector
from truthgraph.monitoring.collectors.worker_stats import WorkerStatsCollector
from truthgraph.monitoring.health import HealthChecker, HealthStatus, get_health_checker
from truthgraph.monitoring.metrics_collector import MetricsCollector, get_metrics_collector
from truthgraph.monitoring.storage.models import DetailedHealthResponse, HealthResponse

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["Monitoring"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Fast health check for load balancers. Returns healthy if API is responsive.",
)
async def health_basic(
    request: Request,
    response: Response,
    checker: HealthChecker = Depends(get_health_checker),
) -> HealthResponse:
    """Basic health check endpoint.

    Returns:
        HealthResponse with status and uptime.

    Performance target: < 10ms
    Always returns 200 OK if API is responsive (no dependency checks).
    """
    return await checker.check_overall_health()


@router.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed health check",
    description="Comprehensive health check including all service dependencies.",
)
async def health_detailed(
    request: Request,
    response: Response,
    checker: HealthChecker = Depends(get_health_checker),
    collector: MetricsCollector = Depends(get_metrics_collector),
) -> DetailedHealthResponse:
    """Detailed health check with all service dependencies.

    Checks:
    - Database connectivity
    - ML services (embedding, NLI)
    - Worker pool status
    - Docker containers (if available)

    Returns:
        DetailedHealthResponse with per-service health status.

    Performance target: < 200ms (concurrent checks with timeout)
    Returns 503 Service Unavailable if critical services are down.
    """
    # Initialize collectors for health checks
    process_collector = ProcessStatsCollector(collector)
    worker_collector = WorkerStatsCollector(collector)

    # Define health check functions
    async def check_database() -> tuple[HealthStatus, str]:
        status, message = await process_collector.check_database_health()
        return (HealthStatus(status), message)

    async def check_workers() -> tuple[HealthStatus, str]:
        status, message = await worker_collector.check_health()
        return (HealthStatus(status), message)

    async def check_embedding_service() -> tuple[HealthStatus, str]:
        ml_health = await process_collector.check_ml_services_health()
        status, message = ml_health.get("embedding_service", ("unhealthy", "Not checked"))
        return (HealthStatus(status), message)

    async def check_nli_service() -> tuple[HealthStatus, str]:
        ml_health = await process_collector.check_ml_services_health()
        status, message = ml_health.get("nli_service", ("unhealthy", "Not checked"))
        return (HealthStatus(status), message)

    # Run all checks concurrently with timeout
    service_checks = {
        "database": check_database,
        "workers": check_workers,
        "embedding_service": check_embedding_service,
        "nli_service": check_nli_service,
    }

    detailed_health = await checker.check_detailed_health(service_checks)

    # Set HTTP status code based on health
    if detailed_health.status == HealthStatus.UNHEALTHY:
        response.status_code = 503  # Service Unavailable
    elif detailed_health.status == HealthStatus.DEGRADED:
        response.status_code = 200  # OK but degraded
    else:
        response.status_code = 200  # OK

    return detailed_health


@router.get(
    "/metrics",
    summary="Prometheus metrics export",
    description="Export all metrics in Prometheus text format for scraping.",
    response_class=Response,
)
async def metrics_prometheus(
    request: Request,
    collector: MetricsCollector = Depends(get_metrics_collector),
) -> Response:
    """Export metrics in Prometheus text format.

    Returns:
        Plain text response with Prometheus-formatted metrics.

    Performance target: < 200ms
    Format: https://prometheus.io/docs/instrumenting/exposition_formats/
    """
    try:
        # Get all metric names
        metric_names = await collector.store.get_all_metric_names()

        # Build Prometheus text format
        lines = []
        lines.append("# TruthGraph Metrics")
        lines.append(f"# Generated at {time.time()}")
        lines.append("")

        for metric_name in metric_names:
            # Get latest value for each metric
            latest = await collector.store.get_latest(metric_name)
            if latest is None:
                continue

            # Determine metric type (simplified - all as gauge for now)
            metric_type = "gauge"
            if "total" in metric_name or "count" in metric_name:
                metric_type = "counter"

            # Add metric metadata
            lines.append(f"# HELP {metric_name} {metric_name.replace('.', ' ')}")
            lines.append(f"# TYPE {metric_name} {metric_type}")

            # Add metric value with labels
            if latest.labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(latest.labels.items()))
                lines.append(f"{metric_name}{{{label_str}}} {latest.value}")
            else:
                lines.append(f"{metric_name} {latest.value}")

            lines.append("")

        prometheus_text = "\n".join(lines)

        return Response(
            content=prometheus_text,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}", exc_info=True)
        return Response(
            content=f"# Error generating metrics: {str(e)}\n",
            media_type="text/plain",
            status_code=500,
        )


@router.get(
    "/metrics/overview",
    summary="Metrics overview for dashboard",
    description="Get comprehensive metrics summary for monitoring dashboard.",
)
async def metrics_overview(
    request: Request,
    collector: MetricsCollector = Depends(get_metrics_collector),
    checker: HealthChecker = Depends(get_health_checker),
) -> dict[str, Any]:
    """Get metrics overview for monitoring dashboard.

    Returns:
        Dictionary with categorized metrics and health status.

    Provides JSON-formatted data suitable for web dashboards.
    """
    try:
        # Get overall health
        health = await health_detailed(request, Response(), checker, collector)

        # Initialize collectors
        process_collector = ProcessStatsCollector(collector)
        worker_collector = WorkerStatsCollector(collector)

        # Get detailed information
        process_details = await process_collector.get_process_details()
        worker_details = await worker_collector.get_worker_details()

        # Get recent metric values
        metric_names = await collector.store.get_all_metric_names()
        recent_metrics = {}

        for name in metric_names:
            latest = await collector.store.get_latest(name)
            if latest:
                recent_metrics[name] = {
                    "value": latest.value,
                    "timestamp": latest.timestamp,
                    "labels": latest.labels,
                }

        return {
            "health": {
                "status": health.status,
                "uptime_seconds": health.uptime_seconds,
                "services": {
                    name: {
                        "status": svc.status,
                        "message": svc.message,
                        "response_time_ms": svc.response_time_ms,
                    }
                    for name, svc in health.services.items()
                },
            },
            "process": process_details,
            "workers": worker_details,
            "metrics": recent_metrics,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Error generating metrics overview: {e}", exc_info=True)
        return {
            "error": str(e),
            "timestamp": time.time(),
        }


@router.get(
    "/metrics/timeseries",
    summary="Time-series metrics data",
    description="Get historical metric data for charting.",
)
async def metrics_timeseries(
    request: Request,
    metric_name: str,
    duration_seconds: int = 3600,
    collector: MetricsCollector = Depends(get_metrics_collector),
) -> dict[str, Any]:
    """Get time-series data for a specific metric.

    Args:
        metric_name: Name of metric to retrieve
        duration_seconds: How far back to look (default 3600 = 1 hour)

    Returns:
        Dictionary with metric values over time.
    """
    try:
        # Get metric data
        values = await collector.store.get_metrics_range(metric_name, duration_seconds)

        # Convert to time-series format
        timeseries = [
            {
                "timestamp": v.timestamp,
                "value": v.value,
                "labels": v.labels,
            }
            for v in values
        ]

        return {
            "metric_name": metric_name,
            "duration_seconds": duration_seconds,
            "data_points": len(timeseries),
            "timeseries": timeseries,
        }

    except Exception as e:
        logger.error(f"Error retrieving timeseries for {metric_name}: {e}", exc_info=True)
        return {
            "error": str(e),
            "metric_name": metric_name,
        }


@router.get(
    "/metrics/list",
    summary="List all available metrics",
    description="Get names of all metrics currently being collected.",
)
async def metrics_list(
    request: Request,
    collector: MetricsCollector = Depends(get_metrics_collector),
) -> dict[str, Any]:
    """List all available metrics.

    Returns:
        Dictionary with metric names categorized by type.
    """
    try:
        metric_names = await collector.store.get_all_metric_names()

        # Categorize metrics
        categories = {
            "system": [],
            "container": [],
            "workers": [],
            "database": [],
            "api": [],
            "ml": [],
            "monitoring": [],
            "asyncio": [],
        }

        for name in metric_names:
            if name.startswith("system."):
                categories["system"].append(name)
            elif name.startswith("container."):
                categories["container"].append(name)
            elif name.startswith("workers.") or name.startswith("queue.") or name.startswith("task."):
                categories["workers"].append(name)
            elif name.startswith("db."):
                categories["database"].append(name)
            elif name.startswith("api."):
                categories["api"].append(name)
            elif name.startswith("ml."):
                categories["ml"].append(name)
            elif name.startswith("monitoring."):
                categories["monitoring"].append(name)
            elif name.startswith("asyncio.") or name.startswith("app."):
                categories["asyncio"].append(name)

        return {
            "total_metrics": len(metric_names),
            "categories": categories,
        }

    except Exception as e:
        logger.error(f"Error listing metrics: {e}", exc_info=True)
        return {
            "error": str(e),
        }
