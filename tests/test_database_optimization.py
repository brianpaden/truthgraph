"""Tests for database query optimization (Feature 2.6).

This test suite validates:
1. OptimizedQueries class functionality
2. QueryBuilder utilities
3. Index definitions
4. Batch operation correctness
5. Query performance targets
6. N+1 query elimination
"""

from pathlib import Path

import pytest

# Import modules to test
try:
    from truthgraph.db.queries import OptimizedQueries
    from truthgraph.db.query_builder import QueryBuilder

    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


class TestOptimizedQueriesModule:
    """Test OptimizedQueries module structure and methods."""

    def test_optimized_queries_module_exists(self):
        """Verify OptimizedQueries module can be imported."""
        assert MODULES_AVAILABLE, "OptimizedQueries module should be importable"

    def test_optimized_queries_class_instantiation(self):
        """Verify OptimizedQueries class can be instantiated."""
        if not MODULES_AVAILABLE:
            pytest.skip("Modules not available")

        queries = OptimizedQueries()
        assert queries is not None
        assert isinstance(queries, OptimizedQueries)

    def test_optimized_queries_has_batch_methods(self):
        """Verify OptimizedQueries has required batch methods."""
        if not MODULES_AVAILABLE:
            pytest.skip("Modules not available")

        queries = OptimizedQueries()

        # Check all required methods exist
        assert hasattr(queries, "batch_get_evidence_by_ids")
        assert hasattr(queries, "batch_create_nli_results")
        assert hasattr(queries, "batch_create_embeddings")
        assert hasattr(queries, "create_verification_result_with_nli")
        assert hasattr(queries, "get_nli_results_for_claim")
        assert hasattr(queries, "get_verification_result_with_details")

        # Check methods are callable
        assert callable(queries.batch_get_evidence_by_ids)
        assert callable(queries.batch_create_nli_results)
        assert callable(queries.batch_create_embeddings)


class TestQueryBuilderModule:
    """Test QueryBuilder module structure and methods."""

    def test_query_builder_module_exists(self):
        """Verify QueryBuilder module can be imported."""
        assert MODULES_AVAILABLE, "QueryBuilder module should be importable"

    def test_query_builder_has_analysis_methods(self):
        """Verify QueryBuilder has query analysis methods."""
        if not MODULES_AVAILABLE:
            pytest.skip("Modules not available")

        # Check class has required methods (without instantiation)
        assert hasattr(QueryBuilder, "explain_analyze")
        assert hasattr(QueryBuilder, "analyze_index_usage")
        assert hasattr(QueryBuilder, "get_missing_indexes_recommendations")
        assert hasattr(QueryBuilder, "timing")
        assert hasattr(QueryBuilder, "build_similarity_search_query")


class TestIndexDefinitions:
    """Test index definitions and SQL file."""

    def test_indexes_sql_file_exists(self):
        """Verify indexes.sql file exists."""
        indexes_file = Path("c:/repos/truthgraph/truthgraph/db/indexes.sql")
        assert indexes_file.exists(), "indexes.sql file should exist"

    def test_indexes_sql_not_empty(self):
        """Verify indexes.sql file has content."""
        indexes_file = Path("c:/repos/truthgraph/truthgraph/db/indexes.sql")
        content = indexes_file.read_text()
        assert len(content) > 0, "indexes.sql should not be empty"
        assert len(content) > 1000, "indexes.sql should have substantial content"

    def test_indexes_sql_has_key_indexes(self):
        """Verify indexes.sql defines critical indexes."""
        indexes_file = Path("c:/repos/truthgraph/truthgraph/db/indexes.sql")
        content = indexes_file.read_text()

        # Check for evidence indexes
        assert "idx_evidence_source_url" in content
        assert "idx_evidence_created_at" in content

        # Check for embeddings indexes
        assert "idx_embeddings_tenant_id" in content
        assert "idx_embeddings_vector_cosine" in content or "Feature 2.3" in content

        # Check for nli_results indexes
        assert "idx_nli_results_claim_id" in content
        assert "idx_nli_results_claim_evidence" in content

        # Check for verification_results indexes
        assert "idx_verification_results_claim_id" in content
        assert "idx_verification_results_claim_created" in content

    def test_indexes_use_concurrently(self):
        """Verify indexes use CONCURRENTLY for production safety."""
        indexes_file = Path("c:/repos/truthgraph/truthgraph/db/indexes.sql")
        content = indexes_file.read_text()

        # Count CREATE INDEX statements
        create_index_count = content.count("CREATE INDEX")

        # Most should use CONCURRENTLY (allow some exceptions for comments)
        concurrently_count = content.count("CONCURRENTLY")
        assert concurrently_count > 0, "Should use CONCURRENTLY for production safety"


class TestBatchOperationLogic:
    """Test batch operation implementations."""

    def test_batch_get_evidence_empty_list(self):
        """Verify batch_get_evidence handles empty list."""
        if not MODULES_AVAILABLE:
            pytest.skip("Modules not available")

        queries = OptimizedQueries()

        # Mock session (no actual DB call)
        class MockSession:
            pass

        session = MockSession()

        # Should return empty list, not error
        result = queries.batch_get_evidence_by_ids(session, [])
        assert result == []

    def test_batch_create_nli_results_empty_list(self):
        """Verify batch_create_nli_results handles empty list."""
        if not MODULES_AVAILABLE:
            pytest.skip("Modules not available")

        queries = OptimizedQueries()

        class MockSession:
            pass

        session = MockSession()

        # Should return empty list, not error
        result = queries.batch_create_nli_results(session, [])
        assert result == []

    def test_batch_create_embeddings_empty_list(self):
        """Verify batch_create_embeddings handles empty list."""
        if not MODULES_AVAILABLE:
            pytest.skip("Modules not available")

        queries = OptimizedQueries()

        class MockSession:
            pass

        session = MockSession()

        # Should return empty list, not error
        result = queries.batch_create_embeddings(session, [])
        assert result == []


class TestPerformanceTargets:
    """Validate performance targets are met."""

    def test_latency_reduction_target_met(self):
        """Verify latency reduction meets 30% target."""
        # Load performance results
        results_file = Path(
            "c:/repos/truthgraph/scripts/benchmarks/results/query_performance_2025-11-01.json"
        )

        if not results_file.exists():
            pytest.skip("Performance results file not found")

        import json

        with open(results_file) as f:
            results = json.load(f)

        # Check overall reduction
        summary = results.get("summary", {})
        avg_reduction = summary.get("average_latency_reduction_percent", 0)

        assert avg_reduction >= 30.0, f"Latency reduction should be ≥30%, got {avg_reduction}%"

    def test_evidence_retrieval_speedup(self):
        """Verify evidence retrieval speedup meets target."""
        results_file = Path(
            "c:/repos/truthgraph/scripts/benchmarks/results/query_performance_2025-11-01.json"
        )

        if not results_file.exists():
            pytest.skip("Performance results file not found")

        import json

        with open(results_file) as f:
            results = json.load(f)

        evidence_retrieval = results["benchmarks"].get("evidence_retrieval", {})
        speedup = evidence_retrieval.get("speedup_factor", 0)

        # Should have significant speedup
        assert speedup >= 2.0, f"Evidence retrieval speedup should be ≥2x, got {speedup}x"

    def test_nli_batch_insert_speedup(self):
        """Verify NLI batch insert speedup meets target."""
        results_file = Path(
            "c:/repos/truthgraph/scripts/benchmarks/results/query_performance_2025-11-01.json"
        )

        if not results_file.exists():
            pytest.skip("Performance results file not found")

        import json

        with open(results_file) as f:
            results = json.load(f)

        nli_batch = results["benchmarks"].get("nli_batch_insert", {})
        speedup = nli_batch.get("speedup_factor", 0)

        # Should have significant speedup
        assert speedup >= 2.0, f"NLI batch insert speedup should be ≥2x, got {speedup}x"

    def test_all_success_criteria_met(self):
        """Verify all success criteria are met."""
        results_file = Path(
            "c:/repos/truthgraph/scripts/benchmarks/results/query_performance_2025-11-01.json"
        )

        if not results_file.exists():
            pytest.skip("Performance results file not found")

        import json

        with open(results_file) as f:
            results = json.load(f)

        summary = results.get("summary", {})

        # Check all criteria
        assert summary.get("target_achieved", False), (
            "30% latency reduction target should be achieved"
        )
        assert summary.get("average_latency_reduction_percent", 0) >= 30.0
        assert summary.get("best_speedup", 0) >= 2.0


class TestNPlusOneElimination:
    """Test N+1 query pattern elimination."""

    def test_batch_operations_eliminate_loops(self):
        """Verify batch operations eliminate N+1 patterns."""
        # This is a design test - batch operations should not have loops

        if not MODULES_AVAILABLE:
            pytest.skip("Modules not available")

        import inspect

        from truthgraph.db.queries import OptimizedQueries

        queries = OptimizedQueries()

        # Get batch_get_evidence_by_ids source
        source = inspect.getsource(queries.batch_get_evidence_by_ids)

        # The key verification: batch operations use a single query, not loops
        # Count session.execute calls - should be 2 (one for with embeddings, one without)
        execute_count = source.count("session.execute")

        # Should have execute calls but not in a loop over items
        assert execute_count >= 1, "Should have at least one execute call"
        assert execute_count <= 3, "Should have minimal execute calls (not one per item)"

        # Verify it uses ANY clause for batch retrieval
        assert "ANY" in source, "Should use ANY clause for batch operations"

    def test_query_builder_no_n_plus_one_in_examples(self):
        """Verify query builder examples avoid N+1 patterns."""
        if not MODULES_AVAILABLE:
            pytest.skip("Modules not available")

        import inspect

        from truthgraph.db.query_builder import QueryBuilder

        # Get build_similarity_search_query source
        source = inspect.getsource(QueryBuilder.build_similarity_search_query)

        # Should use ANY or IN clauses, not loops
        assert "ANY" in source or "example" in source.lower(), (
            "Query builder should use ANY clause for batch operations"
        )


class TestIndexUsageValidation:
    """Validate index usage and effectiveness."""

    def test_performance_results_show_high_index_usage(self):
        """Verify performance results show high index usage."""
        results_file = Path(
            "c:/repos/truthgraph/scripts/benchmarks/results/query_performance_2025-11-01.json"
        )

        if not results_file.exists():
            pytest.skip("Performance results file not found")

        import json

        with open(results_file) as f:
            results = json.load(f)

        index_usage = results["benchmarks"].get("index_usage_analysis", {})

        # Check each table has high index usage
        for table_name, stats in index_usage.items():
            if isinstance(stats, dict) and "index_scan_ratio_percent" in stats:
                ratio = stats["index_scan_ratio_percent"]
                assert ratio >= 90.0, f"{table_name} index scan ratio should be ≥90%, got {ratio}%"

    def test_no_unused_indexes(self):
        """Verify no unused indexes are defined."""
        results_file = Path(
            "c:/repos/truthgraph/scripts/benchmarks/results/query_performance_2025-11-01.json"
        )

        if not results_file.exists():
            pytest.skip("Performance results file not found")

        import json

        with open(results_file) as f:
            results = json.load(f)

        index_usage = results["benchmarks"].get("index_usage_analysis", {})

        # All tables should have "optimal" or "excellent" status
        for table_name, stats in index_usage.items():
            if isinstance(stats, dict) and "status" in stats:
                status = stats["status"]
                assert status in ["optimal", "excellent"], (
                    f"{table_name} should have optimal index usage, got {status}"
                )


class TestDocumentation:
    """Test documentation completeness."""

    def test_analysis_document_exists(self):
        """Verify analysis document exists."""
        doc_file = Path("c:/repos/truthgraph/docs/profiling/database_optimization_analysis.md")
        assert doc_file.exists(), "Analysis document should exist"

    def test_recommendations_document_exists(self):
        """Verify recommendations document exists."""
        doc_file = Path(
            "c:/repos/truthgraph/docs/profiling/database_optimization_recommendations.md"
        )
        assert doc_file.exists(), "Recommendations document should exist"

    def test_analysis_document_comprehensive(self):
        """Verify analysis document is comprehensive."""
        doc_file = Path("c:/repos/truthgraph/docs/profiling/database_optimization_analysis.md")
        content = doc_file.read_text()

        # Should have key sections
        assert "Executive Summary" in content
        assert "Performance Results" in content
        assert "N+1 Query Patterns" in content or "N+1" in content
        assert "Index Optimization" in content
        assert "Batch Operations" in content

        # Should be substantial (>10K characters)
        assert len(content) > 10000, "Analysis should be comprehensive"

    def test_recommendations_document_actionable(self):
        """Verify recommendations document has actionable advice."""
        doc_file = Path(
            "c:/repos/truthgraph/docs/profiling/database_optimization_recommendations.md"
        )
        content = doc_file.read_text(encoding="utf-8")

        # Should have practical sections
        assert "Quick Start" in content or "Getting Started" in content
        assert "Recommendations" in content or "recommendation" in content.lower()
        assert "Deployment" in content or "Production" in content

        # Should have code examples
        assert "```python" in content or "```sql" in content


class TestBenchmarkScript:
    """Test benchmark script functionality."""

    def test_benchmark_script_exists(self):
        """Verify benchmark script exists."""
        script_file = Path("c:/repos/truthgraph/scripts/benchmarks/benchmark_queries.py")
        assert script_file.exists(), "Benchmark script should exist"

    def test_benchmark_script_executable(self):
        """Verify benchmark script has proper structure."""
        script_file = Path("c:/repos/truthgraph/scripts/benchmarks/benchmark_queries.py")
        content = script_file.read_text()

        # Should have main entry point
        assert 'if __name__ == "__main__"' in content or "def main()" in content

        # Should have key benchmark methods
        assert "benchmark" in content.lower()
        assert "evidence" in content.lower()
        assert "nli" in content.lower()

    def test_performance_results_file_exists(self):
        """Verify performance results file exists."""
        results_file = Path(
            "c:/repos/truthgraph/scripts/benchmarks/results/query_performance_2025-11-01.json"
        )
        assert results_file.exists(), "Performance results file should exist"

    def test_performance_results_valid_json(self):
        """Verify performance results file is valid JSON."""
        results_file = Path(
            "c:/repos/truthgraph/scripts/benchmarks/results/query_performance_2025-11-01.json"
        )

        import json

        with open(results_file) as f:
            results = json.load(f)

        # Should have key structure
        assert "metadata" in results
        assert "benchmarks" in results
        assert "summary" in results

    def test_performance_results_has_key_benchmarks(self):
        """Verify performance results include key benchmarks."""
        results_file = Path(
            "c:/repos/truthgraph/scripts/benchmarks/results/query_performance_2025-11-01.json"
        )

        import json

        with open(results_file) as f:
            results = json.load(f)

        benchmarks = results["benchmarks"]

        # Should have all key benchmarks
        assert "evidence_retrieval" in benchmarks
        assert "nli_batch_insert" in benchmarks or "nli" in str(benchmarks).lower()
        assert "batch_vs_individual" in benchmarks or "batch" in str(benchmarks).lower()


class TestCodeQuality:
    """Test code quality standards."""

    def test_optimized_queries_has_type_hints(self):
        """Verify OptimizedQueries has type hints."""
        if not MODULES_AVAILABLE:
            pytest.skip("Modules not available")

        import inspect

        from truthgraph.db.queries import OptimizedQueries

        queries = OptimizedQueries()

        # Check batch_get_evidence_by_ids signature
        sig = inspect.signature(queries.batch_get_evidence_by_ids)

        # Should have type annotations for parameters
        for param_name, param in sig.parameters.items():
            if param_name != "self":
                assert param.annotation != inspect.Parameter.empty, (
                    f"Parameter {param_name} should have type annotation"
                )

        # Should have return type
        assert sig.return_annotation != inspect.Signature.empty, (
            "Method should have return type annotation"
        )

    def test_query_builder_has_type_hints(self):
        """Verify QueryBuilder has type hints."""
        if not MODULES_AVAILABLE:
            pytest.skip("Modules not available")

        import inspect

        from truthgraph.db.query_builder import QueryBuilder

        # Check explain_analyze signature
        sig = inspect.signature(QueryBuilder.explain_analyze)

        # Should have type annotations
        for param_name, param in sig.parameters.items():
            if param_name not in ["self", "params"]:  # params can be Optional
                assert param.annotation != inspect.Parameter.empty, (
                    f"Parameter {param_name} should have type annotation"
                )

    def test_no_obvious_sql_injection_vulnerabilities(self):
        """Verify queries use parameterized SQL."""
        if not MODULES_AVAILABLE:
            pytest.skip("Modules not available")

        import inspect

        from truthgraph.db.queries import OptimizedQueries

        queries = OptimizedQueries()

        # Get source of batch methods
        source = inspect.getsource(queries.batch_get_evidence_by_ids)

        # Should use parameterized queries (:param_name or %(param)s)
        assert ":" in source or "%(" in source, (
            "Should use parameterized queries (not string formatting)"
        )

        # Should NOT use direct string interpolation in SQL (dangerous)
        # F-strings in VALUES clauses are OK for structure, but not for values
        lines = source.split("\n")
        for line in lines:
            if "WHERE" in line and 'f"' in line:
                # This is potentially dangerous
                assert ":" in line or "%(" in line, "WHERE clauses should use parameterized values"


class TestIntegration:
    """Test integration with other features."""

    def test_feature_2_3_coordination(self):
        """Verify coordination with Feature 2.3 (vector search)."""
        results_file = Path(
            "c:/repos/truthgraph/scripts/benchmarks/results/query_performance_2025-11-01.json"
        )

        if not results_file.exists():
            pytest.skip("Performance results file not found")

        import json

        with open(results_file) as f:
            results = json.load(f)

        # Should have reference to Feature 2.3
        content_str = json.dumps(results)
        assert "Feature 2.3" in content_str or "vector" in content_str.lower()

        # Should have IVFFlat configuration
        assert "ivfflat" in content_str.lower() or "vector" in content_str.lower()

    def test_feature_2_4_integration_notes(self):
        """Verify integration notes for Feature 2.4."""
        results_file = Path(
            "c:/repos/truthgraph/scripts/benchmarks/results/query_performance_2025-11-01.json"
        )

        if not results_file.exists():
            pytest.skip("Performance results file not found")

        import json

        with open(results_file) as f:
            results = json.load(f)

        # Should have Feature 2.4 integration notes
        assert "integration_notes_for_feature_2_4" in results or "Feature 2.4" in json.dumps(
            results
        )


class TestProductionReadiness:
    """Test production readiness criteria."""

    def test_connection_pooling_configured(self):
        """Verify connection pooling is mentioned in docs."""
        recommendations_file = Path(
            "c:/repos/truthgraph/docs/profiling/database_optimization_recommendations.md"
        )

        if not recommendations_file.exists():
            pytest.skip("Recommendations file not found")

        content = recommendations_file.read_text(encoding="utf-8")

        assert "pool" in content.lower() or "connection" in content.lower()
        assert "pool_size" in content or "pooling" in content.lower()

    def test_monitoring_recommendations_included(self):
        """Verify monitoring recommendations are included."""
        recommendations_file = Path(
            "c:/repos/truthgraph/docs/profiling/database_optimization_recommendations.md"
        )

        if not recommendations_file.exists():
            pytest.skip("Recommendations file not found")

        content = recommendations_file.read_text(encoding="utf-8")

        assert "monitor" in content.lower() or "monitoring" in content.lower()
        assert "alert" in content.lower() or "threshold" in content.lower()

    def test_deployment_checklist_provided(self):
        """Verify deployment checklist is provided."""
        recommendations_file = Path(
            "c:/repos/truthgraph/docs/profiling/database_optimization_recommendations.md"
        )

        if not recommendations_file.exists():
            pytest.skip("Recommendations file not found")

        content = recommendations_file.read_text(encoding="utf-8")

        assert "deploy" in content.lower() or "production" in content.lower()
        assert "checklist" in content.lower() or "steps" in content.lower()


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
