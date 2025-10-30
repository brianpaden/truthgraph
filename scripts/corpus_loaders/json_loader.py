"""JSON corpus loader implementation.

Loads evidence data from JSON files in two formats:
1. JSON array: Single array containing all evidence items
2. JSONL: Newline-delimited JSON (one object per line)

JSONL format is preferred for large datasets due to memory efficiency.
"""

import json
import logging
from pathlib import Path
from typing import Any, Iterator

from .base_loader import BaseCorpusLoader

logger = logging.getLogger(__name__)


class JSONCorpusLoader(BaseCorpusLoader):
    """Loader for JSON and JSONL formatted corpus files.

    Supports two JSON formats:

    1. JSON Array format:
        [
          {"id": "ev_001", "content": "...", "source": "..."},
          {"id": "ev_002", "content": "...", "source": "..."}
        ]

    2. JSONL format (newline-delimited JSON):
        {"id": "ev_001", "content": "...", "source": "..."}
        {"id": "ev_002", "content": "...", "source": "..."}

    Field mapping (flexible):
        - id: Unique identifier (optional, will be generated)
        - content/text: Evidence content (required)
        - source/source_name: Source name (optional)
        - url/source_url: Source URL (optional)

    Args:
        file_path: Path to JSON/JSONL file
        is_jsonl: If True, treat as JSONL format (auto-detected if None)
        encoding: File encoding (default: 'utf-8')

    Example:
        >>> loader = JSONCorpusLoader('evidence.json')
        >>> for item in loader.load():
        ...     print(item['content'])
    """

    def __init__(
        self,
        file_path: Path | str,
        is_jsonl: bool | None = None,
        encoding: str = 'utf-8',
    ) -> None:
        """Initialize JSON loader.

        Args:
            file_path: Path to JSON/JSONL file
            is_jsonl: If True, treat as JSONL. If None, auto-detect from extension.
            encoding: File encoding (default: 'utf-8')
        """
        super().__init__(file_path)
        self.encoding = encoding

        # Auto-detect JSONL format
        if is_jsonl is None:
            self.is_jsonl = self.file_path.suffix.lower() in ['.jsonl', '.ndjson']
        else:
            self.is_jsonl = is_jsonl

        # Try to count items for progress bar
        self._count_items()

    def _count_items(self) -> None:
        """Count total items for progress tracking."""
        try:
            if self.is_jsonl:
                # Count lines for JSONL
                with open(self.file_path, encoding=self.encoding) as f:
                    self.total_count = sum(1 for line in f if line.strip())
            else:
                # Load JSON array to count items
                with open(self.file_path, encoding=self.encoding) as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.total_count = len(data)
                    else:
                        self.total_count = 1  # Single object

            logger.info(
                f"JSON{'L' if self.is_jsonl else ''} file contains "
                f"{self.total_count} items"
            )
        except Exception as e:
            logger.warning(f"Could not count JSON items: {e}")
            self.total_count = 0

    def load(self) -> Iterator[dict[str, Any]]:
        """Load JSON/JSONL file and yield evidence items.

        For JSONL, reads line by line for memory efficiency.
        For JSON array, loads entire file (not recommended for large datasets).

        Yields:
            Dictionary with standardized fields:
                - id: Item identifier (generated if missing)
                - content: Evidence text
                - source: Source name (if present)
                - url: Source URL (if present)
                - Additional metadata fields

        Raises:
            ValueError: If JSON is malformed or missing required fields
        """
        logger.info(
            f"Loading {'JSONL' if self.is_jsonl else 'JSON'} corpus from {self.file_path}"
        )

        try:
            if self.is_jsonl:
                yield from self._load_jsonl()
            else:
                yield from self._load_json_array()

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}") from e
        except Exception as e:
            raise ValueError(f"Error loading JSON file: {e}") from e

    def _load_json_array(self) -> Iterator[dict[str, Any]]:
        """Load JSON array format.

        Loads entire array into memory, then yields items.
        Not recommended for large datasets.

        Yields:
            Standardized evidence items
        """
        with open(self.file_path, encoding=self.encoding) as f:
            data = json.load(f)

        # Handle single object vs array
        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            raise ValueError(f"Expected JSON array or object, got {type(data)}")

        for idx, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                logger.warning(f"Skipping non-dict item at index {idx}: {type(item)}")
                continue

            # Normalize field names
            normalized_item = self._normalize_fields(item)

            # Generate ID if missing
            if 'id' not in normalized_item or not normalized_item['id']:
                normalized_item['id'] = f"json_{idx:06d}"

            yield normalized_item

    def _load_jsonl(self) -> Iterator[dict[str, Any]]:
        """Load JSONL (newline-delimited JSON) format.

        Memory-efficient line-by-line processing.

        Yields:
            Standardized evidence items
        """
        line_num = 0
        with open(self.file_path, encoding=self.encoding) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue  # Skip empty lines

                line_num += 1
                try:
                    item = json.loads(line)

                    if not isinstance(item, dict):
                        logger.warning(
                            f"Skipping non-dict item at line {line_num}: {type(item)}"
                        )
                        continue

                    # Normalize field names
                    normalized_item = self._normalize_fields(item)

                    # Generate ID if missing
                    if 'id' not in normalized_item or not normalized_item['id']:
                        normalized_item['id'] = f"jsonl_{line_num:06d}"

                    yield normalized_item

                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON at line {line_num}: {e}")
                    continue

    def validate(self, item: dict[str, Any]) -> bool:
        """Validate JSON evidence item.

        Checks that item has required content field and valid data.

        Args:
            item: Evidence item to validate

        Returns:
            True if valid, False otherwise
        """
        # Use base validation for required fields
        if not self._validate_required_fields(item):
            return False

        # Ensure ID is present (should be generated during load)
        if 'id' not in item or not item['id']:
            return False

        # Optional fields should be strings if present
        for field in ['source', 'url']:
            if field in item and item[field] is not None:
                if not isinstance(item[field], str):
                    return False

        return True

    def _normalize_fields(self, item: dict[str, Any]) -> dict[str, Any]:
        """Normalize JSON field names to standard format.

        Supports flexible field naming conventions.

        Args:
            item: Raw JSON item

        Returns:
            Item with normalized field names
        """
        normalized: dict[str, Any] = {}

        # Map content field (required)
        for content_key in ['content', 'text', 'evidence', 'evidence_text', 'body']:
            if content_key in item:
                normalized['content'] = item[content_key]
                break

        # Map ID field
        for id_key in ['id', 'evidence_id', 'doc_id', 'identifier', '_id']:
            if id_key in item:
                normalized['id'] = str(item[id_key])  # Ensure string
                break

        # Map source field
        for source_key in ['source', 'source_name', 'origin', 'publisher']:
            if source_key in item:
                normalized['source'] = item[source_key]
                break

        # Map URL field
        for url_key in ['url', 'source_url', 'link', 'uri', 'href']:
            if url_key in item:
                normalized['url'] = item[url_key]
                break

        # Include any additional fields as metadata
        known_keys = {
            'content', 'text', 'evidence', 'evidence_text', 'body',
            'id', 'evidence_id', 'doc_id', 'identifier', '_id',
            'source', 'source_name', 'origin', 'publisher',
            'url', 'source_url', 'link', 'uri', 'href'
        }

        for key, value in item.items():
            if key not in known_keys and value is not None:
                normalized[key] = value

        return normalized
