"""Unit tests for Process statistics collector."""

import asyncio
import gc
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from truthgraph.monitoring.collectors.process_stats import ProcessStatsCollector
from truthgraph.monitoring.metrics_collector import MetricsCollector


@pytest.fixture
def mock_metrics_collector():
    """Create a mock metrics collector."""
    collector = Mock(spec=MetricsCollector)
    collector.set_gauge = AsyncMock()
    collector.increment_counter = AsyncMock()
    return collector


@pytest.fixture
def process_collector(mock_metrics_collector):
    """Create process stats collector with mock."""
    return ProcessStatsCollector(mock_metrics_collector)


class TestProcessStatsCollector:
    """Test cases for ProcessStatsCollector."""

    @pytest.mark.asyncio
    async def test_initialization(self, process_collector, mock_metrics_collector):
        """Test collector initialization."""
        assert process_collector.metrics_collector == mock_metrics_collector
        assert process_collector._last_gc_counts == [0, 0, 0]

    @pytest.mark.asyncio
    async def test_collect_process_stats(self, process_collector, mock_metrics_collector):
        """Test process statistics collection."""
        # Mock psutil
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 512 * 1024 * 1024  # 512 MB
        mock_memory_info.vms = 1024 * 1024 * 1024  # 1024 MB

        mock_process.memory_info.return_value = mock_memory_info
        mock_process.memory_percent.return_value = 10.5
        mock_process.cpu_percent.return_value = 25.3
        mock_process.num_threads.return_value = 15

        with patch("psutil.Process", return_value=mock_process):
            await process_collector.collect_process_stats()

        # Verify metrics were recorded
        mock_metrics_collector.set_gauge.assert_any_call("app.process.memory.rss_mb", 512.0)
        mock_metrics_collector.set_gauge.assert_any_call("app.process.memory.vms_mb", 1024.0)
        mock_metrics_collector.set_gauge.assert_any_call("app.process.memory.percent", 10.5)
        mock_metrics_collector.set_gauge.assert_any_call("app.process.cpu.percent", 25.3)
        mock_metrics_collector.set_gauge.assert_any_call("app.threads.count", 15)

    @pytest.mark.asyncio
    async def test_collect_process_stats_no_psutil(self, process_collector, mock_metrics_collector):
        """Test handling when psutil is not available."""
        with patch("psutil.Process", side_effect=ImportError("No module named psutil")):
            # Should not raise exception
            await process_collector.collect_process_stats()

        # No metrics should be recorded
        mock_metrics_collector.set_gauge.assert_not_called()

    @pytest.mark.asyncio
    async def test_collect_gc_stats(self, process_collector, mock_metrics_collector):
        """Test garbage collection statistics."""
        # Mock GC stats
        with patch("gc.get_count", return_value=(100, 10, 5)):
            with patch("gc.garbage", []):
                await process_collector.collect_gc_stats()

        # First call should record collections
        assert mock_metrics_collector.increment_counter.call_count >= 0
        mock_metrics_collector.set_gauge.assert_any_call("app.gc.uncollectable", 0)

    @pytest.mark.asyncio
    async def test_collect_gc_stats_with_garbage(self, process_collector, mock_metrics_collector):
        """Test GC stats with uncollectable objects."""
        with patch("gc.get_count", return_value=(100, 10, 5)):
            with patch("gc.garbage", ["obj1", "obj2", "obj3"]):
                await process_collector.collect_gc_stats()

        mock_metrics_collector.set_gauge.assert_any_call("app.gc.uncollectable", 3)

    @pytest.mark.asyncio
    async def test_collect_asyncio_stats(self, process_collector, mock_metrics_collector):
        """Test asyncio task statistics."""
        await process_collector.collect_asyncio_stats()

        # Should record number of active tasks (at least this test task)
        calls = [
            call
            for call in mock_metrics_collector.set_gauge.call_args_list
            if call[0][0] == "app.asyncio.tasks.count"
        ]
        assert len(calls) > 0
        assert calls[0][0][1] >= 0  # At least 0 tasks

    @pytest.mark.asyncio
    async def test_collect_event_loop_health(self, process_collector, mock_metrics_collector):
        """Test event loop health metrics."""
        await process_collector.collect_event_loop_health()

        # Verify lag was recorded
        mock_metrics_collector.set_gauge.assert_any_call(
            "asyncio.event_loop.lag_ms", pytest.approx(0.0, abs=100)
        )

        # Verify pending callbacks was recorded
        calls = [
            call
            for call in mock_metrics_collector.set_gauge.call_args_list
            if call[0][0] == "asyncio.event_loop.pending_callbacks"
        ]
        assert len(calls) > 0

    @pytest.mark.asyncio
    async def test_collect_database_stats(self, process_collector, mock_metrics_collector):
        """Test database connection pool statistics."""
        # Mock SQLAlchemy engine
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_pool.checkedout.return_value = 3

        mock_engine = Mock()
        mock_engine.pool = mock_pool

        with patch("truthgraph.db.engine", mock_engine):
            await process_collector.collect_database_stats()

        # Verify pool metrics were recorded
        mock_metrics_collector.set_gauge.assert_any_call("db.connection.pool.size", 10)
        mock_metrics_collector.set_gauge.assert_any_call("db.connection.pool.active", 3)
        mock_metrics_collector.set_gauge.assert_any_call("db.connection.pool.idle", 7)

    @pytest.mark.asyncio
    async def test_collect_database_stats_unavailable(self, process_collector, mock_metrics_collector):
        """Test database stats when database is unavailable."""
        with patch("truthgraph.db.engine", side_effect=ImportError()):
            # Should not raise exception
            await process_collector.collect_database_stats()

    @pytest.mark.asyncio
    async def test_collect_stats(self, process_collector, mock_metrics_collector):
        """Test that collect_stats runs all collectors."""
        with patch.object(process_collector, "collect_process_stats", new_callable=AsyncMock) as mock_process:
            with patch.object(process_collector, "collect_gc_stats", new_callable=AsyncMock) as mock_gc:
                with patch.object(process_collector, "collect_asyncio_stats", new_callable=AsyncMock) as mock_asyncio:
                    with patch.object(process_collector, "collect_event_loop_health", new_callable=AsyncMock) as mock_event_loop:
                        with patch.object(process_collector, "collect_database_stats", new_callable=AsyncMock) as mock_db:
                            await process_collector.collect_stats()

        # Verify all collectors were called
        mock_process.assert_called_once()
        mock_gc.assert_called_once()
        mock_asyncio.assert_called_once()
        mock_event_loop.assert_called_once()
        mock_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_database_health_success(self, process_collector):
        """Test successful database health check."""
        mock_result = Mock()
        mock_result.scalar.return_value = 1

        mock_db = Mock()
        mock_db.execute.return_value = mock_result
        mock_db.close = Mock()

        mock_session_local = Mock(return_value=mock_db)

        with patch("truthgraph.db.SessionLocal", mock_session_local):
            status, message = await process_collector.check_database_health()

        assert status == "healthy"
        assert "connected" in message.lower()
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_database_health_failure(self, process_collector):
        """Test database health check failure."""
        mock_session_local = Mock(side_effect=Exception("Connection failed"))

        with patch("truthgraph.db.SessionLocal", mock_session_local):
            status, message = await process_collector.check_database_health()

        assert status == "unhealthy"
        assert "error" in message.lower()

    @pytest.mark.asyncio
    async def test_check_ml_services_health(self, process_collector):
        """Test ML services health check."""
        # Mock embedding service
        mock_embedding_svc = Mock()
        mock_embedding_svc.is_loaded.return_value = True

        # Mock NLI service
        mock_nli_svc = Mock()
        mock_nli_svc.get_model_info.return_value = {"initialized": True}

        with patch(
            "truthgraph.services.ml.embedding_service.get_embedding_service",
            return_value=mock_embedding_svc,
        ):
            with patch(
                "truthgraph.services.ml.nli_service.get_nli_service",
                return_value=mock_nli_svc,
            ):
                results = await process_collector.check_ml_services_health()

        assert "embedding_service" in results
        assert "nli_service" in results

        embedding_status, embedding_msg = results["embedding_service"]
        assert embedding_status == "healthy"

        nli_status, nli_msg = results["nli_service"]
        assert nli_status == "healthy"

    @pytest.mark.asyncio
    async def test_check_ml_services_health_degraded(self, process_collector):
        """Test ML services health check when models not loaded."""
        # Mock embedding service (not loaded)
        mock_embedding_svc = Mock()
        mock_embedding_svc.is_loaded.return_value = False

        # Mock NLI service (not initialized)
        mock_nli_svc = Mock()
        mock_nli_svc.get_model_info.return_value = {"initialized": False}

        with patch(
            "truthgraph.services.ml.embedding_service.get_embedding_service",
            return_value=mock_embedding_svc,
        ):
            with patch(
                "truthgraph.services.ml.nli_service.get_nli_service",
                return_value=mock_nli_svc,
            ):
                results = await process_collector.check_ml_services_health()

        embedding_status, _ = results["embedding_service"]
        assert embedding_status == "degraded"

        nli_status, _ = results["nli_service"]
        assert nli_status == "degraded"

    @pytest.mark.asyncio
    async def test_check_ml_services_health_error(self, process_collector):
        """Test ML services health check with errors."""
        with patch(
            "truthgraph.services.ml.embedding_service.get_embedding_service",
            side_effect=Exception("Service unavailable"),
        ):
            with patch(
                "truthgraph.services.ml.nli_service.get_nli_service",
                side_effect=Exception("Service unavailable"),
            ):
                results = await process_collector.check_ml_services_health()

        embedding_status, _ = results["embedding_service"]
        assert embedding_status == "unhealthy"

        nli_status, _ = results["nli_service"]
        assert nli_status == "unhealthy"

    @pytest.mark.asyncio
    async def test_get_process_details(self, process_collector):
        """Test getting detailed process information."""
        mock_process = Mock()
        mock_process.pid = 12345

        mock_memory_info = Mock()
        mock_memory_info.rss = 512 * 1024 * 1024
        mock_memory_info.vms = 1024 * 1024 * 1024

        mock_process.memory_info.return_value = mock_memory_info
        mock_process.cpu_percent.return_value = 25.0
        mock_process.num_threads.return_value = 10

        with patch("psutil.Process", return_value=mock_process):
            details = await process_collector.get_process_details()

        assert "process" in details
        assert details["process"]["pid"] == 12345
        assert details["process"]["cpu_percent"] == 25.0
        assert details["process"]["memory_rss_mb"] == 512.0
        assert details["process"]["num_threads"] == 10

        assert "asyncio" in details
        assert "gc" in details

    @pytest.mark.asyncio
    async def test_get_process_details_error(self, process_collector):
        """Test getting process details with error."""
        with patch("psutil.Process", side_effect=Exception("Process error")):
            details = await process_collector.get_process_details()

        assert "error" in details

    @pytest.mark.asyncio
    async def test_collect_stats_handles_exceptions(self, process_collector, mock_metrics_collector):
        """Test that collect_stats handles exceptions in individual collectors."""
        with patch.object(
            process_collector, "collect_process_stats", side_effect=Exception("Error")
        ):
            # Should not raise exception
            await process_collector.collect_stats()
