"""Edge case validation utilities for Feature 3.3.

This package provides comprehensive tools for handling edge cases in fact verification:

- EdgeCaseDataLoader: Load and validate edge case test data
- EdgeCaseClassifier: Classify claims by edge case characteristics
- EdgeCaseResultsHandler: Aggregate and report test results

Edge case categories supported:
- insufficient_evidence: Claims with limited verification sources
- contradictory_evidence: Claims with conflicting evidence
- ambiguous_phrasing: Claims with unclear or vague language
- long_claims: Claims exceeding 50 words
- short_claims: Claims with 5 or fewer words
- special_characters: Claims with mathematical/scientific symbols
- multilingual: Claims in non-English languages
- complex_technical: Claims with specialized technical terminology
"""

from .classifier import EdgeCaseClassifier
from .data_loader import EdgeCaseDataLoader
from .results_handler import EdgeCaseResultsHandler

__all__ = [
    "EdgeCaseDataLoader",
    "EdgeCaseClassifier",
    "EdgeCaseResultsHandler",
]

__version__ = "1.0.0"
