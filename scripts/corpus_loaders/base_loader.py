"""Abstract base class for corpus loaders.

Defines the interface that all corpus loaders must implement.
Supports validation, iteration, and progress tracking.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterator


class BaseCorpusLoader(ABC):
    """Abstract base class for corpus loaders.

    All corpus loaders must implement this interface to ensure
    consistent behavior across different file formats.

    Attributes:
        file_path: Path to the corpus file to load
        total_count: Total number of items (if known), used for progress bars

    Example:
        >>> class MyLoader(BaseCorpusLoader):
        ...     def load(self):
        ...         yield {"id": "1", "content": "text"}
        ...     def validate(self, item):
        ...         return "content" in item
    """

    def __init__(self, file_path: Path | str) -> None:
        """Initialize loader with file path.

        Args:
            file_path: Path to corpus file to load

        Raises:
            FileNotFoundError: If file does not exist
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        self.total_count: int = 0

    @abstractmethod
    def load(self) -> Iterator[dict[str, Any]]:
        """Load corpus and yield evidence items.

        This is the main method that reads the corpus file and yields
        individual evidence items as dictionaries.

        Yields:
            Dictionary containing evidence fields:
                - id: Unique identifier (optional, will be generated if missing)
                - content: Evidence text content (required)
                - source: Source name (optional)
                - url: Source URL (optional)
                - Any additional metadata fields

        Raises:
            ValueError: If file format is invalid
            IOError: If file cannot be read

        Example:
            >>> for item in loader.load():
            ...     print(item['content'])
        """
        pass

    @abstractmethod
    def validate(self, item: dict[str, Any]) -> bool:
        """Validate evidence item format.

        Checks if an evidence item has all required fields and
        valid data types.

        Args:
            item: Evidence item dictionary to validate

        Returns:
            True if item is valid, False otherwise

        Example:
            >>> item = {"content": "Evidence text", "source": "Wikipedia"}
            >>> loader.validate(item)
            True
            >>> loader.validate({})
            False
        """
        pass

    def get_total_count(self) -> int:
        """Get total number of items (for progress bar).

        Returns total count if known, otherwise 0. This is used
        to display accurate progress bars.

        Returns:
            Total number of items, or 0 if unknown

        Example:
            >>> loader.get_total_count()
            1000
        """
        return self.total_count

    def _validate_required_fields(self, item: dict[str, Any]) -> bool:
        """Check if item has required fields.

        All evidence items must have at minimum a 'content' field
        with non-empty text.

        Args:
            item: Evidence item to check

        Returns:
            True if item has required fields, False otherwise
        """
        # Content is the only truly required field
        if 'content' not in item:
            return False

        # Content must be non-empty string
        if not isinstance(item['content'], str) or not item['content'].strip():
            return False

        return True

    def __repr__(self) -> str:
        """String representation of loader."""
        return f"{self.__class__.__name__}(file_path={self.file_path})"
