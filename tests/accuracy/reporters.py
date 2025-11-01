"""Report generation module for accuracy testing framework.

This module provides report generation in multiple formats:
- HTML reports with interactive visualizations
- JSON reports for machine consumption
- Text summaries for quick review
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class Reporter:
    """Generate accuracy test reports in multiple formats."""

    def __init__(self, output_dir: str = "tests/accuracy/results"):
        """Initialize reporter.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_html_report(
        self,
        metrics: Dict[str, Any],
        output_file: Optional[str] = None,
        title: str = "Accuracy Testing Report",
    ) -> str:
        """Generate interactive HTML report.

        Args:
            metrics: Metrics dictionary from evaluation
            output_file: Output file path
            title: Report title

        Returns:
            Path to generated report
        """
        if output_file is None:
            output_file = str(self.output_dir / "accuracy_report.html")

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Extract data
        accuracy = metrics.get("accuracy", 0)
        macro_f1 = metrics.get("macro_f1", 0)
        weighted_f1 = metrics.get("weighted_f1", 0)
        samples = metrics.get("total_samples", 0)
        timestamp = metrics.get("timestamp", datetime.now().isoformat())

        precision = metrics.get("precision", {})
        recall = metrics.get("recall", {})
        f1 = metrics.get("f1", {})
        confusion_matrix = metrics.get("confusion_matrix", {})
        per_category = metrics.get("per_category", {})

        # Generate confusion matrix HTML
        cm_html = self._generate_confusion_matrix_html(confusion_matrix)

        # Generate verdict metrics table
        verdict_table = self._generate_verdict_metrics_table(precision, recall, f1)

        # Generate category breakdown
        category_section = self._generate_category_section(per_category)

        # Generate HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
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
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header .timestamp {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        .metric-card h3 {{
            color: #667eea;
            margin-bottom: 10px;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
        }}
        .metric-unit {{
            font-size: 0.5em;
            color: #999;
        }}
        .section {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
            font-size: 1.5em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
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
        .verdict-name {{
            font-weight: 600;
            color: #333;
        }}
        .number {{
            text-align: right;
            font-variant-numeric: tabular-nums;
        }}
        .matrix {{
            display: inline-block;
            margin: 20px 0;
        }}
        .matrix-row {{
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
            align-items: center;
        }}
        .matrix-label {{
            width: 100px;
            text-align: right;
            font-weight: 600;
        }}
        .matrix-cell {{
            width: 100px;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #f0f0f0;
            font-weight: 600;
        }}
        .matrix-header {{
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
            margin-left: 100px;
        }}
        .matrix-col-header {{
            width: 100px;
            text-align: center;
            font-weight: 600;
        }}
        .category-subsection {{
            margin-bottom: 20px;
            padding: 15px;
            background-color: #f9f9f9;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }}
        .category-name {{
            font-weight: 600;
            color: #667eea;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        .status {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        .status.success {{
            background-color: #d4edda;
            color: #155724;
        }}
        .status.warning {{
            background-color: #fff3cd;
            color: #856404;
        }}
        .status.danger {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .footer {{
            text-align: center;
            color: #999;
            padding: 20px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div class="timestamp">Generated: {timestamp}</div>
            <div class="timestamp">Total Samples: {samples}</div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Overall Accuracy</h3>
                <div class="metric-value">
                    {accuracy:.1%}
                    <span class="metric-unit"></span>
                </div>
            </div>
            <div class="metric-card">
                <h3>Macro F1 Score</h3>
                <div class="metric-value">
                    {macro_f1:.3f}
                    <span class="metric-unit"></span>
                </div>
            </div>
            <div class="metric-card">
                <h3>Weighted F1 Score</h3>
                <div class="metric-value">
                    {weighted_f1:.3f}
                    <span class="metric-unit"></span>
                </div>
            </div>
            <div class="metric-card">
                <h3>Sample Size</h3>
                <div class="metric-value">
                    {samples}
                    <span class="metric-unit">claims</span>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Per-Verdict Metrics</h2>
            {verdict_table}
        </div>

        <div class="section">
            <h2>Confusion Matrix</h2>
            <p>Rows: Actual verdicts, Columns: Predicted verdicts</p>
            {cm_html}
        </div>

        {category_section}

        <div class="footer">
            <p>Accuracy Testing Framework for TruthGraph Fact Verification Pipeline</p>
        </div>
    </div>
</body>
</html>
"""

        with open(output_path, "w") as f:
            f.write(html_content)

        return str(output_path)

    def generate_json_report(
        self,
        metrics: Dict[str, Any],
        output_file: Optional[str] = None,
    ) -> str:
        """Generate machine-readable JSON report.

        Args:
            metrics: Metrics dictionary from evaluation
            output_file: Output file path

        Returns:
            Path to generated report
        """
        if output_file is None:
            output_file = str(self.output_dir / "accuracy_report.json")

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(metrics, f, indent=2)

        return str(output_path)

    def generate_summary(self, metrics: Dict[str, Any]) -> str:
        """Generate text summary of metrics.

        Args:
            metrics: Metrics dictionary from evaluation

        Returns:
            Text summary
        """
        accuracy = metrics.get("accuracy", 0)
        macro_f1 = metrics.get("macro_f1", 0)
        weighted_f1 = metrics.get("weighted_f1", 0)
        samples = metrics.get("total_samples", 0)
        timestamp = metrics.get("timestamp", datetime.now().isoformat())

        precision = metrics.get("precision", {})
        recall = metrics.get("recall", {})
        f1 = metrics.get("f1", {})
        confusion_matrix = metrics.get("confusion_matrix", {})
        per_category = metrics.get("per_category", {})

        summary = f"""
{'='*60}
ACCURACY TESTING REPORT
{'='*60}

Generated: {timestamp}
Total Samples: {samples}

OVERALL METRICS
{'='*60}
Accuracy:           {accuracy:.1%}
Macro F1 Score:     {macro_f1:.4f}
Weighted F1 Score:  {weighted_f1:.4f}

PER-VERDICT METRICS
{'='*60}
Verdict          Precision    Recall      F1 Score
{'-'*60}
"""
        for verdict in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]:
            p = precision.get(verdict, 0)
            r = recall.get(verdict, 0)
            f = f1.get(verdict, 0)
            summary += f"{verdict:<16} {p:>10.4f}  {r:>10.4f}  {f:>10.4f}\n"

        summary += f"\nCONFUSION MATRIX\n{'='*60}\n"
        summary += "Predicted >>\nActual v    SUPPORTED   REFUTED   INSUFFICIENT\n"
        summary += "-" * 60 + "\n"

        for actual in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]:
            row_data = confusion_matrix.get(actual, {})
            s = row_data.get("SUPPORTED", 0)
            r = row_data.get("REFUTED", 0)
            i = row_data.get("INSUFFICIENT", 0)
            summary += f"{actual:<11} {s:>10}  {r:>10}  {i:>10}\n"

        if per_category:
            summary += f"\nPER-CATEGORY BREAKDOWN\n{'='*60}\n"
            for category, cat_metrics in per_category.items():
                cat_acc = cat_metrics.get("accuracy", 0)
                cat_samples = cat_metrics.get("samples", 0)
                cat_f1 = cat_metrics.get("macro_f1", 0)
                summary += f"\n{category.upper()}\n"
                summary += f"  Samples:  {cat_samples}\n"
                summary += f"  Accuracy: {cat_acc:.1%}\n"
                summary += f"  F1 Score: {cat_f1:.4f}\n"

        summary += f"\n{'='*60}\n"

        return summary

    def save_summary(
        self,
        metrics: Dict[str, Any],
        output_file: Optional[str] = None,
    ) -> str:
        """Save text summary to file.

        Args:
            metrics: Metrics dictionary from evaluation
            output_file: Output file path

        Returns:
            Path to saved file
        """
        if output_file is None:
            output_file = str(self.output_dir / "accuracy_summary.txt")

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        summary = self.generate_summary(metrics)
        with open(output_path, "w") as f:
            f.write(summary)

        return str(output_path)

    @staticmethod
    def _generate_confusion_matrix_html(confusion_matrix: Dict[str, Dict[str, int]]) -> str:
        """Generate HTML representation of confusion matrix.

        Args:
            confusion_matrix: Confusion matrix dictionary

        Returns:
            HTML string for confusion matrix
        """
        verdicts = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]

        html = '<div class="matrix">\n'
        html += '  <div class="matrix-header">\n'
        html += '    <div style="width: 100px;"></div>\n'
        for v in verdicts:
            html += f'    <div class="matrix-col-header">{v}</div>\n'
        html += '  </div>\n'

        for actual in verdicts:
            html += '  <div class="matrix-row">\n'
            html += f'    <div class="matrix-label">{actual}</div>\n'

            row_data = confusion_matrix.get(actual, {})
            for predicted in verdicts:
                count = row_data.get(predicted, 0)
                color_intensity = min(100, (count / 10) * 100) if count > 0 else 0
                bg_color = f'rgba(102, 126, 234, {color_intensity / 100})'
                html += f'    <div class="matrix-cell" style="background-color: {bg_color};">{count}</div>\n'

            html += '  </div>\n'

        html += '</div>\n'
        return html

    @staticmethod
    def _generate_verdict_metrics_table(
        precision: Dict[str, float],
        recall: Dict[str, float],
        f1: Dict[str, float],
    ) -> str:
        """Generate HTML table for verdict metrics.

        Args:
            precision: Precision scores by verdict
            recall: Recall scores by verdict
            f1: F1 scores by verdict

        Returns:
            HTML string for table
        """
        html = '<table>\n'
        html += '  <thead>\n'
        html += '    <tr>\n'
        html += '      <th>Verdict</th>\n'
        html += '      <th class="number">Precision</th>\n'
        html += '      <th class="number">Recall</th>\n'
        html += '      <th class="number">F1 Score</th>\n'
        html += '    </tr>\n'
        html += '  </thead>\n'
        html += '  <tbody>\n'

        for verdict in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]:
            p = precision.get(verdict, 0)
            r = recall.get(verdict, 0)
            f = f1.get(verdict, 0)
            html += '    <tr>\n'
            html += f'      <td class="verdict-name">{verdict}</td>\n'
            html += f'      <td class="number">{p:.4f}</td>\n'
            html += f'      <td class="number">{r:.4f}</td>\n'
            html += f'      <td class="number">{f:.4f}</td>\n'
            html += '    </tr>\n'

        html += '  </tbody>\n'
        html += '</table>\n'
        return html

    @staticmethod
    def _generate_category_section(per_category: Dict[str, Dict[str, Any]]) -> str:
        """Generate HTML section for per-category breakdown.

        Args:
            per_category: Per-category metrics dictionary

        Returns:
            HTML string for category section
        """
        if not per_category:
            return ""

        html = '<div class="section">\n'
        html += '  <h2>Per-Category Analysis</h2>\n'

        for category, metrics in sorted(per_category.items()):
            accuracy = metrics.get("accuracy", 0)
            samples = metrics.get("samples", 0)
            f1 = metrics.get("macro_f1", 0)

            html += '  <div class="category-subsection">\n'
            html += f'    <div class="category-name">{category.title()}</div>\n'
            html += f'    <div>Samples: <strong>{samples}</strong></div>\n'
            html += f'    <div>Accuracy: <strong>{accuracy:.1%}</strong></div>\n'
            html += f'    <div>F1 Score: <strong>{f1:.4f}</strong></div>\n'
            html += '  </div>\n'

        html += '</div>\n'
        return html
