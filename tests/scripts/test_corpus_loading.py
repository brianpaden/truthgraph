"""Tests for corpus loading functionality.

Tests cover:
    - CSV loader
    - JSON/JSONL loaders
    - Base loader interface
    - Validation logic
    - Error handling
"""

import json

# Import loaders - adjust path as needed
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from corpus_loaders import get_loader
from corpus_loaders.csv_loader import CSVCorpusLoader
from corpus_loaders.json_loader import JSONCorpusLoader


class TestBaseCorpusLoader:
    """Test abstract base loader functionality."""

    def test_file_not_found(self):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            CSVCorpusLoader("/nonexistent/file.csv")

    def test_validate_required_fields(self):
        """Test base validation logic."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("id,content\n")
            f.write("1,test\n")
            temp_file = f.name

        try:
            loader = CSVCorpusLoader(temp_file)

            # Valid item
            assert loader._validate_required_fields({"content": "test"})

            # Missing content
            assert not loader._validate_required_fields({"id": "1"})

            # Empty content
            assert not loader._validate_required_fields({"content": ""})
            assert not loader._validate_required_fields({"content": "   "})

        finally:
            Path(temp_file).unlink()


class TestCSVCorpusLoader:
    """Test CSV loader functionality."""

    def test_basic_csv_loading(self):
        """Test loading basic CSV file."""
        csv_content = """id,content,source,url
ev_001,Earth orbits the Sun,Wikipedia,https://example.com
ev_002,Water boils at 100C,Chemistry,https://example.com/chem
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            loader = CSVCorpusLoader(temp_file)

            items = list(loader.load())
            assert len(items) == 2

            # Check first item
            assert items[0]["id"] == "ev_001"
            assert "Earth orbits" in items[0]["content"]
            assert items[0]["source"] == "Wikipedia"
            assert items[0]["url"] == "https://example.com"

            # Check second item
            assert items[1]["id"] == "ev_002"

        finally:
            Path(temp_file).unlink()

    def test_csv_flexible_column_names(self):
        """Test CSV with alternative column names."""
        csv_content = """doc_id,text,source_name,source_url
1,Content here,Source,http://example.com
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            loader = CSVCorpusLoader(temp_file)
            items = list(loader.load())

            assert len(items) == 1
            assert items[0]["content"] == "Content here"
            assert items[0]["source"] == "Source"

        finally:
            Path(temp_file).unlink()

    def test_csv_auto_id_generation(self):
        """Test automatic ID generation when missing."""
        csv_content = """content,source
Text 1,Source 1
Text 2,Source 2
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            loader = CSVCorpusLoader(temp_file)
            items = list(loader.load())

            assert len(items) == 2
            assert items[0]["id"] == "csv_000001"
            assert items[1]["id"] == "csv_000002"

        finally:
            Path(temp_file).unlink()

    def test_csv_missing_content_column(self):
        """Test error when content column is missing."""
        csv_content = """id,source
1,Wikipedia
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            loader = CSVCorpusLoader(temp_file)

            with pytest.raises(ValueError, match="content/text column"):
                list(loader.load())

        finally:
            Path(temp_file).unlink()

    def test_csv_validation(self):
        """Test CSV item validation."""
        csv_content = """id,content
1,Valid content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            loader = CSVCorpusLoader(temp_file)

            # Valid item
            assert loader.validate({"id": "1", "content": "test"})

            # Missing content
            assert not loader.validate({"id": "1"})

            # Missing ID
            assert not loader.validate({"content": "test"})

        finally:
            Path(temp_file).unlink()

    def test_csv_total_count(self):
        """Test total count calculation."""
        csv_content = """id,content
1,Text 1
2,Text 2
3,Text 3
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            loader = CSVCorpusLoader(temp_file)
            assert loader.get_total_count() == 3

        finally:
            Path(temp_file).unlink()


class TestJSONCorpusLoader:
    """Test JSON/JSONL loader functionality."""

    def test_json_array_loading(self):
        """Test loading JSON array format."""
        json_data = [
            {
                "id": "json_001",
                "content": "Content 1",
                "source": "Source 1",
                "url": "http://example.com",
            },
            {"id": "json_002", "content": "Content 2", "source": "Source 2"},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_data, f)
            temp_file = f.name

        try:
            loader = JSONCorpusLoader(temp_file)
            items = list(loader.load())

            assert len(items) == 2
            assert items[0]["id"] == "json_001"
            assert items[0]["content"] == "Content 1"
            assert items[1]["id"] == "json_002"

        finally:
            Path(temp_file).unlink()

    def test_jsonl_loading(self):
        """Test loading JSONL format."""
        jsonl_content = """{"id": "jsonl_001", "content": "Line 1"}
{"id": "jsonl_002", "content": "Line 2"}
{"id": "jsonl_003", "content": "Line 3"}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(jsonl_content)
            temp_file = f.name

        try:
            loader = JSONCorpusLoader(temp_file)
            items = list(loader.load())

            assert len(items) == 3
            assert items[0]["id"] == "jsonl_001"
            assert items[1]["content"] == "Line 2"

        finally:
            Path(temp_file).unlink()

    def test_json_auto_id_generation(self):
        """Test automatic ID generation for JSON items."""
        json_data = [{"content": "Content without ID"}, {"content": "Another one"}]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_data, f)
            temp_file = f.name

        try:
            loader = JSONCorpusLoader(temp_file)
            items = list(loader.load())

            assert len(items) == 2
            assert items[0]["id"] == "json_000001"
            assert items[1]["id"] == "json_000002"

        finally:
            Path(temp_file).unlink()

    def test_jsonl_auto_id_generation(self):
        """Test automatic ID generation for JSONL items."""
        jsonl_content = """{"content": "Line 1"}
{"content": "Line 2"}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(jsonl_content)
            temp_file = f.name

        try:
            loader = JSONCorpusLoader(temp_file)
            items = list(loader.load())

            assert items[0]["id"] == "jsonl_000001"
            assert items[1]["id"] == "jsonl_000002"

        finally:
            Path(temp_file).unlink()

    def test_json_flexible_field_names(self):
        """Test JSON with alternative field names."""
        json_data = [
            {
                "doc_id": "123",
                "text": "Alternative field names",
                "source_name": "Source",
                "source_url": "http://example.com",
            }
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_data, f)
            temp_file = f.name

        try:
            loader = JSONCorpusLoader(temp_file)
            items = list(loader.load())

            assert len(items) == 1
            assert items[0]["content"] == "Alternative field names"
            assert items[0]["source"] == "Source"

        finally:
            Path(temp_file).unlink()

    def test_jsonl_skip_empty_lines(self):
        """Test JSONL skips empty lines."""
        jsonl_content = """{"id": "1", "content": "Line 1"}

{"id": "2", "content": "Line 2"}


{"id": "3", "content": "Line 3"}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(jsonl_content)
            temp_file = f.name

        try:
            loader = JSONCorpusLoader(temp_file)
            items = list(loader.load())

            assert len(items) == 3

        finally:
            Path(temp_file).unlink()

    def test_json_total_count(self):
        """Test total count for JSON."""
        json_data = [{"content": f"Item {i}"} for i in range(10)]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_data, f)
            temp_file = f.name

        try:
            loader = JSONCorpusLoader(temp_file)
            assert loader.get_total_count() == 10

        finally:
            Path(temp_file).unlink()

    def test_jsonl_total_count(self):
        """Test total count for JSONL."""
        jsonl_content = "\n".join([json.dumps({"content": f"Line {i}"}) for i in range(5)])

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(jsonl_content)
            temp_file = f.name

        try:
            loader = JSONCorpusLoader(temp_file)
            assert loader.get_total_count() == 5

        finally:
            Path(temp_file).unlink()


class TestLoaderFactory:
    """Test loader factory function."""

    def test_get_loader_csv(self):
        """Test factory returns CSV loader."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("id,content\n1,test\n")
            temp_file = f.name

        try:
            loader = get_loader("csv", temp_file)
            assert isinstance(loader, CSVCorpusLoader)

        finally:
            Path(temp_file).unlink()

    def test_get_loader_json(self):
        """Test factory returns JSON loader."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('[{"content": "test"}]')
            temp_file = f.name

        try:
            loader = get_loader("json", temp_file)
            assert isinstance(loader, JSONCorpusLoader)

        finally:
            Path(temp_file).unlink()

    def test_get_loader_jsonl(self):
        """Test factory returns JSON loader for JSONL."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"content": "test"}')
            temp_file = f.name

        try:
            loader = get_loader("jsonl", temp_file)
            assert isinstance(loader, JSONCorpusLoader)

        finally:
            Path(temp_file).unlink()

    def test_get_loader_unsupported_format(self):
        """Test factory raises error for unsupported format."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test")
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported format"):
                get_loader("txt", temp_file)

        finally:
            Path(temp_file).unlink()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_csv(self):
        """Test empty CSV file."""
        csv_content = """id,content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            loader = CSVCorpusLoader(temp_file)
            items = list(loader.load())
            assert len(items) == 0

        finally:
            Path(temp_file).unlink()

    def test_empty_json_array(self):
        """Test empty JSON array."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([], f)
            temp_file = f.name

        try:
            loader = JSONCorpusLoader(temp_file)
            items = list(loader.load())
            assert len(items) == 0

        finally:
            Path(temp_file).unlink()

    def test_malformed_json(self):
        """Test malformed JSON raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            temp_file = f.name

        try:
            loader = JSONCorpusLoader(temp_file)

            with pytest.raises(ValueError, match="Invalid JSON"):
                list(loader.load())

        finally:
            Path(temp_file).unlink()

    def test_unicode_content(self):
        """Test handling of Unicode content."""
        csv_content = """id,content
1,"Unicode test: 你好世界 مرحبا العالم"
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
        ) as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            loader = CSVCorpusLoader(temp_file)
            items = list(loader.load())

            assert len(items) == 1
            assert "你好世界" in items[0]["content"]

        finally:
            Path(temp_file).unlink()
