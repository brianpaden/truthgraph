"""CSV corpus loader implementation.

Loads evidence data from CSV files with configurable column mappings.
Supports large files with memory-efficient chunked reading.
"""

import csv
import logging
from pathlib import Path
from typing import Any, Iterator

from .base_loader import BaseCorpusLoader

logger = logging.getLogger(__name__)


class CSVCorpusLoader(BaseCorpusLoader):
    """Loader for CSV-formatted corpus files.

    Supports both standard CSV format and TSV (tab-separated).
    Automatically detects column names from header row.

    Expected columns (flexible naming):
        - id: Unique identifier (optional)
        - content/text: Evidence content (required)
        - source/source_name: Source name (optional)
        - url/source_url: Source URL (optional)

    Example CSV format:
        id,content,source,url
        ev_001,"Evidence text...",Wikipedia,https://...
        ev_002,"More evidence...",Reuters,https://...

    Args:
        file_path: Path to CSV file
        delimiter: Column delimiter (default: ',')
        encoding: File encoding (default: 'utf-8')

    Example:
        >>> loader = CSVCorpusLoader('evidence.csv')
        >>> for item in loader.load():
        ...     print(item['content'])
    """

    def __init__(
        self,
        file_path: Path | str,
        delimiter: str = ',',
        encoding: str = 'utf-8',
    ) -> None:
        """Initialize CSV loader.

        Args:
            file_path: Path to CSV file
            delimiter: Column delimiter (default: ',')
            encoding: File encoding (default: 'utf-8')
        """
        super().__init__(file_path)
        self.delimiter = delimiter
        self.encoding = encoding

        # Try to count total rows for progress bar
        try:
            with open(self.file_path, encoding=self.encoding) as f:
                # Subtract 1 for header row
                self.total_count = sum(1 for _ in f) - 1
            logger.info(f"CSV file contains {self.total_count} rows")
        except Exception as e:
            logger.warning(f"Could not count CSV rows: {e}")
            self.total_count = 0

    def load(self) -> Iterator[dict[str, Any]]:
        """Load CSV file and yield evidence items.

        Reads CSV file row by row for memory efficiency.
        Maps columns to standardized field names.

        Yields:
            Dictionary with standardized fields:
                - id: Row identifier (generated if missing)
                - content: Evidence text
                - source: Source name (if present)
                - url: Source URL (if present)

        Raises:
            ValueError: If CSV is malformed or missing required columns
        """
        logger.info(f"Loading CSV corpus from {self.file_path}")

        try:
            with open(self.file_path, encoding=self.encoding, newline='') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=self.delimiter)

                # Validate header
                if not reader.fieldnames:
                    raise ValueError("CSV file has no header row")

                # Map column names to standard fields
                column_map = self._get_column_mapping(reader.fieldnames)
                logger.info(f"Column mapping: {column_map}")

                # Check for required content column
                if 'content' not in column_map:
                    raise ValueError(
                        f"CSV must have a content/text column. "
                        f"Found columns: {reader.fieldnames}"
                    )

                row_num = 0
                for row in reader:
                    row_num += 1

                    # Map to standard fields
                    item = self._map_row(row, column_map)

                    # Generate ID if missing
                    if 'id' not in item or not item['id']:
                        item['id'] = f"csv_{row_num:06d}"

                    yield item

        except csv.Error as e:
            raise ValueError(f"CSV parsing error at line {reader.line_num}: {e}") from e
        except Exception as e:
            raise ValueError(f"Error loading CSV file: {e}") from e

    def validate(self, item: dict[str, Any]) -> bool:
        """Validate CSV evidence item.

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

    def _get_column_mapping(self, fieldnames: list[str]) -> dict[str, str]:
        """Create mapping from CSV columns to standard field names.

        Supports flexible column naming conventions.

        Args:
            fieldnames: Column names from CSV header

        Returns:
            Dictionary mapping standard field names to CSV column names
        """
        mapping = {}

        # Normalize fieldnames for comparison
        normalized = {name.lower().strip(): name for name in fieldnames}

        # Map content/text column
        for content_variant in ['content', 'text', 'evidence', 'evidence_text']:
            if content_variant in normalized:
                mapping['content'] = normalized[content_variant]
                break

        # Map ID column
        for id_variant in ['id', 'evidence_id', 'doc_id', 'identifier']:
            if id_variant in normalized:
                mapping['id'] = normalized[id_variant]
                break

        # Map source column
        for source_variant in ['source', 'source_name', 'origin']:
            if source_variant in normalized:
                mapping['source'] = normalized[source_variant]
                break

        # Map URL column
        for url_variant in ['url', 'source_url', 'link', 'uri']:
            if url_variant in normalized:
                mapping['url'] = normalized[url_variant]
                break

        return mapping

    def _map_row(self, row: dict[str, Any], column_map: dict[str, str]) -> dict[str, Any]:
        """Map CSV row to standardized item format.

        Args:
            row: CSV row as dictionary
            column_map: Mapping from standard names to CSV columns

        Returns:
            Standardized evidence item
        """
        item: dict[str, Any] = {}

        # Map known fields
        for std_field, csv_field in column_map.items():
            value = row.get(csv_field, '').strip()
            if value:
                item[std_field] = value

        # Include any unmapped columns as metadata
        for csv_field, value in row.items():
            if csv_field not in column_map.values() and value:
                # Use original field name as metadata key
                item[csv_field] = value.strip()

        return item
