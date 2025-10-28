#!/usr/bin/env python
"""Load FEVER processed data into test fixtures.

This script reads the processed FEVER data and creates pytest-compatible
test fixtures. It copies processed data to the tests/fixtures/fever directory
and ensures proper validation.

Usage:
    python load_fever_sample.py --input-dir ./fever_processed [--validate]
"""

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FEVERSampleLoader:
    """Load processed FEVER data into test fixtures."""

    # Expected files from process_fever_data.py
    REQUIRED_FILES = [
        "fever_sample_claims.json",
        "fever_sample_evidence.json",
        "fever_mapping.json",
    ]

    def __init__(self, input_dir: Path, output_dir: Optional[Path] = None):
        """Initialize loader.

        Args:
            input_dir: Directory with processed FEVER data
            output_dir: Test fixtures directory. Defaults to tests/fixtures/fever
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir) if output_dir else Path("tests/fixtures/fever")

        if not self.input_dir.exists():
            raise ValueError(f"Input directory not found: {self.input_dir}")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Input directory: {self.input_dir.absolute()}")
        logger.info(f"Output directory: {self.output_dir.absolute()}")

    def validate_input(self) -> bool:
        """Validate that all required files exist.

        Returns:
            True if all files present, False otherwise
        """
        logger.info("Validating input files...")
        all_present = True

        for filename in self.REQUIRED_FILES:
            filepath = self.input_dir / filename
            if filepath.exists():
                file_size = filepath.stat().st_size
                logger.info(f"  Found: {filename} ({file_size} bytes)")
            else:
                logger.error(f"  Missing: {filename}")
                all_present = False

        return all_present

    def load_json_file(self, filepath: Path) -> Dict:
        """Load and validate JSON file.

        Args:
            filepath: Path to JSON file

        Returns:
            Parsed JSON data

        Raises:
            ValueError: If file is invalid
        """
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {filepath}: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load {filepath}: {e}")

    def validate_claims(self, claims_data: Dict) -> bool:
        """Validate claims data structure.

        Args:
            claims_data: Loaded claims data

        Returns:
            True if valid, False otherwise
        """
        logger.info("Validating claims structure...")

        if "claims" not in claims_data:
            logger.error("Missing 'claims' key in claims data")
            return False

        claims = claims_data["claims"]
        if not isinstance(claims, list):
            logger.error("'claims' must be a list")
            return False

        if not claims:
            logger.error("Empty claims list")
            return False

        # Validate first claim as sample
        required_fields = ["id", "text", "expected_verdict"]
        first_claim = claims[0]

        for field in required_fields:
            if field not in first_claim:
                logger.error(f"Missing required field '{field}' in claim")
                return False

        # Validate verdict values
        valid_verdicts = ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
        for claim in claims:
            if claim.get("expected_verdict") not in valid_verdicts:
                logger.error(f"Invalid verdict: {claim.get('expected_verdict')}")
                return False

        logger.info(f"  Valid: {len(claims)} claims with required fields")
        return True

    def validate_evidence(self, evidence_data: Dict) -> bool:
        """Validate evidence data structure.

        Args:
            evidence_data: Loaded evidence data

        Returns:
            True if valid, False otherwise
        """
        logger.info("Validating evidence structure...")

        if "evidence" not in evidence_data:
            logger.error("Missing 'evidence' key in evidence data")
            return False

        evidence = evidence_data["evidence"]
        if not isinstance(evidence, list):
            logger.error("'evidence' must be a list")
            return False

        # Evidence can be empty
        if evidence:
            required_fields = ["id", "content"]
            first_item = evidence[0]

            for field in required_fields:
                if field not in first_item:
                    logger.error(f"Missing required field '{field}' in evidence")
                    return False

        logger.info(f"  Valid: {len(evidence)} evidence items")
        return True

    def validate_mapping(self, mapping_data: Dict) -> bool:
        """Validate mapping data structure.

        Args:
            mapping_data: Loaded mapping data

        Returns:
            True if valid, False otherwise
        """
        logger.info("Validating mapping structure...")

        if "mappings" not in mapping_data:
            logger.error("Missing 'mappings' key in mapping data")
            return False

        mappings = mapping_data["mappings"]
        if not isinstance(mappings, dict):
            logger.error("'mappings' must be a dictionary")
            return False

        logger.info(f"  Valid: {len(mappings)} claim-to-verdict mappings")
        return True

    def copy_file(self, source: Path, destination: Path) -> bool:
        """Copy file to destination.

        Args:
            source: Source file path
            destination: Destination file path

        Returns:
            True if successful, False otherwise
        """
        try:
            shutil.copy2(source, destination)
            file_size = destination.stat().st_size
            logger.info(f"Copied {source.name} -> {destination} ({file_size} bytes)")
            return True
        except Exception as e:
            logger.error(f"Failed to copy {source.name}: {e}")
            return False

    def load_all(self, validate: bool = True) -> bool:
        """Load all FEVER fixtures.

        Args:
            validate: Whether to validate data

        Returns:
            True if successful, False otherwise
        """
        logger.info("Loading FEVER fixtures...")

        # Validate input files exist
        if not self.validate_input():
            logger.error("Input validation failed")
            return False

        # Load and validate data if requested
        if validate:
            try:
                claims_data = self.load_json_file(self.input_dir / "fever_sample_claims.json")
                evidence_data = self.load_json_file(self.input_dir / "fever_sample_evidence.json")
                mapping_data = self.load_json_file(self.input_dir / "fever_mapping.json")

                if not self.validate_claims(claims_data):
                    logger.error("Claims validation failed")
                    return False

                if not self.validate_evidence(evidence_data):
                    logger.error("Evidence validation failed")
                    return False

                if not self.validate_mapping(mapping_data):
                    logger.error("Mapping validation failed")
                    return False

            except ValueError as e:
                logger.error(f"Validation failed: {e}")
                return False

        # Copy files
        logger.info("Copying fixture files...")
        success = True

        for filename in self.REQUIRED_FILES:
            source = self.input_dir / filename
            destination = self.output_dir / filename
            if not self.copy_file(source, destination):
                success = False

        # Copy stats if present
        stats_file = self.input_dir / "fever_stats.json"
        if stats_file.exists():
            self.copy_file(stats_file, self.output_dir / "fever_stats.json")

        if success:
            logger.info(f"Successfully loaded FEVER fixtures to {self.output_dir.absolute()}")
        else:
            logger.error("Failed to load some fixture files")

        return success

    def get_fixture_info(self) -> Dict:
        """Get information about loaded fixtures.

        Returns:
            Dictionary with fixture information
        """
        info = {
            "location": str(self.output_dir.absolute()),
            "files": [],
        }

        for filepath in sorted(self.output_dir.glob("*.json")):
            try:
                data = self.load_json_file(filepath)
                info["files"].append(
                    {
                        "name": filepath.name,
                        "size_bytes": filepath.stat().st_size,
                        "metadata": data.get("metadata", {}),
                    }
                )
            except Exception as e:
                logger.warning(f"Could not read {filepath.name}: {e}")

        return info


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Load processed FEVER data into test fixtures")
    parser.add_argument(
        "--input-dir", type=Path, required=True, help="Directory with processed FEVER data"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tests/fixtures/fever"),
        help="Test fixtures output directory (default: tests/fixtures/fever)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        default=True,
        help="Validate data structure (default: True)",
    )
    parser.add_argument(
        "--no-validate", dest="validate", action="store_false", help="Skip validation"
    )
    parser.add_argument(
        "--info", action="store_true", help="Show fixture information after loading"
    )

    args = parser.parse_args()

    try:
        loader = FEVERSampleLoader(input_dir=args.input_dir, output_dir=args.output_dir)

        if loader.load_all(validate=args.validate):
            if args.info:
                info = loader.get_fixture_info()
                print("\nFEVER Fixtures Information:")
                print(json.dumps(info, indent=2))

            logger.info("FEVER fixtures loaded successfully!")
            return 0
        else:
            logger.error("Failed to load FEVER fixtures")
            return 1

    except Exception as e:
        logger.error(f"Failed to load FEVER fixtures: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
