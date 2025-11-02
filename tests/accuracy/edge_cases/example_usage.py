"""Example usage of edge case validation framework.

This script demonstrates how to use the edge case data handlers
for comprehensive validation testing.
"""

# Set UTF-8 encoding for console output
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.accuracy.edge_cases import (
    EdgeCaseClassifier,
    EdgeCaseDataLoader,
    EdgeCaseResultsHandler,
)


def example_data_loading():
    """Demonstrate data loading capabilities."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Data Loading")
    print("=" * 80)

    loader = EdgeCaseDataLoader()

    # Load all edge cases
    all_data = loader.load_all_edge_cases()
    print(f"\nLoaded {len(all_data['claims'])} total edge cases")

    # Get statistics
    stats = loader.get_statistics()
    print("\nDataset Statistics:")
    print(f"  Total claims: {stats['total_claims']}")
    print(f"  Languages: {', '.join(stats['languages'])}")

    print("\n  Edge case distribution:")
    for category, count in sorted(stats["edge_case_counts"].items()):
        percentage = (count / stats["total_claims"]) * 100
        print(f"    {category}: {count} ({percentage:.1f}%)")

    print("\n  Verdict distribution:")
    for verdict, count in sorted(stats["verdict_counts"].items()):
        print(f"    {verdict}: {count}")

    print("\n  Complexity:")
    complexity = stats["complexity_stats"]
    print(f"    Min: {complexity['min']:.2f}")
    print(f"    Avg: {complexity['avg']:.2f}")
    print(f"    Max: {complexity['max']:.2f}")

    # Load specific categories
    print("\n" + "-" * 80)
    print("Loading specific categories:")

    long_claims = loader.load_edge_cases("long_claims")
    print(f"\n  Long claims: {len(long_claims)}")
    if long_claims:
        print(f"    Example: {long_claims[0]['text'][:100]}...")

    short_claims = loader.load_edge_cases("short_claims")
    print(f"\n  Short claims: {len(short_claims)}")
    if short_claims:
        print(f"    Examples: {[c['text'] for c in short_claims[:3]]}")

    multilingual = loader.get_multilingual_claims()
    print("\n  Multilingual claims by language:")
    for lang, claims in multilingual.items():
        print(f"    {lang}: {len(claims)} claims")
        if claims:
            print(f"      Example: {claims[0]['text']}")


def example_classification():
    """Demonstrate claim classification."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Claim Classification")
    print("=" * 80)

    classifier = EdgeCaseClassifier()

    # Test various claims
    test_claims = [
        "Water is wet.",  # Short
        "The mitochondria are the powerhouse of the cell.",  # Technical
        "Some studies suggest coffee is healthy.",  # Ambiguous
        "E = mc²",  # Special characters
        "人工智能正在改变世界",  # Multilingual (Chinese)
        " ".join(["word"] * 60),  # Long claim
    ]

    print("\nClassifying test claims:")

    for i, claim in enumerate(test_claims, 1):
        display_claim = claim if len(claim) < 80 else claim[:77] + "..."
        print(f'\n{i}. "{display_claim}"')

        categories = classifier.classify_claim(claim)
        analysis = classifier.analyze_claim(claim)

        print(f"   Categories: {', '.join(categories) if categories else 'None'}")
        print(f"   Word count: {analysis['word_count']}")
        print("   Characteristics:")
        print(f"     - Long: {analysis['is_long']}")
        print(f"     - Short: {analysis['is_short']}")
        print(f"     - Special chars: {analysis['has_special_chars']}")
        print(f"     - Multilingual: {analysis['is_multilingual']}")
        print(f"     - Ambiguous: {analysis['has_ambiguous_phrasing']}")
        print(f"     - Technical: {analysis['is_complex_technical']}")
        if analysis["detected_scripts"]:
            print(f"     - Scripts: {', '.join(analysis['detected_scripts'])}")

    # Batch statistics
    print("\n" + "-" * 80)
    print("Batch classification statistics:")

    stats = classifier.get_category_statistics(test_claims)
    print(f"\nTotal claims analyzed: {stats['_summary']['total_claims']}")
    print(f"Avg categories per claim: {stats['_summary']['avg_categories_per_claim']:.2f}")
    print(f"Avg word count: {stats['_summary']['avg_word_count']:.1f}")

    print("\nCategory distribution:")
    for category, data in sorted(stats.items()):
        if category != "_summary":
            print(f"  {category}: {data['count']} ({data['percentage']:.1f}%)")


def example_results_handling():
    """Demonstrate results handling and reporting."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Results Handling")
    print("=" * 80)

    handler = EdgeCaseResultsHandler()

    # Simulate test results
    print("\nAdding simulated test results...")

    # Successful tests
    handler.add_result(
        claim_id="edge_001",
        claim_text="Water boils at 100°C at sea level",
        edge_case_types=["special_characters"],
        expected_verdict="SUPPORTED",
        predicted_verdict="SUPPORTED",
        confidence_score=0.98,
        execution_time_ms=125.5,
    )

    handler.add_result(
        claim_id="edge_002",
        claim_text="Short claim",
        edge_case_types=["short_claims"],
        expected_verdict="SUPPORTED",
        predicted_verdict="SUPPORTED",
        confidence_score=0.95,
        execution_time_ms=50.2,
    )

    # Failed test
    handler.add_result(
        claim_id="edge_003",
        claim_text="The extremely long technical claim about quantum mechanics...",
        edge_case_types=["long_claims", "complex_technical"],
        expected_verdict="SUPPORTED",
        predicted_verdict="INSUFFICIENT",
        confidence_score=0.62,
        execution_time_ms=450.8,
    )

    # Test with error
    handler.add_result(
        claim_id="edge_004",
        claim_text="人工智能正在改变世界",
        edge_case_types=["multilingual"],
        expected_verdict="SUPPORTED",
        error="Translation failed",
    )

    # More successful tests
    handler.add_result(
        claim_id="edge_005",
        claim_text="Some studies suggest benefits",
        edge_case_types=["ambiguous_phrasing"],
        expected_verdict="INSUFFICIENT",
        predicted_verdict="INSUFFICIENT",
        confidence_score=0.78,
        execution_time_ms=200.0,
    )

    # Aggregate results
    print("\nAggregating results...")
    results = handler.aggregate_results()

    print("\nOverall Statistics:")
    print(f"  Total tests: {results['total_tests']}")
    print(f"  Passed: {results['passed_tests']}")
    print(f"  Failed: {results['failed_tests']}")
    print(f"  Errors: {results['error_tests']}")
    print(f"  Pass rate: {results['pass_rate'] * 100:.2f}%")

    print("\nResults by category:")
    for category, stats in sorted(results["results_by_category"].items()):
        print(f"  {category}: {stats['passed']}/{stats['total']} ({stats['pass_rate'] * 100:.1f}%)")

    print("\nResults by expected verdict:")
    for verdict, stats in sorted(results["results_by_verdict"].items()):
        print(f"  {verdict}: {stats['passed']}/{stats['total']} ({stats['pass_rate'] * 100:.1f}%)")

    print("\nEdge case handling metrics:")
    metrics = results["edge_case_handling_metrics"]
    print(f"  Avg confidence: {metrics['avg_confidence']:.4f}")
    print(f"  Avg execution time: {metrics['avg_execution_time_ms']:.2f} ms")
    print(f"  Error rate: {metrics['error_rate'] * 100:.2f}%")
    print(f"  Valid predictions: {metrics['total_valid_predictions']}")
    print(f"  Total errors: {metrics['total_errors']}")

    # Generate and display summary
    print("\n" + "-" * 80)
    print("Human-readable summary:")
    print("-" * 80)
    summary = handler.generate_summary(results)
    print(summary)

    # Save results
    output_path = handler.save_results(results)
    print(f"\nResults saved to: {output_path}")


def example_complete_workflow():
    """Demonstrate complete edge case testing workflow."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Complete Workflow")
    print("=" * 80)

    # 1. Load data
    print("\n1. Loading edge case data...")
    loader = EdgeCaseDataLoader()

    # Get a subset for demonstration
    insufficient_claims = loader.load_edge_cases("insufficient_evidence")
    print(f"   Loaded {len(insufficient_claims)} insufficient evidence claims")

    # 2. Initialize classifier and handler
    print("\n2. Initializing classifier and results handler...")
    classifier = EdgeCaseClassifier()
    handler = EdgeCaseResultsHandler()

    # 3. Process each claim
    print("\n3. Processing claims...")

    for claim_data in insufficient_claims[:5]:  # Process first 5 for demo
        claim_id = claim_data["id"]
        claim_text = claim_data["text"]

        print(f'\n   Processing {claim_id}: "{claim_text[:60]}..."')

        # Verify classifier detects edge cases
        detected_categories = classifier.classify_claim(claim_text)
        print(f"     Detected categories: {', '.join(detected_categories)}")

        # Simulate verification (in real use, call your verification pipeline)
        import random

        predicted_verdict = random.choice(["SUPPORTED", "REFUTED", "INSUFFICIENT"])
        confidence = random.uniform(0.5, 0.95)

        handler.add_result(
            claim_id=claim_id,
            claim_text=claim_text,
            edge_case_types=claim_data["edge_case_type"],
            expected_verdict=claim_data["expected_verdict"],
            predicted_verdict=predicted_verdict,
            confidence_score=confidence,
            execution_time_ms=random.uniform(50, 300),
        )

        passed = predicted_verdict == claim_data["expected_verdict"]
        print(f"     Result: {'✓ PASS' if passed else '✗ FAIL'}")

    # 4. Analyze results
    print("\n4. Analyzing results...")
    results = handler.aggregate_results()

    print(f"\n   Pass rate: {results['pass_rate'] * 100:.1f}%")
    print(f"   Avg confidence: {results['edge_case_handling_metrics']['avg_confidence']:.3f}")

    # 5. Save report
    print("\n5. Saving results...")
    output_path = handler.save_results()
    print(f"   Results saved to: {output_path}")

    print("\n✓ Workflow complete!")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("EDGE CASE VALIDATION FRAMEWORK - USAGE EXAMPLES")
    print("=" * 80)

    try:
        example_data_loading()
        example_classification()
        example_results_handling()
        example_complete_workflow()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
