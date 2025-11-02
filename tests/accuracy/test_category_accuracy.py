"""Category-specific accuracy evaluation tests.

This module implements Feature 3.2: Multi-Category Evaluation
Evaluates system accuracy across multiple claim categories and identifies
category-specific weaknesses.

Categories evaluated:
- Politics
- Science
- Health
- Current Events
- Historical Facts
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from tests.accuracy.accuracy_framework import AccuracyFramework
from tests.accuracy.reporters import Reporter


class CategoryAccuracyEvaluator:
    """Evaluator for category-specific accuracy analysis."""

    CATEGORIES = [
        "politics",
        "science",
        "health",
        "current_events",
        "historical",
    ]

    def __init__(self, data_dir: str = "tests/accuracy/categories"):
        """Initialize category accuracy evaluator.

        Args:
            data_dir: Directory containing category JSON files
        """
        self.data_dir = Path(data_dir)
        self.framework = AccuracyFramework()
        self.reporter = Reporter()
        self.category_results = {}
        self.claims_by_category = {}

    def load_category_claims(self, category: str) -> List[Dict[str, Any]]:
        """Load claims for a specific category.

        Args:
            category: Category name (politics, science, health, etc.)

        Returns:
            List of claim dictionaries with expected verdicts
        """
        category_file = self.data_dir / f"{category}.json"

        if not category_file.exists():
            raise FileNotFoundError(f"Category file not found: {category_file}")

        with open(category_file, "r") as f:
            data = json.load(f)

        return data.get("claims", [])

    def load_all_categories(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load claims for all categories.

        Returns:
            Dictionary mapping category names to claim lists
        """
        all_claims = {}

        for category in self.CATEGORIES:
            try:
                claims = self.load_category_claims(category)
                all_claims[category] = claims
                self.claims_by_category[category] = claims
            except FileNotFoundError:
                print(f"Warning: Category file not found for {category}")

        return all_claims

    def evaluate_category(
        self,
        category: str,
        predictions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Evaluate accuracy for a specific category.

        Args:
            category: Category name to evaluate
            predictions: Optional list of predictions. If None, uses expected verdicts.

        Returns:
            Dictionary with category evaluation results
        """
        claims = self.load_category_claims(category)

        if not claims:
            raise ValueError(f"No claims found for category: {category}")

        # Extract expected verdicts
        expected_verdicts = [claim.get("expected_verdict", "INSUFFICIENT") for claim in claims]

        # Use provided predictions or expected verdicts (for baseline)
        if predictions is None:
            # For testing, use expected verdicts as predictions (perfect scenario)
            predictions = expected_verdicts
        elif len(predictions) != len(expected_verdicts):
            raise ValueError(
                f"Predictions length ({len(predictions)}) does not match "
                f"claims length ({len(expected_verdicts)})"
            )

        # Evaluate using framework
        result = self.framework.evaluate(
            predictions=predictions,
            expected_verdicts=expected_verdicts,
            categories=[category] * len(predictions),
        )

        # Add category-specific metadata
        result["category"] = category
        result["claim_count"] = len(claims)
        result["claims"] = [
            {
                "id": claim.get("id"),
                "text": claim.get("text"),
                "expected": claim.get("expected_verdict"),
                "predicted": pred,
                "correct": claim.get("expected_verdict") == pred,
            }
            for claim, pred in zip(claims, predictions)
        ]

        self.category_results[category] = result
        return result

    def evaluate_all_categories(
        self,
        predictions_by_category: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Evaluate accuracy for all categories.

        Args:
            predictions_by_category: Optional dict mapping category to predictions.
                                    If None, uses expected verdicts.

        Returns:
            Dictionary mapping category names to evaluation results
        """
        self.load_all_categories()
        all_results = {}

        for category in self.CATEGORIES:
            if category not in self.claims_by_category:
                continue

            # Get predictions for this category
            category_predictions = None
            if predictions_by_category and category in predictions_by_category:
                category_predictions = predictions_by_category[category]

            try:
                result = self.evaluate_category(category, category_predictions)
                all_results[category] = result
            except Exception as e:
                print(f"Error evaluating category {category}: {e}")

        return all_results

    def generate_category_breakdown(
        self,
        results: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate category performance breakdown.

        Args:
            results: Category evaluation results (uses stored if None)

        Returns:
            Dictionary with category performance metrics
        """
        if results is None:
            results = self.category_results

        if not results:
            return {}

        breakdown = {
            "timestamp": datetime.now().isoformat(),
            "categories": {},
            "aggregate": self._calculate_aggregate_metrics(results),
            "rankings": self._rank_categories(results),
            "weaknesses": self._identify_weaknesses(results),
        }

        for category, result in results.items():
            breakdown["categories"][category] = {
                "claims": result.get("claim_count", 0),
                "accuracy": result.get("accuracy", 0),
                "precision": result.get("precision", {}),
                "recall": result.get("recall", {}),
                "f1": result.get("f1", {}),
                "macro_f1": result.get("macro_f1", 0),
                "weighted_f1": result.get("weighted_f1", 0),
                "confusion_matrix": result.get("confusion_matrix", {}),
            }

        return breakdown

    def _calculate_aggregate_metrics(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Calculate aggregate metrics across all categories.

        Args:
            results: Category evaluation results

        Returns:
            Dictionary with aggregate metrics
        """
        if not results:
            return {}

        total_samples = sum(result.get("claim_count", 0) for result in results.values())

        if total_samples == 0:
            return {}

        # Weighted average accuracy
        weighted_accuracy = (
            sum(
                result.get("accuracy", 0) * result.get("claim_count", 0)
                for result in results.values()
            )
            / total_samples
        )

        # Average macro F1
        avg_macro_f1 = sum(result.get("macro_f1", 0) for result in results.values()) / len(results)

        return {
            "total_samples": total_samples,
            "total_categories": len(results),
            "weighted_accuracy": weighted_accuracy,
            "average_macro_f1": avg_macro_f1,
        }

    def _rank_categories(
        self, results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Rank categories by accuracy metrics.

        Args:
            results: Category evaluation results

        Returns:
            Dictionary with ranked categories by different metrics
        """
        category_metrics = [
            {
                "category": category,
                "accuracy": result.get("accuracy", 0),
                "macro_f1": result.get("macro_f1", 0),
                "samples": result.get("claim_count", 0),
            }
            for category, result in results.items()
        ]

        return {
            "by_accuracy": sorted(category_metrics, key=lambda x: x["accuracy"], reverse=True),
            "by_f1": sorted(category_metrics, key=lambda x: x["macro_f1"], reverse=True),
        }

    def _identify_weaknesses(
        self, results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Identify category-specific weaknesses.

        Args:
            results: Category evaluation results

        Returns:
            Dictionary with identified weaknesses per category
        """
        weaknesses = {}

        for category, result in results.items():
            cat_weaknesses = []

            # Low accuracy in category
            accuracy = result.get("accuracy", 0)
            if accuracy < 0.70:
                cat_weaknesses.append(
                    {
                        "type": "low_accuracy",
                        "severity": "high" if accuracy < 0.50 else "medium",
                        "value": accuracy,
                        "message": f"Category accuracy ({accuracy:.1%}) is below target",
                    }
                )

            # Low precision for specific verdict
            precision = result.get("precision", {})
            for verdict, score in precision.items():
                if score < 0.60:
                    cat_weaknesses.append(
                        {
                            "type": "low_precision",
                            "verdict": verdict,
                            "severity": "high" if score < 0.40 else "medium",
                            "value": score,
                            "message": f"Low precision for {verdict}: {score:.1%}",
                        }
                    )

            # Low recall for specific verdict
            recall = result.get("recall", {})
            for verdict, score in recall.items():
                if score < 0.60:
                    cat_weaknesses.append(
                        {
                            "type": "low_recall",
                            "verdict": verdict,
                            "severity": "high" if score < 0.40 else "medium",
                            "value": score,
                            "message": f"Low recall for {verdict}: {score:.1%}",
                        }
                    )

            if cat_weaknesses:
                weaknesses[category] = cat_weaknesses

        return weaknesses

    def save_category_breakdown(
        self,
        breakdown: Dict[str, Any],
        output_file: Optional[str] = None,
    ) -> str:
        """Save category breakdown to JSON file.

        Args:
            breakdown: Category breakdown dictionary
            output_file: Output file path

        Returns:
            Path to saved file
        """
        if output_file is None:
            output_file = "tests/accuracy/results/category_breakdown.json"

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(breakdown, f, indent=2)

        return str(output_path)

    def generate_category_html_report(
        self,
        breakdown: Dict[str, Any],
        output_file: Optional[str] = None,
    ) -> str:
        """Generate HTML report for category breakdown.

        Args:
            breakdown: Category breakdown dictionary
            output_file: Output file path

        Returns:
            Path to generated report
        """
        if output_file is None:
            output_file = "tests/accuracy/results/category_report.html"

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Extract data
        categories = breakdown.get("categories", {})
        aggregate = breakdown.get("aggregate", {})
        rankings = breakdown.get("rankings", {})
        weaknesses = breakdown.get("weaknesses", {})
        timestamp = breakdown.get("timestamp", datetime.now().isoformat())

        # Generate category cards
        category_cards = self._generate_category_cards(categories, weaknesses)

        # Generate rankings
        ranking_tables = self._generate_ranking_tables(rankings)

        # Generate weaknesses section
        weaknesses_section = self._generate_weaknesses_section(weaknesses)

        # Generate HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Category Accuracy Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header h1 {{
            font-size: 2.8em;
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 1.1em;
            opacity: 0.95;
        }}
        .aggregate-metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            text-align: center;
            border-left: 4px solid #667eea;
        }}
        .metric-label {{
            color: #667eea;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        .metric-value {{
            font-size: 2.2em;
            font-weight: bold;
            color: #333;
        }}
        .metric-unit {{
            font-size: 0.5em;
            color: #999;
            margin-left: 5px;
        }}
        .section {{
            background: white;
            padding: 30px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        .section h2 {{
            color: #667eea;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid #667eea;
            font-size: 1.8em;
        }}
        .categories-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .category-card {{
            background: #fafafa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }}
        .category-card h3 {{
            color: #333;
            margin-bottom: 15px;
            font-size: 1.3em;
            text-transform: capitalize;
        }}
        .category-stat {{
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .category-stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .category-stat-value {{
            font-weight: 700;
            color: #333;
            font-size: 1.1em;
        }}
        .progress-bar {{
            width: 100%;
            height: 8px;
            background-color: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 5px;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
        }}
        .status {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
        }}
        .status.excellent {{
            background-color: #d4edda;
            color: #155724;
        }}
        .status.good {{
            background-color: #cfe2ff;
            color: #084298;
        }}
        .status.fair {{
            background-color: #fff3cd;
            color: #664d03;
        }}
        .status.poor {{
            background-color: #f8d7da;
            color: #842029;
        }}
        .weakness {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 4px;
        }}
        .weakness.high {{
            background-color: #f8d7da;
            border-left-color: #dc3545;
        }}
        .weakness-type {{
            font-weight: 600;
            color: #333;
            text-transform: uppercase;
            font-size: 0.9em;
        }}
        .weakness-message {{
            color: #666;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th {{
            background-color: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        tr:hover {{
            background-color: #f9f9f9;
        }}
        .number {{
            text-align: right;
            font-variant-numeric: tabular-nums;
        }}
        .footer {{
            text-align: center;
            color: #999;
            padding: 20px;
            font-size: 0.9em;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Category Accuracy Analysis Report</h1>
            <p>Feature 3.2: Multi-Category Evaluation</p>
            <p>Generated: {timestamp}</p>
        </div>

        <div class="aggregate-metrics">
            <div class="metric-card">
                <div class="metric-label">Total Samples</div>
                <div class="metric-value">
                    {aggregate.get("total_samples", 0)}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Categories</div>
                <div class="metric-value">
                    {aggregate.get("total_categories", 0)}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Weighted Accuracy</div>
                <div class="metric-value">
                    {aggregate.get("weighted_accuracy", 0):.1%}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Macro F1</div>
                <div class="metric-value">
                    {aggregate.get("average_macro_f1", 0):.3f}
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Category Performance Overview</h2>
            <div class="categories-grid">
                {category_cards}
            </div>
        </div>

        {ranking_tables}

        {weaknesses_section}

        <div class="section">
            <h2>Recommendations</h2>
            <p>Based on the category-specific analysis, here are recommendations for improvement:</p>
            <ol style="margin-left: 20px; margin-top: 15px;">
                <li><strong>Focus on Low-Performing Categories:</strong> Prioritize improving categories with accuracy below 75%. Consider collecting more training data or refining models for these categories.</li>
                <li><strong>Address Verdict-Specific Issues:</strong> For categories with low precision or recall on specific verdicts, investigate failure patterns and implement targeted improvements.</li>
                <li><strong>Improve Imbalanced Categories:</strong> Categories with fewer samples may have reliability issues. Consider collecting additional training data or using techniques to handle class imbalance.</li>
                <li><strong>Regular Monitoring:</strong> Continue evaluating category performance regularly to detect regressions early and track improvements over time.</li>
                <li><strong>Category-Specific Models:</strong> Consider training separate models optimized for each category instead of a single universal model.</li>
            </ol>
        </div>

        <div class="footer">
            <p>TruthGraph Accuracy Testing Framework - Multi-Category Evaluation (Feature 3.2)</p>
        </div>
    </div>
</body>
</html>
"""

        with open(output_path, "w") as f:
            f.write(html_content)

        return str(output_path)

    def _generate_category_cards(
        self,
        categories: Dict[str, Dict[str, Any]],
        weaknesses: Dict[str, List[Dict[str, Any]]],
    ) -> str:
        """Generate HTML cards for each category.

        Args:
            categories: Category metrics
            weaknesses: Category weaknesses

        Returns:
            HTML string for category cards
        """
        html = ""

        for category_name in sorted(categories.keys()):
            cat_data = categories[category_name]
            accuracy = cat_data.get("accuracy", 0)
            samples = cat_data.get("claims", 0)
            macro_f1 = cat_data.get("macro_f1", 0)

            # Determine status
            if accuracy >= 0.85:
                status = "excellent"
                status_text = "Excellent"
            elif accuracy >= 0.75:
                status = "good"
                status_text = "Good"
            elif accuracy >= 0.65:
                status = "fair"
                status_text = "Fair"
            else:
                status = "poor"
                status_text = "Poor"

            # Check weaknesses
            cat_weaknesses = weaknesses.get(category_name, [])
            weakness_count = len(cat_weaknesses)
            weakness_indicator = (
                f" ({weakness_count} weakness{'es' if weakness_count != 1 else ''})"
                if weakness_count
                else ""
            )

            html += f"""
            <div class="category-card">
                <h3>{category_name.title()}</h3>
                <div class="category-stat">
                    <span class="category-stat-label">Accuracy</span>
                    <span class="category-stat-value">{accuracy:.1%}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {accuracy * 100}%"></div>
                </div>
                <div class="category-stat" style="margin-top: 15px;">
                    <span class="category-stat-label">Status</span>
                    <span class="status {status}">{status_text}</span>
                </div>
                <div class="category-stat">
                    <span class="category-stat-label">Samples</span>
                    <span class="category-stat-value">{samples}</span>
                </div>
                <div class="category-stat">
                    <span class="category-stat-label">Macro F1</span>
                    <span class="category-stat-value">{macro_f1:.3f}</span>
                </div>
                <div class="category-stat">
                    <span class="category-stat-label">Issues</span>
                    <span class="category-stat-value">{weakness_indicator or "None"}</span>
                </div>
            </div>
            """

        return html

    def _generate_ranking_tables(self, rankings: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate HTML tables for category rankings.

        Args:
            rankings: Category rankings

        Returns:
            HTML string for ranking tables
        """
        html = '<div class="section">\n'
        html += "  <h2>Category Rankings</h2>\n"

        # Accuracy ranking
        by_accuracy = rankings.get("by_accuracy", [])
        if by_accuracy:
            html += '  <h3 style="color: #667eea; margin-top: 20px; margin-bottom: 15px;">By Accuracy</h3>\n'
            html += "  <table>\n"
            html += "    <thead>\n"
            html += "      <tr>\n"
            html += "        <th>Rank</th>\n"
            html += "        <th>Category</th>\n"
            html += '        <th class="number">Accuracy</th>\n'
            html += '        <th class="number">Samples</th>\n'
            html += "      </tr>\n"
            html += "    </thead>\n"
            html += "    <tbody>\n"

            for rank, item in enumerate(by_accuracy, 1):
                html += "      <tr>\n"
                html += f"        <td>{rank}</td>\n"
                html += f"        <td>{item['category'].title()}</td>\n"
                html += f'        <td class="number">{item["accuracy"]:.1%}</td>\n'
                html += f'        <td class="number">{item["samples"]}</td>\n'
                html += "      </tr>\n"

            html += "    </tbody>\n"
            html += "  </table>\n"

        # F1 ranking
        by_f1 = rankings.get("by_f1", [])
        if by_f1:
            html += '  <h3 style="color: #667eea; margin-top: 20px; margin-bottom: 15px;">By F1 Score</h3>\n'
            html += "  <table>\n"
            html += "    <thead>\n"
            html += "      <tr>\n"
            html += "        <th>Rank</th>\n"
            html += "        <th>Category</th>\n"
            html += '        <th class="number">F1 Score</th>\n'
            html += '        <th class="number">Samples</th>\n'
            html += "      </tr>\n"
            html += "    </thead>\n"
            html += "    <tbody>\n"

            for rank, item in enumerate(by_f1, 1):
                html += "      <tr>\n"
                html += f"        <td>{rank}</td>\n"
                html += f"        <td>{item['category'].title()}</td>\n"
                html += f'        <td class="number">{item["macro_f1"]:.4f}</td>\n'
                html += f'        <td class="number">{item["samples"]}</td>\n'
                html += "      </tr>\n"

            html += "    </tbody>\n"
            html += "  </table>\n"

        html += "</div>\n"
        return html

    def _generate_weaknesses_section(self, weaknesses: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate HTML section for identified weaknesses.

        Args:
            weaknesses: Category weaknesses

        Returns:
            HTML string for weaknesses section
        """
        if not weaknesses:
            return ""

        html = '<div class="section">\n'
        html += "  <h2>Identified Weaknesses</h2>\n"

        for category_name in sorted(weaknesses.keys()):
            cat_weaknesses = weaknesses[category_name]
            html += f'  <h3 style="color: #667eea; margin-top: 20px; margin-bottom: 15px;">{category_name.title()}</h3>\n'

            for weakness in cat_weaknesses:
                severity = weakness.get("severity", "medium")
                weakness_type = weakness.get("type", "").replace("_", " ").title()
                message = weakness.get("message", "")

                html += f'  <div class="weakness {severity}">\n'
                html += f'    <div class="weakness-type">{weakness_type}</div>\n'
                html += f'    <div class="weakness-message">{message}</div>\n'
                html += "  </div>\n"

        html += "</div>\n"
        return html


# Test functions


def load_test_predictions(category: str) -> List[str]:
    """Load test predictions for a category.

    For this baseline test, we use a mock predictor that returns the expected
    verdicts, simulating a perfect predictor. In production, this would call
    the actual ML pipeline.

    Args:
        category: Category name

    Returns:
        List of predicted verdicts
    """
    evaluator = CategoryAccuracyEvaluator()
    claims = evaluator.load_category_claims(category)
    # Return expected verdicts as predictions (perfect baseline)
    return [claim.get("expected_verdict", "INSUFFICIENT") for claim in claims]


@pytest.fixture
def category_evaluator():
    """Fixture providing CategoryAccuracyEvaluator instance."""
    return CategoryAccuracyEvaluator()


@pytest.mark.accuracy
@pytest.mark.category
def test_category_evaluation_politics(category_evaluator):
    """Test accuracy evaluation for politics category."""
    result = category_evaluator.evaluate_category("politics")

    assert result is not None
    assert result["category"] == "politics"
    assert result["claim_count"] > 0
    assert "accuracy" in result
    assert "macro_f1" in result
    assert "claims" in result

    print(f"Politics accuracy: {result['accuracy']:.1%}")


@pytest.mark.accuracy
@pytest.mark.category
def test_category_evaluation_science(category_evaluator):
    """Test accuracy evaluation for science category."""
    result = category_evaluator.evaluate_category("science")

    assert result is not None
    assert result["category"] == "science"
    assert result["claim_count"] > 0
    assert "accuracy" in result
    assert "macro_f1" in result

    print(f"Science accuracy: {result['accuracy']:.1%}")


@pytest.mark.accuracy
@pytest.mark.category
def test_category_evaluation_health(category_evaluator):
    """Test accuracy evaluation for health category."""
    result = category_evaluator.evaluate_category("health")

    assert result is not None
    assert result["category"] == "health"
    assert result["claim_count"] > 0
    assert "accuracy" in result
    assert "macro_f1" in result

    print(f"Health accuracy: {result['accuracy']:.1%}")


@pytest.mark.accuracy
@pytest.mark.category
def test_category_evaluation_current_events(category_evaluator):
    """Test accuracy evaluation for current events category."""
    result = category_evaluator.evaluate_category("current_events")

    assert result is not None
    assert result["category"] == "current_events"
    assert result["claim_count"] > 0
    assert "accuracy" in result
    assert "macro_f1" in result

    print(f"Current events accuracy: {result['accuracy']:.1%}")


@pytest.mark.accuracy
@pytest.mark.category
def test_category_evaluation_historical(category_evaluator):
    """Test accuracy evaluation for historical category."""
    result = category_evaluator.evaluate_category("historical")

    assert result is not None
    assert result["category"] == "historical"
    assert result["claim_count"] > 0
    assert "accuracy" in result
    assert "macro_f1" in result

    print(f"Historical accuracy: {result['accuracy']:.1%}")


@pytest.mark.accuracy
@pytest.mark.category
def test_all_categories_evaluation(category_evaluator):
    """Test accuracy evaluation for all categories."""
    results = category_evaluator.evaluate_all_categories()

    assert len(results) > 0
    assert all("accuracy" in result for result in results.values())

    for category, result in results.items():
        print(f"{category}: {result['accuracy']:.1%} ({result['claim_count']} samples)")


@pytest.mark.accuracy
@pytest.mark.category
def test_category_breakdown_generation(category_evaluator):
    """Test generation of category performance breakdown."""
    category_evaluator.evaluate_all_categories()
    breakdown = category_evaluator.generate_category_breakdown()

    assert "categories" in breakdown
    assert "aggregate" in breakdown
    assert "rankings" in breakdown
    assert "weaknesses" in breakdown

    # Verify categories are in breakdown
    assert len(breakdown["categories"]) > 0

    # Verify aggregate metrics
    agg = breakdown["aggregate"]
    assert "total_samples" in agg
    assert "total_categories" in agg
    assert "weighted_accuracy" in agg


@pytest.mark.accuracy
@pytest.mark.category
def test_save_category_breakdown(category_evaluator, tmp_path):
    """Test saving category breakdown to JSON."""
    category_evaluator.evaluate_all_categories()
    breakdown = category_evaluator.generate_category_breakdown()

    output_file = str(tmp_path / "category_breakdown.json")
    saved_path = category_evaluator.save_category_breakdown(breakdown, output_file)

    assert Path(saved_path).exists()

    # Verify saved content
    with open(saved_path, "r") as f:
        saved_data = json.load(f)

    assert "categories" in saved_data
    assert len(saved_data["categories"]) > 0


@pytest.mark.accuracy
@pytest.mark.category
def test_generate_category_html_report(category_evaluator, tmp_path):
    """Test generation of category HTML report."""
    category_evaluator.evaluate_all_categories()
    breakdown = category_evaluator.generate_category_breakdown()

    output_file = str(tmp_path / "category_report.html")
    saved_path = category_evaluator.generate_category_html_report(breakdown, output_file)

    assert Path(saved_path).exists()

    # Verify HTML content
    with open(saved_path, "r") as f:
        content = f.read()

    assert "<html" in content
    assert "Category Accuracy Analysis Report" in content
    assert "Category Performance Overview" in content


@pytest.mark.accuracy
@pytest.mark.category
def test_identify_category_weaknesses(category_evaluator):
    """Test identification of category-specific weaknesses."""
    category_evaluator.evaluate_all_categories()
    breakdown = category_evaluator.generate_category_breakdown()

    weaknesses = breakdown.get("weaknesses", {})

    # Weaknesses should be a dictionary
    assert isinstance(weaknesses, dict)

    # Print identified weaknesses
    for category, cat_weaknesses in weaknesses.items():
        if cat_weaknesses:
            print(f"\n{category.upper()} weaknesses:")
            for weakness in cat_weaknesses:
                print(f"  - {weakness.get('message')}")


@pytest.mark.accuracy
@pytest.mark.category
def test_category_rankings(category_evaluator):
    """Test generation of category rankings."""
    category_evaluator.evaluate_all_categories()
    breakdown = category_evaluator.generate_category_breakdown()

    rankings = breakdown.get("rankings", {})

    assert "by_accuracy" in rankings
    assert "by_f1" in rankings

    # Verify rankings are sorted
    by_accuracy = rankings["by_accuracy"]
    if len(by_accuracy) > 1:
        for i in range(len(by_accuracy) - 1):
            assert by_accuracy[i]["accuracy"] >= by_accuracy[i + 1]["accuracy"]

    # Print rankings
    print("\nRankings by Accuracy:")
    for rank, item in enumerate(by_accuracy, 1):
        print(f"  {rank}. {item['category']}: {item['accuracy']:.1%}")
