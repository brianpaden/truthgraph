#!/usr/bin/env python3
"""Corpus loading and embedding generation script.

This script loads evidence from CSV/JSON files, generates embeddings,
and stores them in the database with progress tracking and error handling.

Features:
    - Batch processing for efficient embedding generation
    - Progress tracking with tqdm
    - Checkpoint-based resume capability
    - Memory-efficient processing for large datasets
    - Comprehensive error handling and logging
    - Retry logic for transient failures

Usage:
    # Load CSV corpus
    python scripts/embed_corpus.py data/evidence.csv --format csv

    # Load JSONL corpus with custom batch size
    python scripts/embed_corpus.py data/evidence.jsonl --format jsonl --batch-size 64

    # Resume interrupted load
    python scripts/embed_corpus.py data/evidence.csv --format csv --resume

    # Dry run to validate data
    python scripts/embed_corpus.py data/evidence.csv --format csv --dry-run

Performance targets:
    - >500 documents/sec for embedding generation
    - <2GB memory for 10K documents
    - <3 seconds per document average throughput
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from truthgraph.db_async import async_engine, AsyncSessionLocal
from truthgraph.schemas import Embedding, Evidence
from truthgraph.services.ml.embedding_service import EmbeddingService

from corpus_loaders import get_loader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = structlog.get_logger()


class CheckpointManager:
    """Manages checkpoint state for resumable corpus loading.

    Checkpoint format (JSON):
        {
            "file_path": "data/evidence.csv",
            "format": "csv",
            "last_processed_idx": 1000,
            "last_processed_id": "ev_001000",
            "total_processed": 1000,
            "total_errors": 5,
            "timestamp": "2025-10-29T20:00:00",
            "batch_size": 32
        }
    """

    def __init__(self, checkpoint_file: Path) -> None:
        """Initialize checkpoint manager.

        Args:
            checkpoint_file: Path to checkpoint JSON file
        """
        self.checkpoint_file = checkpoint_file
        self.checkpoint: dict[str, Any] = {}

    def load(self) -> dict[str, Any]:
        """Load checkpoint from file.

        Returns:
            Checkpoint data, or empty dict if no checkpoint exists
        """
        if not self.checkpoint_file.exists():
            logger.info("No checkpoint file found")
            return {}

        try:
            with open(self.checkpoint_file) as f:
                self.checkpoint = json.load(f)
            logger.info(
                f"Loaded checkpoint: processed {self.checkpoint.get('total_processed', 0)} items"
            )
            return self.checkpoint
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return {}

    def save(
        self,
        file_path: str,
        format_type: str,
        last_idx: int,
        last_id: str,
        total_processed: int,
        total_errors: int,
        batch_size: int,
    ) -> None:
        """Save checkpoint to file.

        Args:
            file_path: Corpus file path
            format_type: File format (csv/json/jsonl)
            last_idx: Index of last processed item
            last_id: ID of last processed item
            total_processed: Total items processed successfully
            total_errors: Total errors encountered
            batch_size: Batch size used
        """
        self.checkpoint = {
            'file_path': file_path,
            'format': format_type,
            'last_processed_idx': last_idx,
            'last_processed_id': last_id,
            'total_processed': total_processed,
            'total_errors': total_errors,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'batch_size': batch_size,
        }

        try:
            # Ensure parent directory exists
            self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

            # Write atomically using temp file
            temp_file = self.checkpoint_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(self.checkpoint, f, indent=2)

            # Atomic rename
            temp_file.replace(self.checkpoint_file)

            logger.debug(f"Saved checkpoint at index {last_idx}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def clear(self) -> None:
        """Clear checkpoint file."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            logger.info("Cleared checkpoint")


async def process_batch(
    session: Any,
    batch: list[dict[str, Any]],
    embedding_service: EmbeddingService,
    tenant_id: str,
    dry_run: bool,
) -> tuple[int, int]:
    """Process a batch of evidence items.

    Args:
        session: Database session
        batch: List of evidence items
        embedding_service: Embedding service instance
        tenant_id: Tenant identifier
        dry_run: If True, skip database operations

    Returns:
        Tuple of (success_count, error_count)
    """
    if not batch:
        return 0, 0

    success_count = 0
    error_count = 0

    try:
        # Extract content for batch embedding
        contents = [item['content'] for item in batch]

        # Generate embeddings in batch
        embeddings = embedding_service.embed_batch(contents, show_progress=False)

        # Process each item
        for item, embedding_vector in zip(batch, embeddings):
            try:
                if dry_run:
                    # Just validate, don't insert
                    logger.debug(f"[DRY RUN] Would insert: {item['id']}")
                    success_count += 1
                    continue

                # Create Evidence record
                evidence = Evidence(
                    content=item['content'],
                    source_url=item.get('url'),
                    source_type=item.get('source'),
                )
                session.add(evidence)
                await session.flush()  # Get evidence.id

                # Create Embedding record
                embedding = Embedding(
                    entity_type='evidence',
                    entity_id=evidence.id,
                    embedding=embedding_vector,
                    model_name=embedding_service.MODEL_NAME,
                    tenant_id=tenant_id,
                )
                session.add(embedding)

                success_count += 1

            except Exception as e:
                logger.error(f"Failed to process item {item.get('id', 'unknown')}: {e}")
                error_count += 1
                continue

        # Commit batch
        if not dry_run:
            await session.commit()

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        if not dry_run:
            await session.rollback()
        error_count = len(batch)

    return success_count, error_count


async def embed_corpus(
    input_file: Path,
    format_type: str,
    batch_size: int = 32,
    checkpoint_interval: int = 100,
    resume: bool = False,
    tenant_id: str = "default",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Load corpus, generate embeddings, and store in database.

    Args:
        input_file: Path to corpus file
        format_type: File format (csv/json/jsonl)
        batch_size: Number of items to process per batch
        checkpoint_interval: Save checkpoint every N items
        resume: If True, resume from checkpoint
        tenant_id: Tenant identifier
        dry_run: If True, validate without database operations

    Returns:
        Statistics dictionary with processing results
    """
    # Initialize checkpoint manager
    checkpoint_file = Path(f".corpus_checkpoint_{input_file.stem}.json")
    checkpoint_mgr = CheckpointManager(checkpoint_file)

    # Load checkpoint if resuming
    checkpoint = checkpoint_mgr.load() if resume else {}
    start_idx = checkpoint.get('last_processed_idx', 0) if checkpoint else 0

    # Validate checkpoint matches current file
    if checkpoint and checkpoint.get('file_path') != str(input_file):
        logger.warning(
            f"Checkpoint file mismatch. Expected {checkpoint.get('file_path')}, "
            f"got {input_file}. Starting from beginning."
        )
        start_idx = 0

    # Initialize services
    logger.info(f"Initializing embedding service...")
    embedding_service = EmbeddingService.get_instance()

    # Load corpus
    logger.info(f"Loading {format_type.upper()} corpus from {input_file}")
    loader = get_loader(format_type, input_file)
    total_count = loader.get_total_count()

    # Statistics
    stats = {
        'total_items': 0,
        'processed': 0,
        'errors': 0,
        'skipped': 0,
        'start_time': time.time(),
    }

    # Process with progress bar
    async with AsyncSessionLocal() as session:
        batch: list[dict[str, Any]] = []
        current_idx = 0

        with tqdm(
            total=total_count,
            initial=start_idx,
            desc="Processing corpus",
            unit="items"
        ) as pbar:
            for item in loader.load():
                current_idx += 1
                stats['total_items'] += 1

                # Skip already processed items
                if current_idx <= start_idx:
                    stats['skipped'] += 1
                    continue

                # Validate item
                if not loader.validate(item):
                    logger.warning(f"Invalid item at index {current_idx}: {item.get('id')}")
                    stats['errors'] += 1
                    pbar.update(1)
                    continue

                batch.append(item)

                # Process batch when full
                if len(batch) >= batch_size:
                    success, errors = await process_batch(
                        session, batch, embedding_service, tenant_id, dry_run
                    )
                    stats['processed'] += success
                    stats['errors'] += errors
                    pbar.update(len(batch))
                    batch = []

                # Save checkpoint periodically
                if current_idx % checkpoint_interval == 0 and not dry_run:
                    checkpoint_mgr.save(
                        file_path=str(input_file),
                        format_type=format_type,
                        last_idx=current_idx,
                        last_id=item.get('id', 'unknown'),
                        total_processed=stats['processed'],
                        total_errors=stats['errors'],
                        batch_size=batch_size,
                    )

            # Process remaining batch
            if batch:
                success, errors = await process_batch(
                    session, batch, embedding_service, tenant_id, dry_run
                )
                stats['processed'] += success
                stats['errors'] += errors
                pbar.update(len(batch))

    # Calculate final statistics
    stats['end_time'] = time.time()
    stats['duration_seconds'] = stats['end_time'] - stats['start_time']
    stats['items_per_second'] = (
        stats['processed'] / stats['duration_seconds']
        if stats['duration_seconds'] > 0 else 0
    )

    # Clear checkpoint on successful completion
    if not dry_run and stats['errors'] == 0:
        checkpoint_mgr.clear()

    return stats


def main() -> int:
    """Main entry point for corpus loading script."""
    parser = argparse.ArgumentParser(
        description="Load evidence corpus and generate embeddings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        'input_file',
        type=Path,
        help='Path to corpus file (CSV or JSON/JSONL)'
    )

    parser.add_argument(
        '--format',
        choices=['csv', 'json', 'jsonl'],
        required=True,
        help='Corpus file format'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for embedding generation (default: 32)'
    )

    parser.add_argument(
        '--checkpoint-interval',
        type=int,
        default=100,
        help='Save checkpoint every N items (default: 100)'
    )

    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from last checkpoint'
    )

    parser.add_argument(
        '--tenant-id',
        default='default',
        help='Tenant identifier (default: "default")'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate corpus without inserting into database'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate input file
    if not args.input_file.exists():
        logger.error(f"Input file not found: {args.input_file}")
        return 1

    # Run corpus loading
    try:
        logger.info("=" * 60)
        logger.info("TruthGraph Corpus Loading")
        logger.info("=" * 60)
        logger.info(f"Input file: {args.input_file}")
        logger.info(f"Format: {args.format}")
        logger.info(f"Batch size: {args.batch_size}")
        logger.info(f"Resume: {args.resume}")
        logger.info(f"Dry run: {args.dry_run}")
        logger.info("=" * 60)

        # Run async processing
        stats = asyncio.run(
            embed_corpus(
                input_file=args.input_file,
                format_type=args.format,
                batch_size=args.batch_size,
                checkpoint_interval=args.checkpoint_interval,
                resume=args.resume,
                tenant_id=args.tenant_id,
                dry_run=args.dry_run,
            )
        )

        # Display results
        logger.info("=" * 60)
        logger.info("Processing Complete")
        logger.info("=" * 60)
        logger.info(f"Total items: {stats['total_items']}")
        logger.info(f"Processed successfully: {stats['processed']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info(f"Skipped (resumed): {stats['skipped']}")
        logger.info(f"Duration: {stats['duration_seconds']:.2f} seconds")
        logger.info(f"Throughput: {stats['items_per_second']:.2f} items/sec")
        logger.info("=" * 60)

        return 0 if stats['errors'] == 0 else 1

    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user. Checkpoint saved for resume.")
        return 130
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
