"""Corpus loaders for importing evidence data from various formats.

This package provides loader implementations for different corpus formats:
- CSV: Comma-separated values with configurable columns
- JSON: JSON arrays or JSONL (newline-delimited JSON)

All loaders implement the BaseCorpusLoader interface for consistent usage.

Example:
    >>> from scripts.corpus_loaders import get_loader
    >>> loader = get_loader('csv', 'evidence.csv')
    >>> for item in loader.load():
    ...     print(item['content'])
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base_loader import BaseCorpusLoader

__all__ = [
    "BaseCorpusLoader",
    "CSVCorpusLoader",
    "JSONCorpusLoader",
    "get_loader",
]


def get_loader(format_type: str, file_path: Path | str) -> "BaseCorpusLoader":
    """Factory function to get appropriate loader for format.

    Args:
        format_type: Format type ('csv' or 'json')
        file_path: Path to corpus file

    Returns:
        Appropriate loader instance

    Raises:
        ValueError: If format_type is not supported

    Example:
        >>> loader = get_loader('csv', 'data/evidence.csv')
        >>> loader = get_loader('json', 'data/evidence.json')
    """
    from .csv_loader import CSVCorpusLoader
    from .json_loader import JSONCorpusLoader

    format_type = format_type.lower()
    file_path = Path(file_path)

    loaders = {
        "csv": CSVCorpusLoader,
        "json": JSONCorpusLoader,
        "jsonl": JSONCorpusLoader,
    }

    if format_type not in loaders:
        raise ValueError(
            f"Unsupported format: {format_type}. Supported formats: {', '.join(loaders.keys())}"
        )

    return loaders[format_type](file_path)
