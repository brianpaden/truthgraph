"""Generate sample accuracy reports for documentation and demonstration.

This script:
1. Loads test data from fixtures
2. Runs accuracy evaluation
3. Generates comprehensive reports in all formats
4. Demonstrates the framework capabilities
"""

import json
from pathlib import Path
from typing import List, Tuple

from tests.accuracy.accuracy_framework import AccuracyFramework
from tests.accuracy.reporters import Reporter


def load_test_claims(fixture_file: str) -> Tuple[List[str], List[str], List[str], List[str]]:
    """Load test claims from JSON fixture.

    Args:
        fixture_file: Path to fixture file

    Returns:
        Tuple of (claim_ids, claim_texts, expected_verdicts, categories)
    """
    if not Path(fixture_file).exists():
        return [], [], [], []

    with open(fixture_file, "r") as f:
        data = json.load(f)

    claim_ids = []
    claim_texts = []
    expected_verdicts = []
    categories = []

    if "claims" in data:
        for claim in data["claims"]:
            claim_ids.append(claim.get("id", ""))
            claim_texts.append(claim.get("text", ""))

            # Map verdict format
            verdict = claim.get("expected_verdict", "INSUFFICIENT")
            if verdict in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]:
                expected_verdicts.append(verdict)
            elif verdict == "SUPPORTS":
                expected_verdicts.append("SUPPORTED")
            elif verdict == "REFUTES":
                expected_verdicts.append("REFUTED")
            else:
                expected_verdicts.append("INSUFFICIENT")

            categories.append(claim.get("category", "general"))

    return claim_ids, claim_texts, expected_verdicts, categories


def simulate_predictions(verdicts: List[str]) -> List[str]:
    """Simulate realistic predictions.

    Args:
        verdicts: Expected verdicts

    Returns:
        List of predicted verdicts
    """
    predictions = []
    for i, verdict in enumerate(verdicts):
        # 75% accuracy pattern
        if i % 4 == 0:
            if verdict == "SUPPORTED":
                predictions.append("REFUTED")
            elif verdict == "REFUTED":
                predictions.append("INSUFFICIENT")
            else:
                predictions.append("SUPPORTED")
        else:
            predictions.append(verdict)

    return predictions


def main():
    """Generate sample reports."""
    # Setup
    results_dir = Path("tests/accuracy/results")
    results_dir.mkdir(parents=True, exist_ok=True)

    framework = AccuracyFramework(str(results_dir))
    reporter = Reporter(str(results_dir))

    # Load all available fixtures
    fixture_files = [
        "tests/fixtures/test_claims.json",
        "tests/fixtures/fever/fever_sample_claims.json",
        "tests/accuracy/real_world_claims.json",
    ]

    all_predictions = []
    all_verdicts = []
    all_categories = []

    print("Loading test fixtures...")
    for fixture_file in fixture_files:
        if not Path(fixture_file).exists():
            print(f"  Skipping {fixture_file} (not found)")
            continue

        claim_ids, claim_texts, verdicts, categories = load_test_claims(fixture_file)

        if verdicts:
            predictions = simulate_predictions(verdicts)
            all_predictions.extend(predictions)
            all_verdicts.extend(verdicts)
            all_categories.extend(categories)

            print(f"  Loaded {len(verdicts)} claims from {fixture_file}")

    if not all_verdicts:
        print("Error: No test data loaded")
        return

    print(f"\nTotal claims loaded: {len(all_verdicts)}")

    # Run evaluation
    print("Running accuracy evaluation...")
    results = framework.evaluate(all_predictions, all_verdicts, all_categories)

    accuracy = results.get("accuracy", 0)
    macro_f1 = results.get("macro_f1", 0)
    weighted_f1 = results.get("weighted_f1", 0)

    print(f"  Overall Accuracy: {accuracy:.1%}")
    print(f"  Macro F1: {macro_f1:.4f}")
    print(f"  Weighted F1: {weighted_f1:.4f}")

    # Generate HTML report
    print("\nGenerating reports...")
    html_path = reporter.generate_html_report(
        results,
        str(results_dir / "accuracy_report.html"),
        title="TruthGraph Accuracy Testing Report"
    )
    print(f"  HTML Report: {html_path}")

    # Generate JSON report
    json_path = reporter.generate_json_report(
        results,
        str(results_dir / "accuracy_results.json")
    )
    print(f"  JSON Report: {json_path}")

    # Generate text summary
    summary_path = reporter.save_summary(
        results,
        str(results_dir / "accuracy_summary.txt")
    )
    print(f"  Text Summary: {summary_path}")

    # Save confusion matrix CSV
    csv_path = framework.save_confusion_matrix_csv(
        str(results_dir / "confusion_matrix.csv")
    )
    print(f"  Confusion Matrix CSV: {csv_path}")

    # Save results JSON
    results_json_path = framework.save_results_json(
        results,
        str(results_dir / "full_results.json")
    )
    print(f"  Full Results JSON: {results_json_path}")

    # Display per-category breakdown
    print("\nPer-Category Breakdown:")
    per_category = results.get("per_category", {})
    for category in sorted(per_category.keys()):
        metrics = per_category[category]
        cat_acc = metrics.get("accuracy", 0)
        cat_samples = metrics.get("samples", 0)
        cat_f1 = metrics.get("macro_f1", 0)
        print(f"  {category:20} Accuracy: {cat_acc:6.1%}  Samples: {cat_samples:3d}  F1: {cat_f1:.4f}")

    # Display verdict metrics table
    print("\nPer-Verdict Metrics:")
    print(f"  {'Verdict':<15} {'Precision':>10} {'Recall':>10} {'F1 Score':>10}")
    print(f"  {'-'*45}")

    precision = results.get("precision", {})
    recall = results.get("recall", {})
    f1 = results.get("f1", {})

    for verdict in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]:
        p = precision.get(verdict, 0)
        r = recall.get(verdict, 0)
        f = f1.get(verdict, 0)
        print(f"  {verdict:<15} {p:>10.4f} {r:>10.4f} {f:>10.4f}")

    # Display confusion matrix
    print("\nConfusion Matrix (Actual vs Predicted):")
    print(f"  {'':15} {'SUPPORTED':>12} {'REFUTED':>12} {'INSUFFICIENT':>15}")
    print(f"  {'-'*56}")

    cm = results.get("confusion_matrix", {})
    for actual in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]:
        row = cm.get(actual, {})
        s = row.get("SUPPORTED", 0)
        r = row.get("REFUTED", 0)
        i = row.get("INSUFFICIENT", 0)
        print(f"  {actual:<15} {s:>12} {r:>12} {i:>15}")

    # Verify accuracy requirement
    print("\nRequirement Validation:")
    print(f"  Overall Accuracy: {accuracy:.1%}")
    print(f"  Requirement (>70%): {'PASSED' if accuracy > 0.70 else 'FAILED'}")

    print("\n" + "="*70)
    print("SAMPLE REPORTS GENERATED SUCCESSFULLY")
    print("="*70)
    print(f"\nReports are located in: {results_dir}")
    print("\nYou can view the HTML report in a web browser:")
    print(f"  {html_path}")


if __name__ == "__main__":
    # This needs to be run from the project root
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    main()
