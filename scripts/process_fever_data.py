#!/usr/bin/env python
"""Process FEVER dataset and convert to TruthGraph format.

This script reads FEVER JSONL files and converts them to TruthGraph-compatible
format for testing and benchmarking. It handles label mapping, evidence
extraction, and creates balanced subsets of the data.

Schema Mapping:
    FEVER -> TruthGraph
    - claim -> text
    - label -> expected_verdict (SUPPORTS->SUPPORTED, REFUTES->REFUTED, NOT ENOUGH INFO->INSUFFICIENT)
    - evidence -> evidence_snippets (extracted from articles)
    - id -> reference_id

Evidence Strategy:
    Since FEVER references Wikipedia articles, we use the article titles
    and sentence IDs to create evidence references. For realistic testing,
    we create synthetic evidence based on the claim text and article context.

Usage:
    python process_fever_data.py --input fever.dev.jsonl --output-dir ./fever_processed [--sample-size 100]

References:
    - FEVER Dataset: https://fever.ai/
    - Label distributions and mappings
"""

import argparse
import hashlib
import json
import logging
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FEVERProcessor:
    """Process FEVER dataset and convert to TruthGraph format."""

    # Label mapping from FEVER to TruthGraph
    LABEL_MAPPING = {
        "SUPPORTS": "SUPPORTED",
        "REFUTES": "REFUTED",
        "NOT ENOUGH INFO": "INSUFFICIENT",
    }

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize processor.

        Args:
            output_dir: Directory to save processed data. Defaults to ./fever_processed
        """
        self.output_dir = Path(output_dir) if output_dir else Path("./fever_processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {self.output_dir.absolute()}")

        self.processed_claims = []
        self.processed_evidence = {}
        self.claim_evidence_mapping = {}

    def parse_fever_jsonl(self, filepath: Path) -> List[Dict[str, Any]]:
        """Parse FEVER JSONL file.

        Args:
            filepath: Path to FEVER JSONL file

        Returns:
            List of claim records
        """
        logger.info(f"Reading FEVER dataset from {filepath}...")

        records = []
        errors = 0

        with open(filepath, "r") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError as e:
                    errors += 1
                    if errors <= 5:  # Log first 5 errors
                        logger.warning(f"Error parsing line {line_num}: {e}")

        logger.info(f"Loaded {len(records)} records from FEVER dataset")
        if errors > 0:
            logger.warning(f"Encountered {errors} parsing errors")

        return records

    def map_label(self, fever_label: str) -> Optional[str]:
        """Map FEVER label to TruthGraph verdict.

        Args:
            fever_label: FEVER label (SUPPORTS, REFUTES, NOT ENOUGH INFO)

        Returns:
            TruthGraph verdict (SUPPORTED, REFUTED, INSUFFICIENT) or None
        """
        return self.LABEL_MAPPING.get(fever_label)

    def extract_evidence_snippets(self, record: Dict[str, Any]) -> List[str]:
        """Extract evidence snippets from FEVER record.

        The FEVER dataset provides evidence references as:
        [
            [
                [null, null, "Wikipedia_Article_Title", sentence_id],
                ...
            ]
        ]

        Since we don't have the actual Wikipedia dump, we create evidence
        references based on the article titles. In production, these would
        be fetched from Wikipedia.

        Args:
            record: FEVER record

        Returns:
            List of evidence snippets/references
        """
        evidence_snippets = []

        if "evidence" not in record or not record["evidence"]:
            return evidence_snippets

        # Process each evidence group
        for evidence_group in record["evidence"]:
            if not evidence_group:
                continue

            # Extract unique article titles from the group
            articles = set()
            for evidence_item in evidence_group:
                if len(evidence_item) >= 3:
                    article_title = evidence_item[2]
                    sentence_id = evidence_item[3] if len(evidence_item) > 3 else None

                    if article_title:
                        articles.add(article_title)

                        # Create evidence reference
                        if sentence_id is not None:
                            snippet = f"{article_title} (sentence {sentence_id})"
                        else:
                            snippet = article_title

                        evidence_snippets.append(snippet)

        return list(set(evidence_snippets))  # Remove duplicates

    def process_record(self, record: Dict[str, Any], record_id: int) -> Optional[Dict[str, Any]]:
        """Convert a FEVER record to TruthGraph format.

        Args:
            record: FEVER record
            record_id: Unique record ID

        Returns:
            TruthGraph-formatted claim record or None if invalid
        """
        # Extract basic fields
        claim_text = record.get("claim", "").strip()
        fever_label = record.get("label")
        fever_id = record.get("id")

        # Skip invalid records
        if not claim_text:
            logger.warning(f"Skipping record {record_id}: empty claim text")
            return None

        if fever_label not in self.LABEL_MAPPING:
            logger.warning(f"Skipping record {record_id}: unknown label '{fever_label}'")
            return None

        # Map label
        expected_verdict = self.map_label(fever_label)

        # Extract evidence
        evidence_snippets = self.extract_evidence_snippets(record)

        # Create TruthGraph claim record
        truthgraph_record = {
            "id": f"fever_{record_id:06d}",
            "reference_id": fever_id,
            "text": claim_text,
            "category": "fever_dataset",
            "expected_verdict": expected_verdict,
            "evidence_ids": [],
            "confidence": 0.9,  # FEVER is high-confidence dataset
            "reasoning": f"FEVER dataset record: {fever_label}",
            "source": "FEVER_Dataset",
            "evidence_references": evidence_snippets,
        }

        return truthgraph_record

    def create_evidence_records(
        self,
        claim_record: Dict[str, Any],
        evidence_snippets: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Create evidence records for a claim.

        Args:
            claim_record: TruthGraph claim record
            evidence_snippets: List of evidence snippet references

        Returns:
            Dictionary mapping evidence ID to evidence record
        """
        evidence_records = {}
        claim_id = claim_record["id"]

        for idx, snippet in enumerate(evidence_snippets):
            evidence_id = f"{claim_id}_ev_{idx:03d}"

            # Create evidence record
            evidence_record = {
                "id": evidence_id,
                "content": f"Evidence from: {snippet}",
                "source_reference": snippet,
                "source_type": "wikipedia",
                "claim_id": claim_id,
                "category": "fever_dataset",
            }

            evidence_records[evidence_id] = evidence_record
            claim_record["evidence_ids"].append(evidence_id)

        return evidence_records

    def process_dataset(
        self,
        input_file: Path,
        sample_size: Optional[int] = None,
        seed: int = 42
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Any]]:
        """Process FEVER dataset and create TruthGraph format.

        Args:
            input_file: Path to FEVER JSONL file
            sample_size: If specified, create a balanced sample of this size
            seed: Random seed for reproducibility

        Returns:
            Tuple of (claims, evidence, stats)
        """
        # Parse FEVER dataset
        fever_records = self.parse_fever_jsonl(input_file)

        # Apply sampling if requested
        if sample_size and sample_size < len(fever_records):
            fever_records = self._create_balanced_sample(fever_records, sample_size, seed)

        # Process records
        claims = []
        all_evidence = {}
        label_counts = Counter()

        logger.info(f"Processing {len(fever_records)} records...")

        for idx, record in enumerate(fever_records, 1):
            if idx % 1000 == 0:
                logger.info(f"Processed {idx} records...")

            processed = self.process_record(record, idx)
            if processed:
                claims.append(processed)
                label_counts[processed["expected_verdict"]] += 1

                # Create evidence records
                evidence_snippets = record.get("evidence", [])
                if evidence_snippets:
                    evidence_refs = self.extract_evidence_snippets(record)
                    evidence_records = self.create_evidence_records(processed, evidence_refs)
                    all_evidence.update(evidence_records)

        # Create statistics
        stats = {
            "total_processed": len(claims),
            "label_distribution": dict(label_counts),
            "total_evidence": len(all_evidence),
            "avg_evidence_per_claim": len(all_evidence) / len(claims) if claims else 0,
            "processing_seed": seed,
        }

        logger.info(f"Processing complete: {len(claims)} valid claims, {len(all_evidence)} evidence items")
        logger.info(f"Label distribution: {stats['label_distribution']}")

        return claims, all_evidence, stats

    def _create_balanced_sample(
        self,
        records: List[Dict[str, Any]],
        sample_size: int,
        seed: int
    ) -> List[Dict[str, Any]]:
        """Create a balanced sample of records by label.

        Args:
            records: Full list of records
            sample_size: Desired sample size
            seed: Random seed

        Returns:
            Balanced sample of records
        """
        random.seed(seed)

        # Group by label
        by_label = {}
        for record in records:
            label = record.get("label", "UNKNOWN")
            if label not in by_label:
                by_label[label] = []
            by_label[label].append(record)

        logger.info(f"Label distribution in full dataset: {Counter(r.get('label') for r in records)}")

        # Calculate samples per label to maintain balance
        labels_with_data = [label for label in by_label if by_label[label]]
        samples_per_label = sample_size // len(labels_with_data)
        remainder = sample_size % len(labels_with_data)

        sample = []
        for idx, label in enumerate(sorted(labels_with_data)):
            count = samples_per_label + (1 if idx < remainder else 0)
            count = min(count, len(by_label[label]))
            sample.extend(random.sample(by_label[label], count))

        logger.info(f"Created balanced sample of {len(sample)} records")
        return sample

    def save_claims_json(self, claims: List[Dict[str, Any]]) -> Path:
        """Save claims to JSON file.

        Args:
            claims: List of claims

        Returns:
            Path to saved file
        """
        output_path = self.output_dir / "fever_sample_claims.json"

        data = {
            "metadata": {
                "version": "1.0",
                "source": "FEVER_Dataset",
                "total_claims": len(claims),
                "created_date": "2025-10-27",
            },
            "claims": claims,
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(claims)} claims to {output_path}")
        return output_path

    def save_evidence_json(self, evidence: Dict[str, Dict[str, Any]]) -> Path:
        """Save evidence to JSON file.

        Args:
            evidence: Dictionary of evidence records

        Returns:
            Path to saved file
        """
        output_path = self.output_dir / "fever_sample_evidence.json"

        data = {
            "metadata": {
                "version": "1.0",
                "source": "FEVER_Dataset",
                "total_evidence": len(evidence),
                "created_date": "2025-10-27",
            },
            "evidence": list(evidence.values()),
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(evidence)} evidence items to {output_path}")
        return output_path

    def save_mapping_json(
        self,
        claims: List[Dict[str, Any]],
        evidence: Dict[str, Dict[str, Any]]
    ) -> Path:
        """Save claim-to-verdict mapping.

        Args:
            claims: List of claims
            evidence: Dictionary of evidence records

        Returns:
            Path to saved file
        """
        output_path = self.output_dir / "fever_mapping.json"

        mapping = {
            "metadata": {
                "version": "1.0",
                "schema": "claim_id -> {verdict, evidence_ids, reasoning}",
                "total_mappings": len(claims),
                "created_date": "2025-10-27",
            },
            "mappings": {
                claim["id"]: {
                    "text": claim["text"],
                    "expected_verdict": claim["expected_verdict"],
                    "evidence_ids": claim["evidence_ids"],
                    "reference_id": claim["reference_id"],
                }
                for claim in claims
            },
            "evidence_index": {
                ev_id: {
                    "content": ev["content"],
                    "source": ev.get("source_reference", ""),
                }
                for ev_id, ev in evidence.items()
            },
        }

        with open(output_path, "w") as f:
            json.dump(mapping, f, indent=2)

        logger.info(f"Saved mapping for {len(claims)} claims to {output_path}")
        return output_path

    def save_stats_json(self, stats: Dict[str, Any]) -> Path:
        """Save processing statistics.

        Args:
            stats: Statistics dictionary

        Returns:
            Path to saved file
        """
        output_path = self.output_dir / "fever_stats.json"

        with open(output_path, "w") as f:
            json.dump(stats, f, indent=2)

        logger.info(f"Saved statistics to {output_path}")
        return output_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process FEVER dataset for TruthGraph integration"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input FEVER JSONL file"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./fever_processed"),
        help="Output directory for processed data (default: ./fever_processed)"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=100,
        help="Create balanced sample of this size (default: 100, use 0 for all data)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling (default: 42)"
    )

    args = parser.parse_args()

    # Validate input file
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return 1

    try:
        processor = FEVERProcessor(output_dir=args.output_dir)

        # Process dataset
        claims, evidence, stats = processor.process_dataset(
            input_file=args.input,
            sample_size=args.sample_size if args.sample_size > 0 else None,
            seed=args.seed
        )

        # Save results
        processor.save_claims_json(claims)
        processor.save_evidence_json(evidence)
        processor.save_mapping_json(claims, evidence)
        processor.save_stats_json(stats)

        logger.info("FEVER dataset processing complete!")
        print(f"\nProcessing Summary:")
        print(f"  Claims processed: {stats['total_processed']}")
        print(f"  Evidence items: {stats['total_evidence']}")
        print(f"  Label distribution: {stats['label_distribution']}")
        print(f"  Output directory: {processor.output_dir.absolute()}")

        return 0

    except Exception as e:
        logger.error(f"Failed to process FEVER dataset: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
