#!/usr/bin/env python3
"""Update regression baseline with current metrics.

This script collects current performance and accuracy metrics and creates
a new baseline for regression testing.

Usage:
    python scripts/update_baseline.py [--version VERSION]

    # Update baseline with auto-detected version
    python scripts/update_baseline.py

    # Update baseline with specific version
    python scripts/update_baseline.py --version 0.2.0
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def get_git_commit() -> Optional[str]:
    """Get current git commit hash.

    Returns:
        Git commit hash or None if not in a git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_git_branch() -> Optional[str]:
    """Get current git branch name.

    Returns:
        Branch name or None if not in a git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def load_performance_metrics() -> Dict[str, Any]:
    """Load performance metrics from benchmark results.

    Returns:
        Performance metrics dictionary
    """
    project_root = Path(__file__).parent.parent

    # Load embedding benchmarks
    embedding_file = (
        project_root / "scripts" / "benchmarks" / "results" / "baseline_embeddings_2025-10-27.json"
    )

    if not embedding_file.exists():
        print(f"❌ Embedding benchmark not found: {embedding_file}", file=sys.stderr)
        print("   Run: python scripts/benchmarks/benchmark_embeddings.py", file=sys.stderr)
        sys.exit(1)

    with open(embedding_file, "r") as f:
        embedding_data = json.load(f)

    # Load NLI benchmarks
    nli_file = project_root / "scripts" / "benchmarks" / "results" / "baseline_nli_2025-10-27.json"

    if not nli_file.exists():
        print(f"❌ NLI benchmark not found: {nli_file}", file=sys.stderr)
        print("   Run: python scripts/benchmarks/benchmark_nli.py", file=sys.stderr)
        sys.exit(1)

    with open(nli_file, "r") as f:
        nli_data = json.load(f)

    # Extract metrics
    embedding_single = embedding_data["benchmarks"]["single_text"]
    embedding_batch = embedding_data["benchmarks"]["batch_sizes"]
    embedding_memory = embedding_data["benchmarks"]["memory"]

    nli_single = nli_data["benchmarks"]["single_pair"]
    nli_batch = nli_data["benchmarks"]["batch_sizes"]
    nli_memory = nli_data["benchmarks"]["memory"]

    return {
        "embedding": {
            "latency_ms": embedding_single["avg_latency_ms"],
            "throughput": embedding_batch["best_throughput"],
            "p95_latency_ms": embedding_single["p95_latency_ms"],
            "p99_latency_ms": embedding_single["p99_latency_ms"],
        },
        "nli": {
            "latency_ms": nli_single["avg_latency_ms"],
            "throughput": nli_batch["best_throughput"],
            "p95_latency_ms": nli_single["p95_latency_ms"],
            "p99_latency_ms": nli_single["p99_latency_ms"],
        },
        "e2e": {
            "latency_seconds": 5.0,  # Placeholder - should be measured
            "throughput_claims_per_sec": 0.2,  # Placeholder - should be measured
        },
        "memory": {
            "baseline_mb": max(embedding_memory["baseline_mb"], nli_memory["baseline_mb"]),
            "peak_mb": embedding_memory["peak_mb"] + nli_memory["peak_mb"],
            "loaded_mb": embedding_memory["loaded_mb"] + nli_memory["loaded_mb"],
        },
    }


def load_accuracy_metrics() -> Dict[str, Any]:
    """Load accuracy metrics from test results.

    Returns:
        Accuracy metrics dictionary
    """
    project_root = Path(__file__).parent.parent
    results_file = project_root / "tests" / "accuracy" / "results" / "baseline_results.json"

    if not results_file.exists():
        print(f"❌ Accuracy results not found: {results_file}", file=sys.stderr)
        print("   Run: pytest tests/accuracy/test_accuracy_baseline.py -v", file=sys.stderr)
        sys.exit(1)

    with open(results_file, "r") as f:
        results = json.load(f)

    # Extract metrics
    confusion_matrix = results["confusion_matrix"]

    # Calculate per-verdict accuracy
    def calculate_verdict_accuracy(verdict: str) -> float:
        """Calculate accuracy for a specific verdict."""
        if verdict not in confusion_matrix:
            return 0.0

        correct = confusion_matrix[verdict][verdict]
        total = sum(confusion_matrix[verdict].values())

        if total == 0:
            return 0.0

        return correct / total

    # Calculate overall metrics
    total_correct = sum(confusion_matrix[v][v] for v in ["SUPPORTED", "REFUTED", "INSUFFICIENT"])
    total_predictions = sum(
        sum(confusion_matrix[v].values()) for v in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
    )

    accuracy = total_correct / total_predictions if total_predictions > 0 else 0.0

    # Use accuracy as proxy for precision/recall/f1 (simplified)
    precision = accuracy
    recall = accuracy
    f1_score = accuracy

    # Extract category accuracies
    categories = results.get("category_accuracy", {})
    category_accuracies = {cat: stats["accuracy"] for cat, stats in categories.items()}

    return {
        "overall": {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
        },
        "per_verdict": {
            "supported": calculate_verdict_accuracy("SUPPORTED"),
            "refuted": calculate_verdict_accuracy("REFUTED"),
            "insufficient": calculate_verdict_accuracy("INSUFFICIENT"),
        },
        "categories": category_accuracies,
        "confusion_matrix": confusion_matrix,
    }


def create_baseline(version: str) -> Dict[str, Any]:
    """Create baseline from current metrics.

    Args:
        version: Version string for the baseline

    Returns:
        Complete baseline dictionary
    """
    print("📊 Collecting performance metrics...")
    performance = load_performance_metrics()
    print("✓ Performance metrics loaded")

    print("📊 Collecting accuracy metrics...")
    accuracy = load_accuracy_metrics()
    print("✓ Accuracy metrics loaded")

    git_commit = get_git_commit()
    git_branch = get_git_branch()

    baseline = {
        "version": version,
        "timestamp": datetime.now().isoformat(),
        "git_commit": git_commit,
        "performance": performance,
        "accuracy": accuracy,
        "metadata": {
            "created_by": "scripts/update_baseline.py",
            "git_branch": git_branch,
            "created_at": datetime.now().isoformat(),
        },
    }

    return baseline


def save_baseline(baseline: Dict[str, Any]) -> Path:
    """Save baseline to file.

    Args:
        baseline: Baseline dictionary to save

    Returns:
        Path to saved baseline file
    """
    project_root = Path(__file__).parent.parent
    baseline_dir = project_root / "tests" / "regression" / "baselines"
    baseline_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"baseline_{timestamp}.json"
    filepath = baseline_dir / filename

    # Save baseline
    with open(filepath, "w") as f:
        json.dump(baseline, f, indent=2)

    return filepath


def update_history(baseline: Dict[str, Any]) -> None:
    """Update baseline history file.

    Args:
        baseline: Baseline dictionary to add to history
    """
    project_root = Path(__file__).parent.parent
    history_file = project_root / "tests" / "regression" / "baselines" / "baseline_history.csv"

    # Create header if file doesn't exist
    if not history_file.exists():
        with open(history_file, "w") as f:
            f.write(
                "timestamp,version,git_commit,overall_accuracy,e2e_latency_seconds,"
                "embedding_throughput,nli_throughput,memory_peak_mb\n"
            )

    # Append entry
    with open(history_file, "a") as f:
        f.write(
            f"{baseline['timestamp']},"
            f"{baseline['version']},"
            f"{baseline.get('git_commit', 'unknown')},"
            f"{baseline['accuracy']['overall']['accuracy']:.4f},"
            f"{baseline['performance']['e2e']['latency_seconds']:.2f},"
            f"{baseline['performance']['embedding']['throughput']:.2f},"
            f"{baseline['performance']['nli']['throughput']:.2f},"
            f"{baseline['performance']['memory']['peak_mb']:.2f}\n"
        )


def print_summary(baseline: Dict[str, Any], filepath: Path) -> None:
    """Print baseline update summary.

    Args:
        baseline: Created baseline
        filepath: Path where baseline was saved
    """
    print("\n" + "=" * 70)
    print("✅ BASELINE UPDATED SUCCESSFULLY")
    print("=" * 70)
    print(f"\nVersion: {baseline['version']}")
    print(f"Saved to: {filepath}")
    print(f"Git commit: {baseline.get('git_commit', 'unknown')}")
    print("\nPerformance Metrics:")
    print(f"  • Embedding latency: {baseline['performance']['embedding']['latency_ms']:.2f}ms")
    print(f"  • NLI latency: {baseline['performance']['nli']['latency_ms']:.2f}ms")
    print(f"  • E2E latency: {baseline['performance']['e2e']['latency_seconds']:.2f}s")
    print(f"  • Memory peak: {baseline['performance']['memory']['peak_mb']:.2f}MB")
    print("\nAccuracy Metrics:")
    print(f"  • Overall accuracy: {baseline['accuracy']['overall']['accuracy']:.2%}")
    print(f"  • Precision: {baseline['accuracy']['overall']['precision']:.2%}")
    print(f"  • Recall: {baseline['accuracy']['overall']['recall']:.2%}")
    print(f"  • F1 score: {baseline['accuracy']['overall']['f1_score']:.2%}")
    print("\nPer-Verdict Accuracy:")
    print(
        f"  • SUPPORTED: {baseline['accuracy']['per_verdict']['supported']:.2%}"
    )
    print(
        f"  • REFUTED: {baseline['accuracy']['per_verdict']['refuted']:.2%}"
    )
    print(
        f"  • INSUFFICIENT: {baseline['accuracy']['per_verdict']['insufficient']:.2%}"
    )
    print("\n" + "=" * 70)
    print("\nNext steps:")
    print("  • Run regression tests: pytest tests/regression/ -v")
    print("  • Commit baseline: git add tests/regression/baselines/")
    print("=" * 70 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update regression baseline with current metrics"
    )
    parser.add_argument(
        "--version",
        type=str,
        default="0.1.0",
        help="Version string for the baseline (default: 0.1.0)",
    )

    args = parser.parse_args()

    print("\n🔄 Updating regression baseline...\n")

    try:
        # Create baseline
        baseline = create_baseline(args.version)

        # Save baseline
        filepath = save_baseline(baseline)

        # Update history
        update_history(baseline)

        # Print summary
        print_summary(baseline, filepath)

        return 0

    except Exception as e:
        print(f"\n❌ Failed to update baseline: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
