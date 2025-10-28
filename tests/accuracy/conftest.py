"""Pytest configuration and fixtures for accuracy tests.

This module provides pytest fixtures and configuration for accuracy
testing of the TruthGraph verification pipeline against real-world
fact-checked claims.

Features:
- Real-world claims and evidence fixture loading
- Category and verdict filtering fixtures
- Accuracy metrics and result tracking
- Comparison logging for version tracking
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest


# ===== FIXTURE LOADING =====


@pytest.fixture(scope="session")
def accuracy_test_dir() -> Path:
    """Get the path to the accuracy tests directory.

    Returns:
        Path to tests/accuracy directory
    """
    return Path(__file__).parent


@pytest.fixture(scope="session")
def real_world_claims_file(accuracy_test_dir: Path) -> Path:
    """Get path to real-world claims JSON file.

    Args:
        accuracy_test_dir: Path to accuracy tests directory

    Returns:
        Path to real_world_claims.json
    """
    return accuracy_test_dir / "real_world_claims.json"


@pytest.fixture(scope="session")
def real_world_evidence_file(accuracy_test_dir: Path) -> Path:
    """Get path to real-world evidence JSON file.

    Args:
        accuracy_test_dir: Path to accuracy tests directory

    Returns:
        Path to real_world_evidence.json
    """
    return accuracy_test_dir / "real_world_evidence.json"


@pytest.fixture(scope="session")
def results_dir(accuracy_test_dir: Path) -> Path:
    """Get the path to the results directory.

    Creates directory if it doesn't exist.

    Args:
        accuracy_test_dir: Path to accuracy tests directory

    Returns:
        Path to results directory
    """
    results_dir = accuracy_test_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


# ===== METADATA FIXTURES =====


@pytest.fixture(scope="session")
def real_world_claims_metadata(real_world_claims_file: Path) -> Dict[str, Any]:
    """Load metadata from real-world claims fixture.

    Args:
        real_world_claims_file: Path to claims file

    Returns:
        Metadata dictionary from claims fixture
    """
    with open(real_world_claims_file, "r") as f:
        data = json.load(f)
    return data.get("metadata", {})


@pytest.fixture(scope="session")
def real_world_evidence_metadata(real_world_evidence_file: Path) -> Dict[str, Any]:
    """Load metadata from real-world evidence fixture.

    Args:
        real_world_evidence_file: Path to evidence file

    Returns:
        Metadata dictionary from evidence fixture
    """
    with open(real_world_evidence_file, "r") as f:
        data = json.load(f)
    return data.get("metadata", {})


# ===== SUMMARY FIXTURES =====


@pytest.fixture(scope="session")
def real_world_claims_summary(
    real_world_claims_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Get summary statistics about real-world claims.

    Args:
        real_world_claims_metadata: Metadata from claims fixture

    Returns:
        Dictionary containing summary statistics
    """
    return {
        "total_claims": real_world_claims_metadata.get("total_claims", 0),
        "sources": real_world_claims_metadata.get("sources", []),
        "categories": real_world_claims_metadata.get("categories", []),
        "verdict_distribution": real_world_claims_metadata.get(
            "verdict_distribution", {}
        ),
        "created_date": real_world_claims_metadata.get("created_date"),
        "version": real_world_claims_metadata.get("version"),
    }


@pytest.fixture(scope="session")
def real_world_evidence_summary(
    real_world_evidence_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Get summary statistics about real-world evidence.

    Args:
        real_world_evidence_metadata: Metadata from evidence fixture

    Returns:
        Dictionary containing summary statistics
    """
    return {
        "total_evidence": real_world_evidence_metadata.get(
            "total_evidence_items", 0
        ),
        "sources": real_world_evidence_metadata.get("sources", []),
        "nli_distribution": real_world_evidence_metadata.get(
            "nli_label_distribution", {}
        ),
        "created_date": real_world_evidence_metadata.get("created_date"),
        "version": real_world_evidence_metadata.get("version"),
    }


# ===== PYTEST CONFIGURATION =====


def pytest_configure(config: Any) -> None:
    """Configure pytest for accuracy tests.

    Args:
        config: Pytest configuration object
    """
    # Register custom markers
    config.addinivalue_line(
        "markers",
        "accuracy: marks tests as accuracy measurement tests",
    )
    config.addinivalue_line(
        "markers",
        "baseline: marks tests that measure baseline accuracy",
    )
    config.addinivalue_line(
        "markers",
        "comparison: marks tests that compare versions",
    )


def pytest_collection_modifyitems(config: Any, items: List[Any]) -> None:
    """Modify collected test items.

    Args:
        config: Pytest configuration object
        items: List of collected test items
    """
    # Mark all tests in accuracy module
    for item in items:
        if "accuracy" in str(item.fspath):
            item.add_marker(pytest.mark.accuracy)

            # Mark baseline tests
            if "baseline" in item.name:
                item.add_marker(pytest.mark.baseline)

            # Mark comparison tests
            if "comparison" in item.name:
                item.add_marker(pytest.mark.comparison)
