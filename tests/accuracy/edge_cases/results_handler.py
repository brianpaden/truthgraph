"""Results handler for edge case validation tests.

This module provides aggregation, storage, and reporting functionality for
edge case test results with comprehensive metrics and analysis.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EdgeCaseTestResult(BaseModel):
    """Model for individual edge case test result."""

    claim_id: str
    claim_text: str
    edge_case_types: List[str]
    expected_verdict: str
    predicted_verdict: Optional[str] = None
    confidence_score: Optional[float] = None
    passed: Optional[bool] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EdgeCaseAggregatedResults(BaseModel):
    """Model for aggregated edge case test results."""

    timestamp: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    pass_rate: float
    results_by_category: Dict[str, Dict[str, Any]]
    results_by_verdict: Dict[str, Dict[str, Any]]
    edge_case_handling_metrics: Dict[str, Any]
    individual_results: List[EdgeCaseTestResult]


class EdgeCaseResultsHandler:
    """Handler for aggregating and managing edge case test results."""

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize results handler.

        Args:
            output_dir: Directory to save results. Defaults to tests/accuracy/edge_cases/results
        """
        if output_dir is None:
            output_dir = Path(__file__).parent / "results"

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[EdgeCaseTestResult] = []

    def add_result(
        self,
        claim_id: str,
        claim_text: str,
        edge_case_types: List[str],
        expected_verdict: str,
        predicted_verdict: Optional[str] = None,
        confidence_score: Optional[float] = None,
        error: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        **metadata,
    ) -> None:
        """Add a single test result.

        Args:
            claim_id: Unique claim identifier
            claim_text: The claim text
            edge_case_types: List of edge case categories
            expected_verdict: Expected verdict
            predicted_verdict: Actual predicted verdict
            confidence_score: Confidence of prediction (0-1)
            error: Error message if test failed
            execution_time_ms: Execution time in milliseconds
            **metadata: Additional metadata fields
        """
        # Determine if test passed
        passed = None
        if error:
            passed = False
        elif predicted_verdict is not None:
            passed = predicted_verdict == expected_verdict

        result = EdgeCaseTestResult(
            claim_id=claim_id,
            claim_text=claim_text,
            edge_case_types=edge_case_types,
            expected_verdict=expected_verdict,
            predicted_verdict=predicted_verdict,
            confidence_score=confidence_score,
            passed=passed,
            error=error,
            execution_time_ms=execution_time_ms,
            metadata=metadata,
        )

        self.results.append(result)

    def aggregate_results(
        self, test_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Aggregate edge case test results.

        Args:
            test_results: Optional list of test result dictionaries.
                         Uses stored results if not provided.

        Returns:
            Aggregated results dictionary
        """
        # Use provided results or stored results
        if test_results is not None:
            self.results = [EdgeCaseTestResult(**r) for r in test_results]

        if not self.results:
            return self._empty_results()

        # Calculate overall statistics
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed is True)
        failed = sum(1 for r in self.results if r.passed is False and not r.error)
        errors = sum(1 for r in self.results if r.error is not None)

        # Aggregate by edge case category
        category_results = self._aggregate_by_category()

        # Aggregate by expected verdict
        verdict_results = self._aggregate_by_verdict()

        # Calculate edge case handling metrics
        edge_metrics = self._calculate_edge_case_metrics()

        # Create aggregated results
        aggregated = EdgeCaseAggregatedResults(
            timestamp=datetime.now().isoformat(),
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            error_tests=errors,
            pass_rate=passed / total if total > 0 else 0.0,
            results_by_category=category_results,
            results_by_verdict=verdict_results,
            edge_case_handling_metrics=edge_metrics,
            individual_results=self.results,
        )

        return aggregated.model_dump()

    def save_results(
        self, results: Optional[Dict[str, Any]] = None, output_path: Optional[str] = None
    ) -> str:
        """Save results to JSON file.

        Args:
            results: Results dictionary to save. Uses aggregated results if not provided.
            output_path: Output file path. Uses default if not provided.

        Returns:
            Path to saved file
        """
        if results is None:
            results = self.aggregate_results()

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(self.output_dir / f"edge_case_results_{timestamp}.json")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert to JSON-serializable format
        serializable_results = self._make_json_serializable(results)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)

        return str(output_file)

    def generate_summary(self, results: Optional[Dict[str, Any]] = None) -> str:
        """Generate human-readable summary of results.

        Args:
            results: Results dictionary. Uses aggregated results if not provided.

        Returns:
            Formatted summary string
        """
        if results is None:
            results = self.aggregate_results()

        summary_parts = []

        # Header
        summary_parts.append("=" * 80)
        summary_parts.append("EDGE CASE VALIDATION RESULTS SUMMARY")
        summary_parts.append("=" * 80)
        summary_parts.append(f"Timestamp: {results.get('timestamp', 'N/A')}")
        summary_parts.append("")

        # Overall statistics
        summary_parts.append("Overall Statistics:")
        summary_parts.append(f"  Total Tests: {results.get('total_tests', 0)}")
        summary_parts.append(f"  Passed: {results.get('passed_tests', 0)}")
        summary_parts.append(f"  Failed: {results.get('failed_tests', 0)}")
        summary_parts.append(f"  Errors: {results.get('error_tests', 0)}")
        summary_parts.append(f"  Pass Rate: {results.get('pass_rate', 0) * 100:.2f}%")
        summary_parts.append("")

        # Results by edge case category
        summary_parts.append("Results by Edge Case Category:")
        category_results = results.get("results_by_category", {})
        for category, stats in sorted(category_results.items()):
            summary_parts.append(f"  {category}:")
            summary_parts.append(f"    Tests: {stats.get('total', 0)}")
            summary_parts.append(f"    Passed: {stats.get('passed', 0)}")
            summary_parts.append(
                f"    Pass Rate: {stats.get('pass_rate', 0) * 100:.2f}%"
            )

        summary_parts.append("")

        # Results by expected verdict
        summary_parts.append("Results by Expected Verdict:")
        verdict_results = results.get("results_by_verdict", {})
        for verdict, stats in sorted(verdict_results.items()):
            summary_parts.append(f"  {verdict}:")
            summary_parts.append(f"    Tests: {stats.get('total', 0)}")
            summary_parts.append(f"    Passed: {stats.get('passed', 0)}")
            summary_parts.append(
                f"    Pass Rate: {stats.get('pass_rate', 0) * 100:.2f}%"
            )

        summary_parts.append("")

        # Edge case handling metrics
        summary_parts.append("Edge Case Handling Metrics:")
        edge_metrics = results.get("edge_case_handling_metrics", {})
        summary_parts.append(
            f"  Avg Confidence: {edge_metrics.get('avg_confidence', 0):.4f}"
        )
        summary_parts.append(
            f"  Avg Execution Time: {edge_metrics.get('avg_execution_time_ms', 0):.2f} ms"
        )
        summary_parts.append(
            f"  Error Rate: {edge_metrics.get('error_rate', 0) * 100:.2f}%"
        )

        summary_parts.append("")
        summary_parts.append("=" * 80)

        return "\n".join(summary_parts)

    def load_results(self, results_path: str) -> Dict[str, Any]:
        """Load results from JSON file.

        Args:
            results_path: Path to results file

        Returns:
            Loaded results dictionary
        """
        with open(results_path, "r", encoding="utf-8") as f:
            results = json.load(f)

        # Reconstruct EdgeCaseTestResult objects if present
        if "individual_results" in results:
            self.results = [
                EdgeCaseTestResult(**r) for r in results["individual_results"]
            ]

        return results

    def clear_results(self) -> None:
        """Clear all stored results."""
        self.results = []

    def _aggregate_by_category(self) -> Dict[str, Dict[str, Any]]:
        """Aggregate results by edge case category.

        Returns:
            Dictionary mapping category to statistics
        """
        category_stats: Dict[str, Dict[str, Any]] = {}

        for result in self.results:
            for category in result.edge_case_types:
                if category not in category_stats:
                    category_stats[category] = {
                        "total": 0,
                        "passed": 0,
                        "failed": 0,
                        "errors": 0,
                    }

                category_stats[category]["total"] += 1
                if result.passed is True:
                    category_stats[category]["passed"] += 1
                elif result.error:
                    category_stats[category]["errors"] += 1
                else:
                    category_stats[category]["failed"] += 1

        # Calculate pass rates
        for category, stats in category_stats.items():
            total = stats["total"]
            stats["pass_rate"] = stats["passed"] / total if total > 0 else 0.0

        return category_stats

    def _aggregate_by_verdict(self) -> Dict[str, Dict[str, Any]]:
        """Aggregate results by expected verdict.

        Returns:
            Dictionary mapping verdict to statistics
        """
        verdict_stats: Dict[str, Dict[str, Any]] = {}

        for result in self.results:
            verdict = result.expected_verdict
            if verdict not in verdict_stats:
                verdict_stats[verdict] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "errors": 0,
                }

            verdict_stats[verdict]["total"] += 1
            if result.passed is True:
                verdict_stats[verdict]["passed"] += 1
            elif result.error:
                verdict_stats[verdict]["errors"] += 1
            else:
                verdict_stats[verdict]["failed"] += 1

        # Calculate pass rates
        for verdict, stats in verdict_stats.items():
            total = stats["total"]
            stats["pass_rate"] = stats["passed"] / total if total > 0 else 0.0

        return verdict_stats

    def _calculate_edge_case_metrics(self) -> Dict[str, Any]:
        """Calculate edge case handling metrics.

        Returns:
            Dictionary with edge case metrics
        """
        if not self.results:
            return {}

        # Filter out results with errors for accuracy metrics
        valid_results = [r for r in self.results if r.predicted_verdict is not None]

        # Calculate average confidence
        confidences = [
            r.confidence_score for r in valid_results if r.confidence_score is not None
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Calculate average execution time
        exec_times = [
            r.execution_time_ms
            for r in self.results
            if r.execution_time_ms is not None
        ]
        avg_exec_time = sum(exec_times) / len(exec_times) if exec_times else 0.0

        # Calculate error rate
        total = len(self.results)
        errors = sum(1 for r in self.results if r.error is not None)
        error_rate = errors / total if total > 0 else 0.0

        return {
            "avg_confidence": avg_confidence,
            "avg_execution_time_ms": avg_exec_time,
            "error_rate": error_rate,
            "total_valid_predictions": len(valid_results),
            "total_errors": errors,
        }

    def _empty_results(self) -> Dict[str, Any]:
        """Create empty results structure.

        Returns:
            Empty results dictionary
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "error_tests": 0,
            "pass_rate": 0.0,
            "results_by_category": {},
            "results_by_verdict": {},
            "edge_case_handling_metrics": {},
            "individual_results": [],
        }

    @staticmethod
    def _make_json_serializable(obj: Any) -> Any:
        """Convert object to JSON-serializable format.

        Args:
            obj: Object to convert

        Returns:
            JSON-serializable version
        """
        if isinstance(obj, dict):
            return {k: EdgeCaseResultsHandler._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [EdgeCaseResultsHandler._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (BaseModel,)):
            return obj.model_dump()
        elif hasattr(obj, "item"):  # numpy types
            return obj.item()
        elif isinstance(obj, float):
            return round(obj, 6)
        else:
            return obj
