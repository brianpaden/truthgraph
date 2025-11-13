"""Docker container statistics collector.

Monitors resource usage (CPU, memory, network I/O) for all TruthGraph containers
using the Docker API. Designed to work on both Windows (npipe) and Linux (unix socket).
"""

import asyncio
import logging
import platform
from typing import Any

logger = logging.getLogger(__name__)


class DockerStatsCollector:
    """Collects resource metrics from Docker containers.

    Uses asyncio.to_thread() to avoid blocking the event loop with
    synchronous Docker SDK calls. Handles platform differences between
    Windows and Linux.

    Metrics collected per container (with service label):
    - container.cpu.percent{service="api|postgres|frontend"}
    - container.memory.usage_mb{service="api|postgres|frontend"}
    - container.memory.limit_mb{service="api|postgres|frontend"}
    - container.memory.percent{service="api|postgres|frontend"}
    - container.network.bytes_in{service="api|postgres|frontend"}
    - container.network.bytes_out{service="api|postgres|frontend"}
    - container.status{service="api|postgres|frontend"} (running/paused/exited)
    - container.restart_count{service="api|postgres|frontend"}
    - container.uptime_seconds{service="api|postgres|frontend"}

    Attributes:
        metrics_collector: MetricsCollector instance for recording metrics
        docker_client: Docker client instance (lazy-loaded)

    Example:
        >>> collector = DockerStatsCollector(metrics_collector)
        >>> await collector.collect_stats()
    """

    def __init__(self, metrics_collector: Any):
        """Initialize Docker stats collector.

        Args:
            metrics_collector: MetricsCollector instance for recording metrics
        """
        self.metrics_collector = metrics_collector
        self._docker_client: Any | None = None
        self._is_available = True  # Track if Docker is available

    def _create_docker_client(self) -> Any:
        """Create Docker client with platform-specific connection.

        Returns:
            Docker client instance configured for the current platform.

        Raises:
            ImportError: If docker package is not installed
            Exception: If Docker daemon is not accessible
        """
        try:
            import docker

            # Platform-specific Docker socket connection
            if platform.system() == "Windows":
                # Windows uses named pipe
                client = docker.DockerClient(base_url="npipe:////./pipe/docker_engine")
            else:
                # Linux/macOS uses unix socket
                client = docker.DockerClient(base_url="unix:///var/run/docker.sock")

            # Test connection
            client.ping()
            logger.info(f"Docker client initialized for {platform.system()}")
            return client

        except ImportError:
            logger.warning("Docker SDK not installed, container monitoring disabled")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Docker daemon: {e}")
            raise

    def _get_docker_client(self) -> Any | None:
        """Get or create Docker client instance.

        Returns:
            Docker client if available, None if Docker is not accessible.
        """
        if not self._is_available:
            return None

        if self._docker_client is None:
            try:
                self._docker_client = self._create_docker_client()
            except Exception as e:
                logger.warning(f"Docker monitoring unavailable: {e}")
                self._is_available = False
                return None

        return self._docker_client

    async def collect_stats(self) -> None:
        """Collect statistics for all TruthGraph containers.

        Uses asyncio.to_thread() to avoid blocking the event loop.
        Collects metrics for containers with 'truthgraph' in their name.
        """
        client = self._get_docker_client()
        if client is None:
            # Docker not available, skip collection
            return

        try:
            # Run blocking Docker API calls in thread pool
            stats = await asyncio.to_thread(self._collect_stats_sync, client)

            # Record all metrics
            for container_stats in stats:
                service = container_stats["service"]
                labels = {"service": service}

                # CPU metrics
                if container_stats["cpu_percent"] is not None:
                    await self.metrics_collector.set_gauge(
                        "container.cpu.percent",
                        container_stats["cpu_percent"],
                        labels=labels,
                    )

                # Memory metrics
                await self.metrics_collector.set_gauge(
                    "container.memory.usage_mb",
                    container_stats["memory_usage_mb"],
                    labels=labels,
                )
                await self.metrics_collector.set_gauge(
                    "container.memory.limit_mb",
                    container_stats["memory_limit_mb"],
                    labels=labels,
                )
                await self.metrics_collector.set_gauge(
                    "container.memory.percent",
                    container_stats["memory_percent"],
                    labels=labels,
                )

                # Network metrics
                await self.metrics_collector.set_gauge(
                    "container.network.bytes_in",
                    container_stats["network_bytes_in"],
                    labels=labels,
                )
                await self.metrics_collector.set_gauge(
                    "container.network.bytes_out",
                    container_stats["network_bytes_out"],
                    labels=labels,
                )

                # Container health metrics
                await self.metrics_collector.set_gauge(
                    "container.status",
                    1 if container_stats["status"] == "running" else 0,
                    labels=labels,
                )
                await self.metrics_collector.set_gauge(
                    "container.restart_count",
                    container_stats["restart_count"],
                    labels=labels,
                )
                await self.metrics_collector.set_gauge(
                    "container.uptime_seconds",
                    container_stats["uptime_seconds"],
                    labels=labels,
                )

        except Exception as e:
            logger.error(f"Error collecting Docker stats: {e}", exc_info=True)

    def _collect_stats_sync(self, client: Any) -> list[dict[str, Any]]:
        """Synchronous Docker stats collection (runs in thread pool).

        Args:
            client: Docker client instance

        Returns:
            List of container statistics dictionaries.
        """
        stats = []

        try:
            # Get all containers (including stopped ones)
            containers = client.containers.list(all=True)

            for container in containers:
                # Only monitor TruthGraph-related containers
                container_name = container.name.lower()
                if "truthgraph" not in container_name and "postgres" not in container_name:
                    continue

                # Determine service name
                service = self._extract_service_name(container_name)

                # Get container stats (single read, no streaming)
                try:
                    # For running containers, get real-time stats
                    if container.status == "running":
                        # stats() without stream=True returns a single snapshot
                        raw_stats = container.stats(stream=False)
                        container_stats = self._parse_stats(raw_stats, container, service)
                    else:
                        # For stopped containers, provide basic info
                        container_stats = {
                            "service": service,
                            "status": container.status,
                            "cpu_percent": 0.0,
                            "memory_usage_mb": 0.0,
                            "memory_limit_mb": 0.0,
                            "memory_percent": 0.0,
                            "network_bytes_in": 0,
                            "network_bytes_out": 0,
                            "restart_count": container.attrs.get("RestartCount", 0),
                            "uptime_seconds": 0,
                        }

                    stats.append(container_stats)

                except Exception as e:
                    logger.error(f"Error getting stats for container {container_name}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error listing Docker containers: {e}")

        return stats

    def _extract_service_name(self, container_name: str) -> str:
        """Extract service name from container name.

        Args:
            container_name: Full container name

        Returns:
            Service name (api, postgres, frontend, or other).
        """
        container_name = container_name.lower()

        if "api" in container_name or "backend" in container_name:
            return "api"
        elif "postgres" in container_name or "db" in container_name:
            return "postgres"
        elif "frontend" in container_name or "nginx" in container_name:
            return "frontend"
        else:
            return "other"

    def _parse_stats(self, raw_stats: dict, container: Any, service: str) -> dict[str, Any]:
        """Parse Docker stats API response into metrics.

        Args:
            raw_stats: Raw stats from Docker API
            container: Container object
            service: Service name

        Returns:
            Dictionary of parsed metrics.
        """
        import time

        # CPU calculation
        cpu_percent = self._calculate_cpu_percent(raw_stats)

        # Memory stats
        memory_stats = raw_stats.get("memory_stats", {})
        memory_usage = memory_stats.get("usage", 0)
        memory_limit = memory_stats.get("limit", 1)  # Avoid division by zero

        memory_usage_mb = memory_usage / (1024 * 1024)
        memory_limit_mb = memory_limit / (1024 * 1024)
        memory_percent = (memory_usage / memory_limit * 100) if memory_limit > 0 else 0.0

        # Network stats
        networks = raw_stats.get("networks", {})
        network_bytes_in = sum(net.get("rx_bytes", 0) for net in networks.values())
        network_bytes_out = sum(net.get("tx_bytes", 0) for net in networks.values())

        # Container info
        started_at = container.attrs.get("State", {}).get("StartedAt")
        uptime_seconds = 0
        if started_at and container.status == "running":
            from datetime import datetime

            try:
                start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                uptime_seconds = int((datetime.now(start_time.tzinfo) - start_time).total_seconds())
            except Exception:
                pass

        return {
            "service": service,
            "status": container.status,
            "cpu_percent": cpu_percent,
            "memory_usage_mb": memory_usage_mb,
            "memory_limit_mb": memory_limit_mb,
            "memory_percent": memory_percent,
            "network_bytes_in": network_bytes_in,
            "network_bytes_out": network_bytes_out,
            "restart_count": container.attrs.get("RestartCount", 0),
            "uptime_seconds": uptime_seconds,
        }

    def _calculate_cpu_percent(self, stats: dict) -> float:
        """Calculate CPU usage percentage from Docker stats.

        Args:
            stats: Raw stats dictionary from Docker API

        Returns:
            CPU usage percentage (0-100).
        """
        try:
            cpu_stats = stats.get("cpu_stats", {})
            precpu_stats = stats.get("precpu_stats", {})

            cpu_delta = (
                cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
                - precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            )

            system_delta = (
                cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get("system_cpu_usage", 0)
            )

            if system_delta > 0 and cpu_delta > 0:
                # Number of CPUs
                num_cpus = cpu_stats.get("online_cpus", 1)
                cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
                return round(cpu_percent, 2)

        except Exception as e:
            logger.debug(f"Error calculating CPU percent: {e}")

        return 0.0

    async def close(self) -> None:
        """Close Docker client and cleanup resources."""
        if self._docker_client:
            try:
                await asyncio.to_thread(self._docker_client.close)
                logger.info("Docker client closed")
            except Exception as e:
                logger.error(f"Error closing Docker client: {e}")
