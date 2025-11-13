"""Unit tests for Docker statistics collector."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from truthgraph.monitoring.collectors.docker_stats import DockerStatsCollector
from truthgraph.monitoring.metrics_collector import MetricsCollector


@pytest.fixture
def mock_metrics_collector():
    """Create a mock metrics collector."""
    collector = Mock(spec=MetricsCollector)
    collector.set_gauge = AsyncMock()
    return collector


@pytest.fixture
def docker_collector(mock_metrics_collector):
    """Create Docker stats collector with mock."""
    return DockerStatsCollector(mock_metrics_collector)


class TestDockerStatsCollector:
    """Test cases for DockerStatsCollector."""

    @pytest.mark.asyncio
    async def test_initialization(self, docker_collector, mock_metrics_collector):
        """Test collector initialization."""
        assert docker_collector.metrics_collector == mock_metrics_collector
        assert docker_collector._docker_client is None
        assert docker_collector._is_available is True

    @pytest.mark.asyncio
    async def test_collect_stats_docker_unavailable(self, docker_collector):
        """Test collection when Docker is unavailable."""
        docker_collector._is_available = False

        # Should not raise exception
        await docker_collector.collect_stats()

        # No metrics should be recorded
        docker_collector.metrics_collector.set_gauge.assert_not_called()

    @pytest.mark.asyncio
    async def test_collect_stats_success(self, docker_collector, mock_metrics_collector):
        """Test successful stats collection."""
        # Mock Docker client
        mock_container = Mock()
        mock_container.name = "truthgraph-api"
        mock_container.status = "running"
        mock_container.attrs = {"RestartCount": 0, "State": {"StartedAt": "2024-01-01T00:00:00Z"}}

        mock_container.stats.return_value = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 1000000000},
                "system_cpu_usage": 10000000000,
                "online_cpus": 4,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 900000000},
                "system_cpu_usage": 9500000000,
            },
            "memory_stats": {
                "usage": 512 * 1024 * 1024,  # 512 MB
                "limit": 2048 * 1024 * 1024,  # 2048 MB
            },
            "networks": {
                "eth0": {
                    "rx_bytes": 1000000,
                    "tx_bytes": 500000,
                }
            },
        }

        mock_client = Mock()
        mock_client.containers.list.return_value = [mock_container]

        # Mock Docker client creation
        with patch.object(
            docker_collector, "_get_docker_client", return_value=mock_client
        ) as mock_get_client:
            # Mock the sync collection method
            with patch.object(
                docker_collector, "_collect_stats_sync", return_value=[
                    {
                        "service": "api",
                        "status": "running",
                        "cpu_percent": 8.42,
                        "memory_usage_mb": 512.0,
                        "memory_limit_mb": 2048.0,
                        "memory_percent": 25.0,
                        "network_bytes_in": 1000000,
                        "network_bytes_out": 500000,
                        "restart_count": 0,
                        "uptime_seconds": 3600,
                    }
                ]
            ):
                await docker_collector.collect_stats()

        # Verify metrics were recorded
        assert mock_metrics_collector.set_gauge.call_count >= 8  # At least 8 metrics per container

    @pytest.mark.asyncio
    async def test_extract_service_name(self, docker_collector):
        """Test service name extraction from container names."""
        assert docker_collector._extract_service_name("truthgraph-api") == "api"
        assert docker_collector._extract_service_name("truthgraph-backend") == "api"
        assert docker_collector._extract_service_name("postgres-db") == "postgres"
        assert docker_collector._extract_service_name("truthgraph-frontend") == "frontend"
        assert docker_collector._extract_service_name("nginx") == "frontend"
        assert docker_collector._extract_service_name("redis") == "other"

    @pytest.mark.asyncio
    async def test_calculate_cpu_percent(self, docker_collector):
        """Test CPU percentage calculation."""
        stats = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 1000000000},
                "system_cpu_usage": 10000000000,
                "online_cpus": 4,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 900000000},
                "system_cpu_usage": 9500000000,
            },
        }

        cpu_percent = docker_collector._calculate_cpu_percent(stats)

        # (1000000000 - 900000000) / (10000000000 - 9500000000) * 4 * 100 = 80.0
        assert cpu_percent == pytest.approx(80.0, rel=0.1)

    @pytest.mark.asyncio
    async def test_calculate_cpu_percent_no_delta(self, docker_collector):
        """Test CPU calculation with no delta (should return 0)."""
        stats = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 1000000000},
                "system_cpu_usage": 10000000000,
                "online_cpus": 4,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 1000000000},
                "system_cpu_usage": 10000000000,
            },
        }

        cpu_percent = docker_collector._calculate_cpu_percent(stats)
        assert cpu_percent == 0.0

    @pytest.mark.asyncio
    async def test_parse_stats(self, docker_collector):
        """Test parsing of Docker stats."""
        mock_container = Mock()
        mock_container.name = "truthgraph-api"
        mock_container.status = "running"
        mock_container.attrs = {
            "RestartCount": 2,
            "State": {"StartedAt": "2024-01-01T00:00:00.000000000Z"},
        }

        raw_stats = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 1000000000},
                "system_cpu_usage": 10000000000,
                "online_cpus": 4,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 900000000},
                "system_cpu_usage": 9500000000,
            },
            "memory_stats": {
                "usage": 512 * 1024 * 1024,
                "limit": 2048 * 1024 * 1024,
            },
            "networks": {
                "eth0": {"rx_bytes": 1000000, "tx_bytes": 500000},
            },
        }

        stats = docker_collector._parse_stats(raw_stats, mock_container, "api")

        assert stats["service"] == "api"
        assert stats["status"] == "running"
        assert stats["cpu_percent"] > 0
        assert stats["memory_usage_mb"] == 512.0
        assert stats["memory_limit_mb"] == 2048.0
        assert stats["memory_percent"] == 25.0
        assert stats["network_bytes_in"] == 1000000
        assert stats["network_bytes_out"] == 500000
        assert stats["restart_count"] == 2

    @pytest.mark.asyncio
    async def test_collect_stats_handles_exception(self, docker_collector, mock_metrics_collector):
        """Test that collection handles exceptions gracefully."""
        mock_client = Mock()
        mock_client.containers.list.side_effect = Exception("Docker error")

        with patch.object(docker_collector, "_get_docker_client", return_value=mock_client):
            # Should not raise exception
            await docker_collector.collect_stats()

        # No metrics should be recorded
        mock_metrics_collector.set_gauge.assert_not_called()

    @pytest.mark.asyncio
    async def test_close(self, docker_collector):
        """Test closing Docker client."""
        mock_client = Mock()
        mock_client.close = Mock()

        docker_collector._docker_client = mock_client

        await docker_collector.close()

        # Verify close was called (via asyncio.to_thread)
        # Note: In real test, we'd need to mock asyncio.to_thread

    @pytest.mark.asyncio
    async def test_docker_client_creation_failure(self, docker_collector):
        """Test handling of Docker client creation failure."""
        with patch.object(docker_collector, "_create_docker_client", side_effect=Exception("Docker not available")):
            client = docker_collector._get_docker_client()

            assert client is None
            assert docker_collector._is_available is False

    @pytest.mark.asyncio
    async def test_multiple_containers(self, docker_collector, mock_metrics_collector):
        """Test collection with multiple containers."""
        # Mock multiple containers
        mock_api_container = Mock()
        mock_api_container.name = "truthgraph-api"
        mock_api_container.status = "running"

        mock_db_container = Mock()
        mock_db_container.name = "postgres-db"
        mock_db_container.status = "running"

        mock_client = Mock()

        with patch.object(docker_collector, "_get_docker_client", return_value=mock_client):
            with patch.object(
                docker_collector, "_collect_stats_sync", return_value=[
                    {
                        "service": "api",
                        "status": "running",
                        "cpu_percent": 10.0,
                        "memory_usage_mb": 512.0,
                        "memory_limit_mb": 2048.0,
                        "memory_percent": 25.0,
                        "network_bytes_in": 1000000,
                        "network_bytes_out": 500000,
                        "restart_count": 0,
                        "uptime_seconds": 3600,
                    },
                    {
                        "service": "postgres",
                        "status": "running",
                        "cpu_percent": 5.0,
                        "memory_usage_mb": 1024.0,
                        "memory_limit_mb": 2048.0,
                        "memory_percent": 50.0,
                        "network_bytes_in": 2000000,
                        "network_bytes_out": 1000000,
                        "restart_count": 0,
                        "uptime_seconds": 7200,
                    },
                ]
            ):
                await docker_collector.collect_stats()

        # Should record metrics for both containers
        assert mock_metrics_collector.set_gauge.call_count >= 16  # 8 metrics × 2 containers
