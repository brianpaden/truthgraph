"""Utilities for robustness testing framework.

This module provides core functionality for:
- Running robustness tests
- Measuring accuracy degradation
- Analyzing vulnerability patterns
- Generating robustness reports
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RobustnessMetrics:
    """Metrics for measuring robustness across dimensions."""

    dimension: str
    base_accuracy: float
    variant_accuracy: float
    accuracy_degradation: float = field(default=0.0, init=False)
    confidence_variance: float = 0.0
    test_count: int = 0
    correct_count: int = 0
    failed_variants: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Calculate derived metrics after initialization."""
        self.accuracy_degradation = self.base_accuracy - self.variant_accuracy

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)


@dataclass
class RobustnessResult:
    """Result of a robustness test."""

    test_id: str
    dimension: str
    base_claim: str
    expected_verdict: str
    category: str
    variant_claim: str
    predicted_verdict: str
    confidence: float
    is_correct: bool
    variant_type: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return asdict(self)


class RobustnessAnalyzer:
    """Analyzer for robustness test results."""

    def __init__(self, results_dir: str = "tests/robustness/results"):
        """Initialize robustness analyzer.

        Args:
            results_dir: Directory to store results
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[RobustnessResult] = []
        self.metrics_by_dimension: Dict[str, RobustnessMetrics] = {}

    def add_result(self, result: RobustnessResult) -> None:
        """Add a test result.

        Args:
            result: RobustnessResult to add
        """
        self.results.append(result)
        logger.debug(
            "added_robustness_result",
            test_id=result.test_id,
            dimension=result.dimension,
            is_correct=result.is_correct,
        )

    def calculate_dimension_metrics(
        self,
        dimension: str,
        base_accuracy: float,
    ) -> RobustnessMetrics:
        """Calculate metrics for a dimension.

        Args:
            dimension: Robustness dimension name
            base_accuracy: Baseline accuracy without variants

        Returns:
            RobustnessMetrics for the dimension
        """
        dimension_results = [r for r in self.results if r.dimension == dimension]

        if not dimension_results:
            return RobustnessMetrics(
                dimension=dimension,
                base_accuracy=base_accuracy,
                variant_accuracy=0.0,
            )

        correct = sum(1 for r in dimension_results if r.is_correct)
        total = len(dimension_results)
        variant_accuracy = correct / total if total > 0 else 0.0

        # Calculate confidence variance
        confidences = [r.confidence for r in dimension_results]
        mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        confidence_variance = (
            sum((c - mean_confidence) ** 2 for c in confidences) / len(confidences)
            if confidences
            else 0.0
        )

        metrics = RobustnessMetrics(
            dimension=dimension,
            base_accuracy=base_accuracy,
            variant_accuracy=variant_accuracy,
            confidence_variance=confidence_variance,
            test_count=total,
            correct_count=correct,
            failed_variants=[
                r.test_id for r in dimension_results if not r.is_correct
            ],
        )

        self.metrics_by_dimension[dimension] = metrics
        return metrics

    def identify_vulnerabilities(
        self,
        threshold: float = 0.15,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Identify vulnerability areas based on accuracy degradation.

        Args:
            threshold: Degradation threshold (default 15%)

        Returns:
            Dictionary mapping vulnerability type to findings
        """
        vulnerabilities: Dict[str, List[Dict[str, Any]]] = {
            "high_degradation": [],
            "low_confidence": [],
            "category_specific": [],
            "variant_patterns": [],
        }

        # High degradation vulnerabilities
        for dimension, metrics in self.metrics_by_dimension.items():
            if metrics.accuracy_degradation >= threshold:
                vulnerabilities["high_degradation"].append({
                    "dimension": dimension,
                    "degradation": metrics.accuracy_degradation,
                    "base_accuracy": metrics.base_accuracy,
                    "variant_accuracy": metrics.variant_accuracy,
                    "severity": self._calculate_severity(
                        metrics.accuracy_degradation
                    ),
                })

        # Low confidence patterns
        for result in self.results:
            if result.confidence < 0.5 and not result.is_correct:
                vulnerabilities["low_confidence"].append({
                    "test_id": result.test_id,
                    "dimension": result.dimension,
                    "confidence": result.confidence,
                    "variant_type": result.variant_type,
                })

        # Category-specific vulnerabilities
        category_performance = self._analyze_by_category()
        for category, metrics_dict in category_performance.items():
            if metrics_dict["degradation"] >= threshold:
                vulnerabilities["category_specific"].append({
                    "category": category,
                    "degradation": metrics_dict["degradation"],
                    "accuracy": metrics_dict["accuracy"],
                })

        # Variant pattern analysis
        pattern_analysis = self._analyze_variant_patterns()
        vulnerabilities["variant_patterns"] = pattern_analysis

        return vulnerabilities

    def generate_improvement_recommendations(
        self,
        vulnerabilities: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """Generate improvement recommendations based on vulnerabilities.

        Args:
            vulnerabilities: Dictionary of identified vulnerabilities

        Returns:
            List of prioritized recommendations
        """
        recommendations: List[Dict[str, Any]] = []

        # High degradation recommendations
        for vuln in vulnerabilities.get("high_degradation", []):
            recommendations.append({
                "priority": "CRITICAL" if vuln["degradation"] > 0.3 else "HIGH",
                "area": vuln["dimension"],
                "issue": f"Accuracy degradation of {vuln['degradation']:.1%}",
                "recommendation": self._get_degradation_recommendation(
                    vuln["dimension"]
                ),
                "expected_impact": "High",
                "effort": "Medium",
            })

        # Low confidence recommendations
        low_conf_count = len(vulnerabilities.get("low_confidence", []))
        if low_conf_count > 0:
            recommendations.append({
                "priority": "MEDIUM",
                "area": "Model Confidence Calibration",
                "issue": f"{low_conf_count} test cases show low confidence with incorrect predictions",
                "recommendation": "Implement confidence threshold tuning and uncertainty estimation",
                "expected_impact": "Medium",
                "effort": "Medium",
            })

        # Category-specific recommendations
        for vuln in vulnerabilities.get("category_specific", []):
            recommendations.append({
                "priority": "MEDIUM",
                "area": f"{vuln['category'].title()} Category",
                "issue": f"Degradation of {vuln['degradation']:.1%} in {vuln['category']} category",
                "recommendation": f"Add domain-specific training data for {vuln['category']}",
                "expected_impact": "Medium",
                "effort": "High",
            })

        # Sort by priority
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        recommendations.sort(
            key=lambda x: priority_order.get(x["priority"], 999)
        )

        return recommendations

    def _calculate_severity(self, degradation: float) -> str:
        """Calculate severity level based on degradation.

        Args:
            degradation: Accuracy degradation percentage

        Returns:
            Severity level string
        """
        if degradation >= 0.3:
            return "CRITICAL"
        elif degradation >= 0.2:
            return "HIGH"
        elif degradation >= 0.1:
            return "MEDIUM"
        else:
            return "LOW"

    def _analyze_by_category(self) -> Dict[str, Dict[str, float]]:
        """Analyze robustness by claim category.

        Returns:
            Dictionary mapping category to metrics
        """
        category_results: Dict[str, List[RobustnessResult]] = {}

        for result in self.results:
            if result.category not in category_results:
                category_results[result.category] = []
            category_results[result.category].append(result)

        category_performance: Dict[str, Dict[str, float]] = {}
        for category, results in category_results.items():
            correct = sum(1 for r in results if r.is_correct)
            total = len(results)
            accuracy = correct / total if total > 0 else 0.0

            category_performance[category] = {
                "accuracy": accuracy,
                "test_count": total,
                "correct_count": correct,
                "degradation": 1.0 - accuracy,  # Approximate degradation
            }

        return category_performance

    def _analyze_variant_patterns(self) -> List[Dict[str, Any]]:
        """Analyze patterns in variant test failures.

        Returns:
            List of pattern analysis results
        """
        variant_patterns: Dict[str, List[RobustnessResult]] = {}

        for result in self.results:
            if result.variant_type not in variant_patterns:
                variant_patterns[result.variant_type] = []
            variant_patterns[result.variant_type].append(result)

        patterns: List[Dict[str, Any]] = []
        for variant_type, results in variant_patterns.items():
            failure_count = sum(1 for r in results if not r.is_correct)
            total = len(results)
            failure_rate = failure_count / total if total > 0 else 0.0

            patterns.append({
                "variant_type": variant_type,
                "total_tests": total,
                "failures": failure_count,
                "failure_rate": failure_rate,
                "severity": "HIGH" if failure_rate > 0.5 else "MEDIUM"
                if failure_rate > 0.3 else "LOW",
            })

        # Sort by failure rate
        patterns.sort(key=lambda x: x["failure_rate"], reverse=True)
        return patterns

    def generate_json_report(
        self,
        filename: str = "robustness_report.json",
    ) -> Dict[str, Any]:
        """Generate JSON report with all robustness metrics.

        Args:
            filename: Output filename

        Returns:
            Dictionary with report data
        """
        report = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "total_tests": len(self.results),
                "correct_tests": sum(1 for r in self.results if r.is_correct),
                "overall_accuracy": self._calculate_overall_accuracy(),
            },
            "metrics_by_dimension": {
                dim: metrics.to_dict()
                for dim, metrics in self.metrics_by_dimension.items()
            },
            "results_sample": [
                r.to_dict() for r in self.results[:10]
            ],
        }

        # Write report
        report_path = self.results_dir / filename
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info("generated_json_report", path=str(report_path))
        return report

    def generate_markdown_report(
        self,
        vulnerabilities: Dict[str, List[Dict[str, Any]]],
        recommendations: List[Dict[str, Any]],
        filename: str = "vulnerability_analysis.md",
    ) -> str:
        """Generate markdown report with vulnerability analysis.

        Args:
            vulnerabilities: Identified vulnerabilities
            recommendations: Improvement recommendations
            filename: Output filename

        Returns:
            Markdown report content
        """
        report_lines: List[str] = [
            "# Model Robustness Testing Report",
            "",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Executive Summary",
            "",
            f"- **Total Tests**: {len(self.results)}",
            f"- **Overall Accuracy**: {self._calculate_overall_accuracy():.1%}",
            f"- **Robustness Dimensions**: {len(self.metrics_by_dimension)}",
            f"- **Vulnerabilities Identified**: {sum(len(v) for v in vulnerabilities.values())}",
            "",
        ]

        # Dimension metrics
        report_lines.extend([
            "## Robustness by Dimension",
            "",
        ])

        for dimension, metrics in self.metrics_by_dimension.items():
            report_lines.extend([
                f"### {dimension.title()}",
                "",
                f"- **Base Accuracy**: {metrics.base_accuracy:.1%}",
                f"- **Variant Accuracy**: {metrics.variant_accuracy:.1%}",
                f"- **Degradation**: {metrics.accuracy_degradation:.1%}",
                f"- **Test Count**: {metrics.test_count}",
                f"- **Correct**: {metrics.correct_count}",
                f"- **Confidence Variance**: {metrics.confidence_variance:.4f}",
                "",
            ])

        # Vulnerabilities
        report_lines.extend([
            "## Identified Vulnerabilities",
            "",
        ])

        if vulnerabilities["high_degradation"]:
            report_lines.extend([
                "### High Accuracy Degradation",
                "",
            ])
            for vuln in vulnerabilities["high_degradation"]:
                report_lines.extend([
                    f"- **{vuln['dimension'].title()}**",
                    f"  - Degradation: {vuln['degradation']:.1%}",
                    f"  - Severity: {vuln['severity']}",
                    "",
                ])

        if vulnerabilities["category_specific"]:
            report_lines.extend([
                "### Category-Specific Issues",
                "",
            ])
            for vuln in vulnerabilities["category_specific"]:
                report_lines.extend([
                    f"- **{vuln['category'].title()}**",
                    f"  - Degradation: {vuln['degradation']:.1%}",
                    "",
                ])

        # Recommendations
        report_lines.extend([
            "## Improvement Recommendations",
            "",
        ])

        for idx, rec in enumerate(recommendations, 1):
            report_lines.extend([
                f"### {idx}. {rec['area']} ({rec['priority']})",
                "",
                f"**Issue**: {rec['issue']}",
                "",
                f"**Recommendation**: {rec['recommendation']}",
                "",
                f"**Expected Impact**: {rec['expected_impact']}",
                "",
                f"**Effort**: {rec['effort']}",
                "",
            ])

        report_content = "\n".join(report_lines)

        # Write report
        report_path = self.results_dir / filename
        with open(report_path, "w") as f:
            f.write(report_content)

        logger.info("generated_markdown_report", path=str(report_path))
        return report_content

    def _calculate_overall_accuracy(self) -> float:
        """Calculate overall accuracy across all tests.

        Returns:
            Overall accuracy percentage
        """
        if not self.results:
            return 0.0
        correct = sum(1 for r in self.results if r.is_correct)
        return correct / len(self.results)

    def _get_degradation_recommendation(self, dimension: str) -> str:
        """Get recommendation based on dimension.

        Args:
            dimension: Robustness dimension

        Returns:
            Recommendation text
        """
        recommendations_map = {
            "typo_robustness": "Implement character-level error correction and fuzzy matching",
            "paraphrase_robustness": "Train model on paraphrased claims and semantic augmentation",
            "adversarial_robustness": "Implement adversarial training and negation handling",
            "noise_robustness": "Add noise-robust training data and implement denoising",
            "multilingual_robustness": "Extend model to support multi-language claims and translation",
        }
        return recommendations_map.get(
            dimension,
            f"Improve model robustness for {dimension}",
        )
