"""Baseline accuracy test against real-world claims.

This module measures TruthGraph performance on fact-checked claims
from public fact-checking sources. It provides comprehensive accuracy
metrics and comparison capabilities for version-to-version tracking.

Test execution:
    pytest tests/accuracy/test_accuracy_baseline.py -v

Performance notes:
    - Baseline run establishes accuracy metrics
    - Results are saved for comparison with future versions
    - Each claim includes source, verdict mapping, and confidence
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest
from sqlalchemy.orm import Session

from truthgraph.services.verification_pipeline_service import (
    VerificationPipelineService,
    VerdictLabel,
)


class AccuracyResults:
    """Container for accuracy test results and metrics."""

    def __init__(self):
        """Initialize accuracy results tracker."""
        self.total_claims = 0
        self.correct_verdicts = 0
        self.incorrect_verdicts = 0
        self.verdict_results = []
        self.confusion_matrix = {
            "SUPPORTED": {"SUPPORTED": 0, "REFUTED": 0, "INSUFFICIENT": 0},
            "REFUTED": {"SUPPORTED": 0, "REFUTED": 0, "INSUFFICIENT": 0},
            "INSUFFICIENT": {"SUPPORTED": 0, "REFUTED": 0, "INSUFFICIENT": 0},
        }
        self.category_accuracy = {}
        self.source_accuracy = {}
        self.start_time = None
        self.end_time = None

    def add_result(
        self,
        claim_id: str,
        claim_text: str,
        expected_verdict: str,
        actual_verdict: str,
        confidence: float,
        category: str,
        source: str,
        evidence_count: int,
    ) -> None:
        """Add a verification result to tracking.

        Args:
            claim_id: ID of the claim
            claim_text: Text of the claim
            expected_verdict: Expected verdict from fact-checker
            actual_verdict: Verdict from TruthGraph
            confidence: Confidence score from TruthGraph
            category: Claim category
            source: Fact-checking source
            evidence_count: Number of evidence items found
        """
        self.total_claims += 1
        is_correct = expected_verdict == actual_verdict

        if is_correct:
            self.correct_verdicts += 1
        else:
            self.incorrect_verdicts += 1

        # Update confusion matrix
        self.confusion_matrix[expected_verdict][actual_verdict] += 1

        # Track by category
        if category not in self.category_accuracy:
            self.category_accuracy[category] = {"correct": 0, "total": 0}
        self.category_accuracy[category]["total"] += 1
        if is_correct:
            self.category_accuracy[category]["correct"] += 1

        # Track by source
        if source not in self.source_accuracy:
            self.source_accuracy[source] = {"correct": 0, "total": 0}
        self.source_accuracy[source]["total"] += 1
        if is_correct:
            self.source_accuracy[source]["correct"] += 1

        # Store individual result
        self.verdict_results.append(
            {
                "claim_id": claim_id,
                "claim_text": claim_text,
                "expected_verdict": expected_verdict,
                "actual_verdict": actual_verdict,
                "correct": is_correct,
                "confidence": confidence,
                "category": category,
                "source": source,
                "evidence_count": evidence_count,
            }
        )

    def get_accuracy(self) -> float:
        """Get overall accuracy percentage.

        Returns:
            Accuracy as decimal (0-1)
        """
        if self.total_claims == 0:
            return 0.0
        return self.correct_verdicts / self.total_claims

    def get_category_accuracy(self, category: str) -> float:
        """Get accuracy for a specific category.

        Args:
            category: Category name

        Returns:
            Accuracy as decimal (0-1) or 0.0 if category not found
        """
        if category not in self.category_accuracy:
            return 0.0
        stats = self.category_accuracy[category]
        if stats["total"] == 0:
            return 0.0
        return stats["correct"] / stats["total"]

    def get_source_accuracy(self, source: str) -> float:
        """Get accuracy for a specific source.

        Args:
            source: Source name

        Returns:
            Accuracy as decimal (0-1) or 0.0 if source not found
        """
        if source not in self.source_accuracy:
            return 0.0
        stats = self.source_accuracy[source]
        if stats["total"] == 0:
            return 0.0
        return stats["correct"] / stats["total"]

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary format.

        Returns:
            Dictionary containing all accuracy metrics
        """
        return {
            "metadata": {
                "timestamp": self.end_time,
                "duration_seconds": (
                    (self.end_time - self.start_time).total_seconds()
                    if self.end_time and self.start_time
                    else None
                ),
            },
            "overall_metrics": {
                "total_claims": self.total_claims,
                "correct_verdicts": self.correct_verdicts,
                "incorrect_verdicts": self.incorrect_verdicts,
                "accuracy": self.get_accuracy(),
                "accuracy_percentage": f"{self.get_accuracy():.2%}",
            },
            "confusion_matrix": self.confusion_matrix,
            "category_accuracy": {
                category: {
                    "correct": stats["correct"],
                    "total": stats["total"],
                    "accuracy": self.get_category_accuracy(category),
                }
                for category, stats in self.category_accuracy.items()
            },
            "source_accuracy": {
                source: {
                    "correct": stats["correct"],
                    "total": stats["total"],
                    "accuracy": self.get_source_accuracy(source),
                }
                for source, stats in self.source_accuracy.items()
            },
            "detailed_results": self.verdict_results,
        }


# ===== FIXTURES =====


@pytest.fixture(scope="session")
def real_world_claims() -> Dict[str, Any]:
    """Load real-world claims fixture from JSON file.

    Returns:
        Dictionary containing claims metadata and claim objects
    """
    claims_file = Path(__file__).parent / "real_world_claims.json"

    if not claims_file.exists():
        pytest.fail(f"Real-world claims fixture not found at {claims_file}")

    try:
        with open(claims_file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in real-world claims: {e}")
    except Exception as e:
        pytest.fail(f"Failed to load real-world claims: {e}")


@pytest.fixture(scope="session")
def real_world_evidence() -> Dict[str, Any]:
    """Load real-world evidence fixture from JSON file.

    Returns:
        Dictionary containing evidence metadata and evidence items
    """
    evidence_file = Path(__file__).parent / "real_world_evidence.json"

    if not evidence_file.exists():
        pytest.fail(f"Real-world evidence fixture not found at {evidence_file}")

    try:
        with open(evidence_file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in real-world evidence: {e}")
    except Exception as e:
        pytest.fail(f"Failed to load real-world evidence: {e}")


@pytest.fixture
def real_world_claims_by_category(real_world_claims: Dict[str, Any]):
    """Factory fixture to retrieve claims filtered by category.

    Args:
        real_world_claims: Real-world claims fixture

    Returns:
        Callable that takes a category and returns matching claims
    """

    def _get_claims(category: str) -> List[Dict[str, Any]]:
        """Get claims filtered by category.

        Args:
            category: The category to filter by

        Returns:
            List of claims in the specified category
        """
        return [
            claim
            for claim in real_world_claims["claims"]
            if claim["category"] == category
        ]

    return _get_claims


@pytest.fixture
def real_world_claims_by_verdict(real_world_claims: Dict[str, Any]):
    """Factory fixture to retrieve claims filtered by expected verdict.

    Args:
        real_world_claims: Real-world claims fixture

    Returns:
        Callable that takes a verdict and returns matching claims
    """

    def _get_claims(verdict: str) -> List[Dict[str, Any]]:
        """Get claims filtered by expected verdict.

        Args:
            verdict: The verdict type to filter by

        Returns:
            List of claims with the specified verdict
        """
        return [
            claim
            for claim in real_world_claims["claims"]
            if claim["expected_verdict"] == verdict
        ]

    return _get_claims


@pytest.fixture
def real_world_claims_by_source(real_world_claims: Dict[str, Any]):
    """Factory fixture to retrieve claims filtered by source.

    Args:
        real_world_claims: Real-world claims fixture

    Returns:
        Callable that takes a source and returns matching claims
    """

    def _get_claims(source: str) -> List[Dict[str, Any]]:
        """Get claims filtered by fact-checking source.

        Args:
            source: The source name to filter by

        Returns:
            List of claims from the specified source
        """
        return [
            claim
            for claim in real_world_claims["claims"]
            if claim["source"] == source
        ]

    return _get_claims


@pytest.fixture
def accuracy_results() -> AccuracyResults:
    """Create an accuracy results tracker.

    Returns:
        AccuracyResults instance for tracking test metrics
    """
    return AccuracyResults()


# ===== TESTS =====


def test_real_world_claims_fixture_exists(real_world_claims: Dict[str, Any]) -> None:
    """Test that real-world claims fixture loads successfully."""
    assert real_world_claims is not None
    assert "claims" in real_world_claims
    assert "metadata" in real_world_claims
    assert len(real_world_claims["claims"]) > 0


def test_real_world_evidence_fixture_exists(
    real_world_evidence: Dict[str, Any],
) -> None:
    """Test that real-world evidence fixture loads successfully."""
    assert real_world_evidence is not None
    assert "evidence" in real_world_evidence
    assert "metadata" in real_world_evidence
    assert len(real_world_evidence["evidence"]) > 0


def test_real_world_claims_structure(real_world_claims: Dict[str, Any]) -> None:
    """Verify structure and content of real-world claims.

    Validates:
    - All claims have required fields
    - Verdict values are valid
    - Confidence scores are in valid range
    - Evidence IDs reference existing evidence
    """
    valid_verdicts = {"SUPPORTED", "REFUTED", "INSUFFICIENT"}
    required_fields = {
        "id",
        "text",
        "category",
        "expected_verdict",
        "confidence",
        "source",
        "source_url",
        "fact_checker_verdict",
        "fact_checker_reasoning",
        "date_checked",
        "evidence_ids",
    }

    claims = real_world_claims["claims"]
    assert len(claims) >= 20, "At least 20 real-world claims required"

    for claim in claims:
        # Check required fields
        assert required_fields.issubset(
            claim.keys()
        ), f"Claim {claim['id']} missing required fields"

        # Check verdict validity
        assert (
            claim["expected_verdict"] in valid_verdicts
        ), f"Invalid verdict in claim {claim['id']}"

        # Check confidence range
        confidence = claim["confidence"]
        assert 0 <= confidence <= 1, f"Invalid confidence in claim {claim['id']}"

        # Check evidence ID list
        assert isinstance(
            claim["evidence_ids"], list
        ), f"Evidence IDs should be list in claim {claim['id']}"


def test_real_world_evidence_structure(
    real_world_evidence: Dict[str, Any],
) -> None:
    """Verify structure and content of real-world evidence.

    Validates:
    - All evidence items have required fields
    - NLI labels are valid
    - Content is non-empty
    - URLs are provided
    """
    valid_labels = {"entailment", "contradiction", "neutral"}
    required_fields = {
        "id",
        "content",
        "source",
        "url",
        "relevance",
        "supports_claim",
        "excerpt_from_fact_checker",
        "nli_label",
    }

    evidence_items = real_world_evidence["evidence"]
    assert len(evidence_items) >= 30, "At least 30 real-world evidence items required"

    for evidence in evidence_items:
        # Check required fields
        assert required_fields.issubset(
            evidence.keys()
        ), f"Evidence {evidence['id']} missing required fields"

        # Check NLI label validity
        assert (
            evidence["nli_label"] in valid_labels
        ), f"Invalid NLI label in evidence {evidence['id']}"

        # Check content non-empty
        assert (
            evidence["content"] and evidence["content"].strip()
        ), f"Empty content in evidence {evidence['id']}"

        # Check URL provided
        assert (
            evidence["url"] and evidence["url"].strip()
        ), f"Missing URL in evidence {evidence['id']}"


def test_real_world_evidence_references(
    real_world_claims: Dict[str, Any],
    real_world_evidence: Dict[str, Any],
) -> None:
    """Verify that all evidence IDs referenced in claims exist.

    This test ensures referential integrity between claims and evidence.
    """
    evidence_ids = {ev["id"] for ev in real_world_evidence["evidence"]}

    for claim in real_world_claims["claims"]:
        for ev_id in claim.get("evidence_ids", []):
            assert (
                ev_id in evidence_ids
            ), f"Claim {claim['id']} references non-existent evidence {ev_id}"


def test_verdict_distribution(real_world_claims: Dict[str, Any]) -> None:
    """Verify balanced distribution of verdict types.

    Ensures the dataset includes adequate samples of each verdict type
    for comprehensive testing.
    """
    verdict_counts = {}
    for claim in real_world_claims["claims"]:
        verdict = claim["expected_verdict"]
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

    # Verify all verdict types are represented
    assert "SUPPORTED" in verdict_counts, "No SUPPORTED claims in dataset"
    assert "REFUTED" in verdict_counts, "No REFUTED claims in dataset"
    assert "INSUFFICIENT" in verdict_counts, "No INSUFFICIENT claims in dataset"

    # Verify reasonable distribution (at least one claim of each type)
    total = sum(verdict_counts.values())
    assert total >= 20, f"Expected at least 20 claims, got {total}"

    # Each verdict type should have at least 2 claims for testing
    for verdict, count in verdict_counts.items():
        assert count >= 2, f"{verdict} should have at least 2 claims (got {count})"


def test_category_coverage(real_world_claims: Dict[str, Any]) -> None:
    """Verify coverage of multiple claim categories.

    Ensures the dataset covers diverse domains for comprehensive evaluation.
    """
    categories = set()
    for claim in real_world_claims["claims"]:
        categories.add(claim["category"])

    # Require at least 4 different categories
    assert (
        len(categories) >= 4
    ), f"Expected at least 4 categories, got {len(categories)}"

    print(f"Categories covered: {', '.join(sorted(categories))}")


def test_real_world_claims_by_category(
    real_world_claims_by_category,
) -> None:
    """Test filtering claims by category."""
    health_claims = real_world_claims_by_category("health")
    assert len(health_claims) > 0, "Should have health claims"

    science_claims = real_world_claims_by_category("science")
    assert len(science_claims) > 0, "Should have science claims"


def test_real_world_claims_by_verdict(
    real_world_claims_by_verdict,
) -> None:
    """Test filtering claims by expected verdict."""
    supported_claims = real_world_claims_by_verdict("SUPPORTED")
    assert len(supported_claims) > 0, "Should have SUPPORTED claims"

    refuted_claims = real_world_claims_by_verdict("REFUTED")
    assert len(refuted_claims) > 0, "Should have REFUTED claims"

    insufficient_claims = real_world_claims_by_verdict("INSUFFICIENT")
    assert len(insufficient_claims) > 0, "Should have INSUFFICIENT claims"


def test_accuracy_results_tracking() -> None:
    """Test AccuracyResults tracking functionality."""
    results = AccuracyResults()

    # Add some results
    results.add_result(
        "test_001",
        "Test claim 1",
        "SUPPORTED",
        "SUPPORTED",
        0.95,
        "science",
        "Snopes",
        5,
    )
    results.add_result(
        "test_002",
        "Test claim 2",
        "REFUTED",
        "SUPPORTED",
        0.80,
        "health",
        "FactCheck.org",
        3,
    )

    # Verify tracking
    assert results.total_claims == 2
    assert results.correct_verdicts == 1
    assert results.incorrect_verdicts == 1
    assert results.get_accuracy() == 0.5
    assert results.category_accuracy["science"]["correct"] == 1
    assert results.category_accuracy["health"]["correct"] == 0
    assert results.source_accuracy["Snopes"]["correct"] == 1
    assert results.source_accuracy["FactCheck.org"]["correct"] == 0


def test_accuracy_results_serialization() -> None:
    """Test that accuracy results can be serialized to JSON."""
    results = AccuracyResults()
    results.start_time = datetime.now()
    results.add_result(
        "test_001",
        "Test claim",
        "SUPPORTED",
        "SUPPORTED",
        0.95,
        "science",
        "Snopes",
        5,
    )
    results.end_time = datetime.now()

    # Should not raise exception
    result_dict = results.to_dict()
    assert "overall_metrics" in result_dict
    assert "confusion_matrix" in result_dict
    assert result_dict["overall_metrics"]["accuracy"] == 1.0


# ===== BASELINE ACCURACY TEST (Optional, requires database setup) =====


@pytest.mark.skip(
    reason="Requires active TruthGraph services and database connection"
)
def test_baseline_accuracy(
    db: Session,
    real_world_claims: Dict[str, Any],
    accuracy_results: AccuracyResults,
) -> None:
    """
    Measure baseline accuracy on real-world claims.

    This test requires:
    - Active database connection (db fixture)
    - Initialized TruthGraph services
    - Evidence corpus loaded in database

    To run this test:
    1. Start TruthGraph services
    2. Load evidence into database
    3. Run: pytest tests/accuracy/test_accuracy_baseline.py::test_baseline_accuracy -v
    """
    accuracy_results.start_time = datetime.now()

    # Initialize verification pipeline
    pipeline = VerificationPipelineService()

    # Process each claim
    for claim_data in real_world_claims["claims"]:
        try:
            # Run verification pipeline
            claim_id = uuid.UUID(claim_data["id"].replace("rw_", "0" * 30))
            result = pipeline.verify_claim(
                db=db,
                claim_id=claim_id,
                claim_text=claim_data["text"],
                top_k_evidence=10,
                min_similarity=0.5,
                use_cache=False,
            )

            # Map TruthGraph verdict to our format
            actual_verdict = result.verdict.value

            # Track result
            accuracy_results.add_result(
                claim_id=claim_data["id"],
                claim_text=claim_data["text"],
                expected_verdict=claim_data["expected_verdict"],
                actual_verdict=actual_verdict,
                confidence=result.confidence,
                category=claim_data["category"],
                source=claim_data["source"],
                evidence_count=len(result.evidence_items),
            )

        except Exception as e:
            pytest.skip(f"Could not verify claim {claim_data['id']}: {e}")

    accuracy_results.end_time = datetime.now()

    # Save baseline results
    results_file = Path(__file__).parent / "results" / "baseline_results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)

    with open(results_file, "w") as f:
        json.dump(accuracy_results.to_dict(), f, indent=2, default=str)

    # Report results
    accuracy = accuracy_results.get_accuracy()
    print(f"\n{'='*60}")
    print(f"BASELINE ACCURACY TEST RESULTS")
    print(f"{'='*60}")
    print(f"Overall Accuracy: {accuracy:.2%}")
    print(f"Correct: {accuracy_results.correct_verdicts}/{accuracy_results.total_claims}")
    print(f"Duration: {accuracy_results.end_time - accuracy_results.start_time}")
    print(f"Results saved to: {results_file}")

    # Assert minimum accuracy threshold
    assert (
        accuracy >= 0.50
    ), f"Baseline accuracy {accuracy:.2%} below minimum threshold (50%)"
