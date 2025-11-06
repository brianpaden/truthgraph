"""Pytest configuration and fixtures for robustness tests.

This module provides fixtures and configuration for robustness
testing of the TruthGraph verification pipeline.
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest


@pytest.fixture(scope="session")
def robustness_test_dir() -> Path:
    """Get the path to the robustness tests directory.

    Returns:
        Path to tests/robustness directory
    """
    return Path(__file__).parent


@pytest.fixture(scope="session")
def robustness_data_dir(robustness_test_dir: Path) -> Path:
    """Get the path to the robustness data directory.

    Args:
        robustness_test_dir: Path to robustness tests directory

    Returns:
        Path to data directory
    """
    return robustness_test_dir / "data"


@pytest.fixture(scope="session")
def results_dir(robustness_test_dir: Path) -> Path:
    """Get the path to the results directory.

    Creates directory if it doesn't exist.

    Args:
        robustness_test_dir: Path to robustness tests directory

    Returns:
        Path to results directory
    """
    results_dir = robustness_test_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


@pytest.fixture(scope="session")
def typo_examples_file(robustness_data_dir: Path) -> Path:
    """Get path to typo examples file.

    Args:
        robustness_data_dir: Path to data directory

    Returns:
        Path to typo_examples.json
    """
    return robustness_data_dir / "typo_examples.json"


@pytest.fixture(scope="session")
def paraphrase_examples_file(robustness_data_dir: Path) -> Path:
    """Get path to paraphrase examples file.

    Args:
        robustness_data_dir: Path to data directory

    Returns:
        Path to paraphrase_examples.json
    """
    return robustness_data_dir / "paraphrase_examples.json"


@pytest.fixture(scope="session")
def adversarial_examples_file(robustness_data_dir: Path) -> Path:
    """Get path to adversarial examples file.

    Args:
        robustness_data_dir: Path to data directory

    Returns:
        Path to adversarial_examples.json
    """
    return robustness_data_dir / "adversarial_examples.json"


@pytest.fixture(scope="session")
def noise_examples_file(robustness_data_dir: Path) -> Path:
    """Get path to noise examples file.

    Args:
        robustness_data_dir: Path to data directory

    Returns:
        Path to noise_examples.json
    """
    return robustness_data_dir / "noise_examples.json"


@pytest.fixture(scope="session")
def multilingual_examples_file(robustness_data_dir: Path) -> Path:
    """Get path to multilingual examples file.

    Args:
        robustness_data_dir: Path to data directory

    Returns:
        Path to multilingual_examples.json
    """
    return robustness_data_dir / "multilingual_examples.json"


@pytest.fixture(scope="session")
def typo_examples(typo_examples_file: Path) -> Dict[str, Any]:
    """Load typo examples fixture.

    Args:
        typo_examples_file: Path to typo examples file

    Returns:
        Dictionary with typo test cases
    """
    with open(typo_examples_file, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def paraphrase_examples(paraphrase_examples_file: Path) -> Dict[str, Any]:
    """Load paraphrase examples fixture.

    Args:
        paraphrase_examples_file: Path to paraphrase examples file

    Returns:
        Dictionary with paraphrase test cases
    """
    with open(paraphrase_examples_file, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def adversarial_examples(adversarial_examples_file: Path) -> Dict[str, Any]:
    """Load adversarial examples fixture.

    Args:
        adversarial_examples_file: Path to adversarial examples file

    Returns:
        Dictionary with adversarial test cases
    """
    with open(adversarial_examples_file, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def noise_examples(noise_examples_file: Path) -> Dict[str, Any]:
    """Load noise examples fixture.

    Args:
        noise_examples_file: Path to noise examples file

    Returns:
        Dictionary with noise test cases
    """
    with open(noise_examples_file, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def multilingual_examples(multilingual_examples_file: Path) -> Dict[str, Any]:
    """Load multilingual examples fixture.

    Args:
        multilingual_examples_file: Path to multilingual examples file

    Returns:
        Dictionary with multilingual test cases
    """
    with open(multilingual_examples_file, "r") as f:
        return json.load(f)
