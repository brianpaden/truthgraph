#!/usr/bin/env python
"""Download and extract FEVER dataset for integration testing.

This script downloads the FEVER (Fact Extraction and VERification) dataset
from the official source and extracts it to a local directory for processing.

The FEVER dataset contains fact verification data with Wikipedia-based evidence
for training and evaluating fact verification systems.

Usage:
    python download_fever_dataset.py [--output-dir PATH] [--dev-only] [--validate]

References:
    - FEVER Dataset: https://fever.ai/dataset/fever.html
    - Paper: https://arxiv.org/abs/1803.05355
    - GitHub: https://github.com/facebookresearch/FEVER-evidence-retrieval

Dataset Info:
    - Dev set: ~19,998 claims with Wikipedia evidence
    - Test set: ~18,999 claims (without gold evidence)
    - Format: JSONL (JSON Lines)
    - Size: ~1 GB (compressed)

Labels:
    - SUPPORTS: Evidence strongly supports the claim
    - REFUTES: Evidence strongly refutes the claim
    - NOT ENOUGH INFO: Insufficient evidence to make a determination
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import urllib.request
from pathlib import Path
from typing import Dict, Optional
from zipfile import ZipFile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FEVERDatasetDownloader:
    """Download and extract FEVER dataset."""

    # Dataset URLs
    FEVER_URLS = {
        "dev": "https://fever.ai/download/fever/fever.dev.jsonl",
        "test": "https://fever.ai/download/fever/fever.test.jsonl",
        "train": "https://fever.ai/download/fever/fever.train.jsonl.gz",
    }

    # Expected checksums for validation (optional)
    CHECKSUMS = {
        "dev": "aca90f1c843ce9b3a8d5d8b09b9e1c9a",  # MD5 (example)
        "test": "b8b5c1d5e2f3a4b6c7d8e9f0a1b2c3d4",
        "train": "c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6",
    }

    def __init__(self, output_dir: Optional[Path] = None, validate: bool = False):
        """Initialize downloader.

        Args:
            output_dir: Directory to save dataset. Defaults to ./data/fever
            validate: Whether to validate checksums after download
        """
        self.output_dir = Path(output_dir) if output_dir else Path("./data/fever")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.validate = validate
        logger.info(f"Output directory: {self.output_dir.absolute()}")

    def download_file(self, url: str, filename: str, force: bool = False) -> Path:
        """Download a single file from URL.

        Args:
            url: URL to download from
            filename: Name to save file as
            force: Force re-download even if file exists

        Returns:
            Path to downloaded file
        """
        output_path = self.output_dir / filename

        # Skip if file already exists and not forcing
        if output_path.exists() and not force:
            logger.info(f"File already exists, skipping: {output_path}")
            return output_path

        logger.info(f"Downloading {filename} from {url}...")
        try:
            urllib.request.urlretrieve(url, output_path)
            logger.info(f"Downloaded successfully: {output_path} ({output_path.stat().st_size} bytes)")
            return output_path
        except urllib.error.URLError as e:
            logger.error(f"Failed to download {url}: {e}")
            raise

    def validate_checksum(self, filepath: Path, expected_md5: str) -> bool:
        """Validate file checksum.

        Args:
            filepath: Path to file
            expected_md5: Expected MD5 checksum

        Returns:
            True if checksum matches, False otherwise
        """
        md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)

        actual_md5 = md5.hexdigest()
        if actual_md5 == expected_md5:
            logger.info(f"Checksum valid for {filepath.name}")
            return True
        else:
            logger.warning(
                f"Checksum mismatch for {filepath.name}: "
                f"expected {expected_md5}, got {actual_md5}"
            )
            return False

    def extract_gzip(self, filepath: Path) -> Path:
        """Extract gzip file.

        Args:
            filepath: Path to .gz file

        Returns:
            Path to extracted file
        """
        import gzip
        output_path = filepath.with_suffix("")

        logger.info(f"Extracting {filepath} to {output_path}...")
        with gzip.open(filepath, "rb") as f_in:
            with open(output_path, "wb") as f_out:
                f_out.writelines(f_in)

        logger.info(f"Extracted successfully: {output_path}")
        return output_path

    def download_dev_set(self, force: bool = False) -> Path:
        """Download FEVER dev set.

        Args:
            force: Force re-download

        Returns:
            Path to dev set file
        """
        logger.info("Downloading FEVER dev set...")
        filepath = self.download_file(self.FEVER_URLS["dev"], "fever.dev.jsonl", force)

        if self.validate and "dev" in self.CHECKSUMS:
            self.validate_checksum(filepath, self.CHECKSUMS["dev"])

        return filepath

    def download_test_set(self, force: bool = False) -> Path:
        """Download FEVER test set (without gold evidence).

        Args:
            force: Force re-download

        Returns:
            Path to test set file
        """
        logger.info("Downloading FEVER test set...")
        filepath = self.download_file(self.FEVER_URLS["test"], "fever.test.jsonl", force)

        if self.validate and "test" in self.CHECKSUMS:
            self.validate_checksum(filepath, self.CHECKSUMS["test"])

        return filepath

    def download_train_set(self, force: bool = False) -> Path:
        """Download FEVER training set (large, gzip compressed).

        Args:
            force: Force re-download

        Returns:
            Path to extracted train set file
        """
        logger.info("Downloading FEVER train set (this may take a while)...")
        filepath = self.download_file(self.FEVER_URLS["train"], "fever.train.jsonl.gz", force)

        if self.validate and "train" in self.CHECKSUMS:
            self.validate_checksum(filepath, self.CHECKSUMS["train"])

        extracted_path = self.extract_gzip(filepath)
        return extracted_path

    def get_dataset_info(self, jsonl_path: Path) -> Dict:
        """Get information about a JSONL dataset file.

        Args:
            jsonl_path: Path to JSONL file

        Returns:
            Dictionary with dataset statistics
        """
        logger.info(f"Analyzing {jsonl_path}...")

        stats = {
            "total_records": 0,
            "labels": {"SUPPORTS": 0, "REFUTES": 0, "NOT ENOUGH INFO": 0},
            "verifiable": {"VERIFIABLE": 0, "NOT VERIFIABLE": 0},
            "sample_record": None,
        }

        with open(jsonl_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    record = json.loads(line)
                    stats["total_records"] += 1

                    # Count labels
                    label = record.get("label", "UNKNOWN")
                    if label in stats["labels"]:
                        stats["labels"][label] += 1

                    # Count verifiable
                    verifiable = record.get("verifiable", "UNKNOWN")
                    if verifiable in stats["verifiable"]:
                        stats["verifiable"][verifiable] += 1

                    # Store first record as sample
                    if stats["sample_record"] is None:
                        stats["sample_record"] = record

                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing line {line_num}: {e}")

        logger.info(f"Dataset statistics: {stats['total_records']} records")
        logger.info(f"  Labels: {stats['labels']}")
        logger.info(f"  Verifiable: {stats['verifiable']}")

        return stats

    def download_all(self) -> Dict[str, Path]:
        """Download all FEVER datasets.

        Returns:
            Dictionary mapping dataset name to file path
        """
        logger.info("Downloading all FEVER datasets...")

        results = {
            "dev": self.download_dev_set(),
            "test": self.download_test_set(),
        }

        logger.info("Successfully downloaded FEVER datasets")
        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download FEVER dataset for TruthGraph integration"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./data/fever"),
        help="Output directory for dataset (default: ./data/fever)"
    )
    parser.add_argument(
        "--dev-only",
        action="store_true",
        help="Download only dev set (recommended for testing)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate checksums after download"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show dataset statistics after download"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if files exist"
    )

    args = parser.parse_args()

    try:
        downloader = FEVERDatasetDownloader(
            output_dir=args.output_dir,
            validate=args.validate
        )

        if args.dev_only:
            logger.info("Downloading dev set only...")
            dev_path = downloader.download_dev_set(force=args.force)

            if args.info:
                stats = downloader.get_dataset_info(dev_path)
                print("\nDev Set Statistics:")
                print(json.dumps(stats, indent=2, default=str))
        else:
            logger.info("Downloading all available datasets...")
            datasets = downloader.download_all()

            if args.info:
                for name, path in datasets.items():
                    logger.info(f"\n{name.upper()} Set Statistics:")
                    stats = downloader.get_dataset_info(path)
                    print(json.dumps(stats, indent=2, default=str))

        logger.info(f"All datasets ready in {downloader.output_dir.absolute()}")
        return 0

    except Exception as e:
        logger.error(f"Failed to download FEVER dataset: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
