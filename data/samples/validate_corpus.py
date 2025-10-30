#!/usr/bin/env python3
"""
Validate TruthGraph Sample Evidence Corpus.

This script validates the evidence corpus for:
- Required fields presence
- Content quality (length, format)
- URL format validation
- Category validity
- Duplicate detection
- Statistical analysis
"""

import json
import csv
import re
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import urlparse


class CorpusValidator:
    """Validator for evidence corpus."""

    REQUIRED_FIELDS = ['id', 'content', 'source', 'url', 'category', 'relevance', 'language', 'date_added']
    VALID_CATEGORIES = ['science', 'health', 'history', 'technology', 'politics', 'geography']
    VALID_RELEVANCE = ['high', 'medium', 'low']
    VALID_LANGUAGES = ['en']

    MIN_CONTENT_LENGTH = 50
    MAX_CONTENT_LENGTH = 2000

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.seen_ids: Set[str] = set()
        self.seen_content: Set[str] = set()

    def validate_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def validate_document(self, doc: Dict, index: int) -> bool:
        """Validate a single evidence document."""
        doc_id = doc.get('id', f'document_{index}')
        has_error = False

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in doc:
                self.errors.append(f"{doc_id}: Missing required field '{field}'")
                has_error = True

        if has_error:
            return False

        # Validate ID uniqueness
        if doc['id'] in self.seen_ids:
            self.errors.append(f"{doc_id}: Duplicate ID found")
            has_error = True
        else:
            self.seen_ids.add(doc['id'])

        # Validate ID format (sample_ev_NNN)
        if not re.match(r'^sample_ev_\d{3}$', doc['id']):
            self.warnings.append(f"{doc_id}: ID doesn't match expected format 'sample_ev_NNN'")

        # Validate content
        content = doc.get('content', '')
        content_length = len(content)

        if content_length < self.MIN_CONTENT_LENGTH:
            self.warnings.append(f"{doc_id}: Content too short ({content_length} chars, min {self.MIN_CONTENT_LENGTH})")
        elif content_length > self.MAX_CONTENT_LENGTH:
            self.warnings.append(f"{doc_id}: Content too long ({content_length} chars, max {self.MAX_CONTENT_LENGTH})")

        # Check for duplicate content
        if content in self.seen_content:
            self.errors.append(f"{doc_id}: Duplicate content found")
            has_error = True
        else:
            self.seen_content.add(content)

        # Validate URL
        if not self.validate_url(doc.get('url', '')):
            self.errors.append(f"{doc_id}: Invalid URL format '{doc.get('url', '')}'")
            has_error = True

        # Validate category
        if doc.get('category') not in self.VALID_CATEGORIES:
            self.errors.append(f"{doc_id}: Invalid category '{doc.get('category')}'. Must be one of {self.VALID_CATEGORIES}")
            has_error = True

        # Validate relevance
        if doc.get('relevance') not in self.VALID_RELEVANCE:
            self.warnings.append(f"{doc_id}: Invalid relevance '{doc.get('relevance')}'. Should be one of {self.VALID_RELEVANCE}")

        # Validate language
        if doc.get('language') not in self.VALID_LANGUAGES:
            self.warnings.append(f"{doc_id}: Invalid language '{doc.get('language')}'. Should be one of {self.VALID_LANGUAGES}")

        # Validate source is not empty
        if not doc.get('source', '').strip():
            self.warnings.append(f"{doc_id}: Empty source field")

        return not has_error

    def validate_json_corpus(self, file_path: Path) -> bool:
        """Validate JSON corpus file."""
        print(f"\nValidating JSON corpus: {file_path}")
        print("-" * 60)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                evidence_list = json.load(f)

            if not isinstance(evidence_list, list):
                self.errors.append("JSON corpus must be a list of evidence documents")
                return False

            print(f"Found {len(evidence_list)} documents")

            all_valid = True
            for i, doc in enumerate(evidence_list):
                if not self.validate_document(doc, i):
                    all_valid = False

            return all_valid

        except json.JSONDecodeError as e:
            self.errors.append(f"JSON parsing error: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Error reading JSON file: {e}")
            return False

    def validate_csv_corpus(self, file_path: Path) -> bool:
        """Validate CSV corpus file."""
        print(f"\nValidating CSV corpus: {file_path}")
        print("-" * 60)

        # Reset for CSV validation
        self.seen_ids.clear()
        self.seen_content.clear()

        try:
            with open(file_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)

                # Check header
                if reader.fieldnames != self.REQUIRED_FIELDS:
                    self.errors.append(f"CSV header mismatch. Expected {self.REQUIRED_FIELDS}, got {reader.fieldnames}")
                    return False

                documents = list(reader)
                print(f"Found {len(documents)} documents")

                all_valid = True
                for i, doc in enumerate(documents):
                    if not self.validate_document(doc, i):
                        all_valid = False

                return all_valid

        except Exception as e:
            self.errors.append(f"Error reading CSV file: {e}")
            return False

    def validate_metadata(self, file_path: Path, expected_count: int) -> bool:
        """Validate metadata file."""
        print(f"\nValidating metadata: {file_path}")
        print("-" * 60)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            required_meta_fields = ['name', 'version', 'date_created', 'total_items', 'categories', 'sources', 'languages', 'statistics']

            for field in required_meta_fields:
                if field not in metadata:
                    self.errors.append(f"Metadata missing required field '{field}'")

            # Validate total_items matches actual count
            if metadata.get('total_items') != expected_count:
                self.errors.append(f"Metadata total_items ({metadata.get('total_items')}) doesn't match actual count ({expected_count})")

            # Validate categories sum
            if 'categories' in metadata:
                category_sum = sum(metadata['categories'].values())
                if category_sum != expected_count:
                    self.errors.append(f"Category counts ({category_sum}) don't sum to total_items ({expected_count})")

            print(f"Metadata total items: {metadata.get('total_items')}")
            print(f"Categories: {metadata.get('categories')}")

            return len(self.errors) == 0

        except Exception as e:
            self.errors.append(f"Error reading metadata file: {e}")
            return False

    def print_statistics(self):
        """Print validation statistics."""
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)

        if not self.errors and not self.warnings:
            print("SUCCESS: All validations passed!")
        else:
            if self.errors:
                print(f"\nERRORS: {len(self.errors)}")
                for error in self.errors[:20]:  # Show first 20
                    print(f"  - {error}")
                if len(self.errors) > 20:
                    print(f"  ... and {len(self.errors) - 20} more errors")

            if self.warnings:
                print(f"\nWARNINGS: {len(self.warnings)}")
                for warning in self.warnings[:20]:  # Show first 20
                    print(f"  - {warning}")
                if len(self.warnings) > 20:
                    print(f"  ... and {len(self.warnings) - 20} more warnings")

        print("\nUnique IDs found:", len(self.seen_ids))
        print("Unique content found:", len(self.seen_content))


def main():
    """Main validation function."""
    corpus_dir = Path(__file__).parent

    json_file = corpus_dir / "evidence_corpus.json"
    csv_file = corpus_dir / "evidence_corpus.csv"
    metadata_file = corpus_dir / "metadata.json"

    print("=" * 60)
    print("TruthGraph Sample Evidence Corpus Validator")
    print("=" * 60)

    validator = CorpusValidator()

    # Validate JSON
    json_valid = validator.validate_json_corpus(json_file)
    json_count = len(validator.seen_ids)

    # Validate CSV
    csv_valid = validator.validate_csv_corpus(csv_file)
    csv_count = len(validator.seen_ids)

    # Validate metadata
    metadata_valid = validator.validate_metadata(metadata_file, json_count)

    # Check JSON and CSV have same count
    if json_count != csv_count:
        validator.errors.append(f"JSON and CSV have different document counts (JSON: {json_count}, CSV: {csv_count})")

    # Print statistics
    validator.print_statistics()

    # Return exit code
    if validator.errors:
        print("\nValidation FAILED")
        return 1
    elif validator.warnings:
        print("\nValidation PASSED with warnings")
        return 0
    else:
        print("\nValidation PASSED")
        return 0


if __name__ == "__main__":
    exit(main())
