#!/usr/bin/env python
"""Generate comprehensive category accuracy report.

This script generates the full category breakdown report including:
- Per-category accuracy metrics
- Category rankings
- Identified weaknesses
- HTML visualization
- JSON data export
"""

import json
from datetime import datetime
from pathlib import Path

from tests.accuracy.test_category_accuracy import CategoryAccuracyEvaluator


def main():
    """Generate comprehensive category report."""
    print("=" * 70)
    print("FEATURE 3.2: MULTI-CATEGORY EVALUATION")
    print("Category Accuracy Analysis Report Generation")
    print("=" * 70)

    # Initialize evaluator
    evaluator = CategoryAccuracyEvaluator()

    # Load and evaluate all categories
    print("\nEvaluating categories...")
    print("-" * 70)

    results = evaluator.evaluate_all_categories()

    # Generate breakdown
    print("\nGenerating category breakdown...")
    breakdown = evaluator.generate_category_breakdown(results)

    # Display results
    print("\nCategory Performance Summary:")
    print("-" * 70)

    categories = breakdown.get('categories', {})
    for category_name in sorted(categories.keys()):
        cat_data = categories[category_name]
        accuracy = cat_data.get('accuracy', 0)
        samples = cat_data.get('claims', 0)
        f1 = cat_data.get('macro_f1', 0)
        print(f"{category_name.upper():<20} | Accuracy: {accuracy:>6.1%} | F1: {f1:>7.4f} | Samples: {samples:>2}")

    # Display aggregate metrics
    print("\nAggregate Metrics:")
    print("-" * 70)
    agg = breakdown.get('aggregate', {})
    print(f"Total Samples:       {agg.get('total_samples', 0)}")
    print(f"Total Categories:    {agg.get('total_categories', 0)}")
    print(f"Weighted Accuracy:   {agg.get('weighted_accuracy', 0):.1%}")
    print(f"Average Macro F1:    {agg.get('average_macro_f1', 0):.4f}")

    # Display rankings
    print("\nCategory Rankings by Accuracy:")
    print("-" * 70)
    rankings = breakdown.get('rankings', {})
    by_accuracy = rankings.get('by_accuracy', [])
    for rank, item in enumerate(by_accuracy, 1):
        print(f"{rank}. {item['category'].upper():<20} {item['accuracy']:>6.1%}")

    # Display weaknesses
    weaknesses = breakdown.get('weaknesses', {})
    if weaknesses:
        print("\nIdentified Category Weaknesses:")
        print("-" * 70)
        for category_name in sorted(weaknesses.keys()):
            cat_weaknesses = weaknesses[category_name]
            if cat_weaknesses:
                print(f"\n{category_name.upper()}:")
                for weakness in cat_weaknesses:
                    severity = weakness.get('severity', 'medium').upper()
                    message = weakness.get('message', '')
                    print(f"  [{severity}] {message}")

    # Save JSON report
    print("\nSaving reports...")
    print("-" * 70)

    json_path = evaluator.save_category_breakdown(breakdown)
    print(f"JSON Report:  {json_path}")

    # Generate and save HTML report
    html_path = evaluator.generate_category_html_report(breakdown)
    print(f"HTML Report:  {html_path}")

    # Generate detailed statistics
    stats = generate_detailed_statistics(breakdown, results)
    stats_path = Path("tests/accuracy/results/category_statistics.json")
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"Statistics:   {stats_path}")

    # Generate recommendations
    recommendations = generate_recommendations(breakdown)
    rec_path = Path("tests/accuracy/results/category_recommendations.json")
    rec_path.parent.mkdir(parents=True, exist_ok=True)
    with open(rec_path, 'w') as f:
        json.dump(recommendations, f, indent=2)
    print(f"Recommendations: {rec_path}")

    # Generate summary report
    summary = generate_summary_report(breakdown, recommendations)
    summary_path = Path("tests/accuracy/results/CATEGORY_ANALYSIS_SUMMARY.md")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, 'w') as f:
        f.write(summary)
    print(f"Summary:      {summary_path}")

    print("\n" + "=" * 70)
    print("Category Analysis Report Generation Complete")
    print("=" * 70)


def generate_detailed_statistics(
    breakdown: dict,
    results: dict
) -> dict:
    """Generate detailed statistics for all categories.

    Args:
        breakdown: Category breakdown data
        results: Raw evaluation results

    Returns:
        Dictionary with detailed statistics
    """
    statistics = {
        "generated": datetime.now().isoformat(),
        "categories": {},
    }

    categories = breakdown.get('categories', {})
    for category_name in sorted(categories.keys()):
        cat_data = categories[category_name]
        result = results.get(category_name, {})

        # Calculate error distribution
        claims = result.get('claims', [])
        error_distribution = {
            "SUPPORTED": {"correct": 0, "errors": {}},
            "REFUTED": {"correct": 0, "errors": {}},
            "INSUFFICIENT": {"correct": 0, "errors": {}},
        }

        for claim in claims:
            expected = claim.get('expected', 'INSUFFICIENT')
            predicted = claim.get('predicted', 'INSUFFICIENT')
            is_correct = claim.get('correct', False)

            if is_correct:
                error_distribution[expected]["correct"] += 1
            else:
                if predicted not in error_distribution[expected]["errors"]:
                    error_distribution[expected]["errors"][predicted] = 0
                error_distribution[expected]["errors"][predicted] += 1

        statistics["categories"][category_name] = {
            "accuracy": cat_data.get('accuracy', 0),
            "precision": cat_data.get('precision', {}),
            "recall": cat_data.get('recall', {}),
            "f1": cat_data.get('f1', {}),
            "macro_f1": cat_data.get('macro_f1', 0),
            "samples": cat_data.get('claims', 0),
            "error_distribution": error_distribution,
            "confusion_matrix": cat_data.get('confusion_matrix', {}),
        }

    return statistics


def generate_recommendations(breakdown: dict) -> dict:
    """Generate category-specific recommendations.

    Args:
        breakdown: Category breakdown data

    Returns:
        Dictionary with recommendations
    """
    recommendations = {
        "generated": datetime.now().isoformat(),
        "priority_actions": [],
        "by_category": {},
    }

    categories = breakdown.get('categories', {})
    weaknesses = breakdown.get('weaknesses', {})

    # Generate priority actions
    all_issues = []
    for category, cat_weaknesses in weaknesses.items():
        for weakness in cat_weaknesses:
            all_issues.append({
                "category": category,
                "severity": weakness.get('severity', 'medium'),
                "type": weakness.get('type', 'unknown'),
                "message": weakness.get('message', ''),
            })

    # Sort by severity
    priority_map = {"high": 0, "medium": 1, "low": 2}
    all_issues.sort(key=lambda x: priority_map.get(x['severity'], 3))

    recommendations["priority_actions"] = all_issues[:5]  # Top 5 issues

    # Generate per-category recommendations
    for category_name in sorted(categories.keys()):
        cat_data = categories[category_name]
        accuracy = cat_data.get('accuracy', 0)
        samples = cat_data.get('claims', 0)
        precision = cat_data.get('precision', {})
        recall = cat_data.get('recall', {})

        cat_recs = {
            "overall": [],
            "data": [],
            "modeling": [],
        }

        # Overall recommendations
        if accuracy < 0.65:
            cat_recs["overall"].append("CRITICAL: Category accuracy is significantly below target. Consider architectural changes.")
        elif accuracy < 0.75:
            cat_recs["overall"].append("Category accuracy is below target. Significant improvements needed.")
        elif accuracy < 0.85:
            cat_recs["overall"].append("Category accuracy is adequate but improvement opportunities exist.")
        else:
            cat_recs["overall"].append("Category performance is good. Continue monitoring for regressions.")

        # Data recommendations
        if samples < 10:
            cat_recs["data"].append("Increase training data for this category - current sample size is limited.")
        elif samples < 20:
            cat_recs["data"].append("Collect more training examples to improve model robustness.")

        # Modeling recommendations
        low_precision_verdicts = [v for v, s in precision.items() if s < 0.70]
        if low_precision_verdicts:
            cat_recs["modeling"].append(
                f"Improve precision for {', '.join(low_precision_verdicts)} verdict(s). "
                "Focus on reducing false positives."
            )

        low_recall_verdicts = [v for v, s in recall.items() if s < 0.70]
        if low_recall_verdicts:
            cat_recs["modeling"].append(
                f"Improve recall for {', '.join(low_recall_verdicts)} verdict(s). "
                "Focus on capturing more true instances."
            )

        recommendations["by_category"][category_name] = cat_recs

    return recommendations


def generate_summary_report(breakdown: dict, recommendations: dict) -> str:
    """Generate markdown summary report.

    Args:
        breakdown: Category breakdown data
        recommendations: Recommendations data

    Returns:
        Markdown formatted report
    """
    categories = breakdown.get('categories', {})
    agg = breakdown.get('aggregate', {})

    report = f"""# Category Accuracy Analysis Report

**Feature 3.2: Multi-Category Evaluation**

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

This report presents a comprehensive analysis of the TruthGraph fact verification system's accuracy across multiple claim categories.

### Key Metrics

- **Total Samples Evaluated**: {agg.get('total_samples', 0)}
- **Categories Analyzed**: {agg.get('total_categories', 0)}
- **Overall Weighted Accuracy**: {agg.get('weighted_accuracy', 0):.1%}
- **Average Macro F1 Score**: {agg.get('average_macro_f1', 0):.4f}

## Category Performance Breakdown

| Category | Accuracy | Samples | Macro F1 | Status |
|----------|----------|---------|----------|--------|
"""

    for category_name in sorted(categories.keys()):
        cat_data = categories[category_name]
        accuracy = cat_data.get('accuracy', 0)
        samples = cat_data.get('claims', 0)
        f1 = cat_data.get('macro_f1', 0)

        if accuracy >= 0.85:
            status = "Excellent"
        elif accuracy >= 0.75:
            status = "Good"
        elif accuracy >= 0.65:
            status = "Fair"
        else:
            status = "Needs Improvement"

        report += f"| {category_name.title()} | {accuracy:.1%} | {samples} | {f1:.4f} | {status} |\n"

    report += "\n## Detailed Category Analysis\n\n"

    rankings = breakdown.get('rankings', {})
    by_accuracy = rankings.get('by_accuracy', [])

    report += "### Rankings by Accuracy\n\n"
    for rank, item in enumerate(by_accuracy, 1):
        report += f"{rank}. **{item['category'].title()}** - {item['accuracy']:.1%} ({item['samples']} samples)\n"

    report += "\n## Identified Weaknesses\n\n"

    weaknesses = breakdown.get('weaknesses', {})
    if weaknesses:
        for category_name in sorted(weaknesses.keys()):
            cat_weaknesses = weaknesses[category_name]
            if cat_weaknesses:
                report += f"### {category_name.title()}\n\n"
                for weakness in cat_weaknesses:
                    severity = weakness.get('severity', 'medium').upper()
                    message = weakness.get('message', '')
                    report += f"- **[{severity}]** {message}\n"
                report += "\n"
    else:
        report += "No critical weaknesses identified across categories.\n\n"

    report += "## Recommendations\n\n"

    priority_actions = recommendations.get('priority_actions', [])
    if priority_actions:
        report += "### Priority Actions\n\n"
        for i, action in enumerate(priority_actions, 1):
            severity = action.get('severity', 'medium').upper()
            message = action.get('message', '')
            report += f"{i}. **[{severity}]** {message}\n"
        report += "\n"

    by_category_recs = recommendations.get('by_category', {})
    if by_category_recs:
        report += "### Category-Specific Recommendations\n\n"
        for category_name in sorted(by_category_recs.keys()):
            cat_recs = by_category_recs[category_name]
            report += f"#### {category_name.title()}\n\n"

            overall = cat_recs.get('overall', [])
            if overall:
                report += "**Overall**\n"
                for rec in overall:
                    report += f"- {rec}\n"
                report += "\n"

            data = cat_recs.get('data', [])
            if data:
                report += "**Data Strategy**\n"
                for rec in data:
                    report += f"- {rec}\n"
                report += "\n"

            modeling = cat_recs.get('modeling', [])
            if modeling:
                report += "**Modeling Improvements**\n"
                for rec in modeling:
                    report += f"- {rec}\n"
                report += "\n"

    report += """## Conclusion

This multi-category evaluation reveals the strengths and weaknesses of the fact verification system across different claim types. The results can be used to:

1. **Prioritize Development**: Focus on improving low-performing categories
2. **Guide Data Collection**: Collect more training data for weak categories
3. **Inform Architecture**: Consider category-specific models or ensemble approaches
4. **Monitor Quality**: Track category performance over time to detect regressions

## Next Steps

1. Implement recommendations for low-performing categories
2. Collect additional training data for underrepresented categories
3. Consider fine-tuning models per category
4. Re-evaluate after implementation to measure improvements
5. Continue monitoring category performance as system evolves

---

*Report generated by TruthGraph Accuracy Testing Framework*
"""

    return report


if __name__ == "__main__":
    main()
