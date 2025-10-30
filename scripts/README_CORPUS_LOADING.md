# Corpus Loading Guide

Production-ready script for loading evidence corpus into TruthGraph database with automatic embedding generation.

## Overview

The `embed_corpus.py` script provides a robust, memory-efficient solution for loading large evidence datasets and generating embeddings for semantic search.

**Key Features:**

- Multiple format support (CSV, JSON, JSONL)
- Batch embedding generation for high throughput
- Progress tracking with tqdm
- Checkpoint-based resume capability
- Memory-efficient processing for large datasets
- Comprehensive error handling and logging
- Dry-run validation mode

**Performance Targets:**

- Throughput: >500 documents/sec
- Memory: <2GB for 10K documents
- Average: <3 seconds per document

## Quick Start

### Basic Usage

```bash
# Load CSV corpus
python scripts/embed_corpus.py data/evidence.csv --format csv

# Load JSON corpus
python scripts/embed_corpus.py data/evidence.json --format json

# Load JSONL corpus (recommended for large datasets)
python scripts/embed_corpus.py data/evidence.jsonl --format jsonl
```

### With Custom Settings

```bash
# Use larger batch size for GPU
python scripts/embed_corpus.py data/evidence.csv --format csv --batch-size 128

# Resume interrupted load
python scripts/embed_corpus.py data/evidence.csv --format csv --resume

# Dry run to validate data
python scripts/embed_corpus.py data/evidence.csv --format csv --dry-run
```

## Input Format Specifications

### CSV Format

**Required Columns:**

- `content` or `text`: Evidence text content (required)

**Optional Columns:**

- `id`: Unique identifier (auto-generated if missing)
- `source` or `source_name`: Source name
- `url` or `source_url`: Source URL

**Example:**

```csv
id,content,source,url
ev_001,"The Earth orbits the Sun at 93 million miles.",Wikipedia,https://en.wikipedia.org/wiki/Earth
ev_002,"Water boils at 100°C at sea level.",Chemistry,https://example.com/chemistry
```

**Flexible Column Names:**

The loader supports various column name conventions:

- Content: `content`, `text`, `evidence`, `evidence_text`
- ID: `id`, `evidence_id`, `doc_id`, `identifier`
- Source: `source`, `source_name`, `origin`
- URL: `url`, `source_url`, `link`, `uri`

### JSON Array Format

Array of evidence objects.

**Example:**

```json
[
  {
    "id": "json_001",
    "content": "Evidence text content here...",
    "source": "Wikipedia",
    "url": "https://example.com"
  },
  {
    "id": "json_002",
    "content": "More evidence content...",
    "source": "Reuters"
  }
]
```

**Flexible Field Names:**

Similar to CSV, supports flexible naming:

- Content: `content`, `text`, `evidence`, `body`
- ID: `id`, `evidence_id`, `doc_id`, `_id`
- Source: `source`, `source_name`, `publisher`
- URL: `url`, `source_url`, `link`, `href`

### JSONL Format (Recommended for Large Datasets)

Newline-delimited JSON - one JSON object per line. More memory-efficient than JSON arrays.

**Example:**

```jsonl
{"id": "jsonl_001", "content": "First evidence item...", "source": "Nature"}
{"id": "jsonl_002", "content": "Second evidence item...", "source": "Science"}
{"id": "jsonl_003", "content": "Third evidence item...", "source": "IEEE"}
```

**Advantages:**

- Memory-efficient line-by-line processing
- Easy to append new records
- Simple to process in parallel
- Resilient to partial failures

## Command Line Options

### Required Arguments

- `input_file`: Path to corpus file (CSV, JSON, or JSONL)
- `--format`: File format (`csv`, `json`, or `jsonl`)

### Optional Arguments

```
--batch-size BATCH_SIZE
    Number of items to process per batch (default: 32)
    Recommended: 32 for CPU, 128+ for GPU

--checkpoint-interval INTERVAL
    Save checkpoint every N items (default: 100)
    Lower values = more frequent saves, slower performance

--resume
    Resume from last checkpoint
    Automatically skips already-processed items

--tenant-id TENANT_ID
    Tenant identifier for multi-tenancy (default: "default")

--dry-run
    Validate corpus without inserting into database
    Useful for testing file format and content

--verbose
    Enable verbose logging for debugging
```

## Resume Capability

The script automatically saves checkpoints during processing. If interrupted (Ctrl+C, crash, etc.), resume with:

```bash
python scripts/embed_corpus.py data/evidence.csv --format csv --resume
```

**Checkpoint Format:**

Checkpoints are saved in `.corpus_checkpoint_<filename>.json`:

```json
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
```

**Checkpoint Management:**

- Saved automatically every N items (configurable)
- Atomic writes prevent corruption
- Cleared automatically on successful completion
- Manual cleanup: Delete `.corpus_checkpoint_*.json` files

## Performance Tuning

### Batch Size Optimization

**CPU (Default: 32):**

```bash
python scripts/embed_corpus.py data/corpus.csv --format csv --batch-size 32
```

**GPU (Recommended: 128-256):**

```bash
python scripts/embed_corpus.py data/corpus.csv --format csv --batch-size 128
```

**Memory-Constrained (Use: 8-16):**

```bash
python scripts/embed_corpus.py data/corpus.csv --format csv --batch-size 8
```

### Format Selection

**CSV:**

- Good for: Spreadsheet data, structured datasets
- Memory: Moderate (line-by-line processing)
- Performance: Good

**JSON Array:**

- Good for: Small-to-medium datasets (<10K items)
- Memory: High (loads entire array)
- Performance: Good for small files

**JSONL (Recommended):**

- Good for: Large datasets (>10K items)
- Memory: Low (line-by-line processing)
- Performance: Excellent
- **Use this for production datasets**

### Database Considerations

**PostgreSQL Configuration:**

Increase work memory for better performance:

```sql
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
SELECT pg_reload_conf();
```

**Connection Pooling:**

The script uses async database connections with connection pooling (configured in `db_async.py`):

- Default pool size: 10
- Max overflow: 20

## Example Workflows

### Loading FEVER Dataset

```bash
# 1. Download and prepare FEVER data (using existing scripts)
python scripts/download_fever_dataset.py

# 2. Process into JSONL format
python scripts/process_fever_data.py --output data/fever_evidence.jsonl

# 3. Load into database with embeddings
python scripts/embed_corpus.py data/fever_evidence.jsonl --format jsonl --batch-size 64
```

### Incremental Loading

```bash
# Load initial corpus
python scripts/embed_corpus.py data/corpus_2025_01.csv --format csv

# Later, load additional data
python scripts/embed_corpus.py data/corpus_2025_02.csv --format csv
```

### Validation Before Loading

```bash
# Dry run to check format and content
python scripts/embed_corpus.py data/new_corpus.csv --format csv --dry-run --verbose

# If validation passes, load for real
python scripts/embed_corpus.py data/new_corpus.csv --format csv
```

### Large Dataset Loading

```bash
# For datasets >100K items
# Use JSONL format, larger batches, and GPU if available

python scripts/embed_corpus.py \
  data/large_corpus.jsonl \
  --format jsonl \
  --batch-size 128 \
  --checkpoint-interval 500
```

## Error Handling

### Common Errors

**1. Missing Content Column**

```
ValueError: CSV must have a content/text column
```

**Solution:** Ensure CSV has a column named `content`, `text`, or similar.

**2. Invalid JSON**

```
ValueError: Invalid JSON format
```

**Solution:** Validate JSON with `python -m json.tool file.json`

**3. Database Connection Error**

```
sqlalchemy.exc.OperationalError
```

**Solution:** Check database is running and credentials in `.env` are correct.

**4. Out of Memory**

```
MemoryError
```

**Solution:** Reduce `--batch-size` or use JSONL format.

### Error Recovery

**Automatic Retry:**

The script handles transient errors within batches. Failed items are logged but don't stop processing.

**Manual Recovery:**

1. Check logs for error details
2. Fix data issues in source file
3. Resume with `--resume` flag
4. Script will skip already-processed items

## Monitoring Progress

### Progress Bar

The script displays real-time progress:

```
Processing corpus: 45%|████████      | 4500/10000 [02:15<02:45, 33.23items/s]
```

Shows:

- Percentage complete
- Items processed / total
- Time elapsed / remaining
- Items per second throughput

### Logging

**Standard Output:**

```
2025-10-29 20:00:00 - INFO - Loading CSV corpus from data/evidence.csv
2025-10-29 20:00:01 - INFO - Processing 1000 texts with batch_size=32
2025-10-29 20:00:05 - INFO - Saved checkpoint at index 100
```

**Verbose Mode:**

Enable with `--verbose` for detailed debugging:

```bash
python scripts/embed_corpus.py data/corpus.csv --format csv --verbose
```

## Sample Data

Sample corpus files are provided in `scripts/corpus_samples/`:

- `sample_evidence.csv` - 50 scientific facts in CSV format
- `sample_evidence.json` - 20 educational items in JSON format
- `sample_evidence.jsonl` - 15 knowledge items in JSONL format

**Test with samples:**

```bash
# Test CSV loader
python scripts/embed_corpus.py scripts/corpus_samples/sample_evidence.csv --format csv --dry-run

# Test JSON loader
python scripts/embed_corpus.py scripts/corpus_samples/sample_evidence.json --format json --dry-run

# Test JSONL loader
python scripts/embed_corpus.py scripts/corpus_samples/sample_evidence.jsonl --format jsonl --dry-run
```

## Architecture

### Component Overview

```
scripts/
├── embed_corpus.py              # Main script
├── corpus_loaders/
│   ├── __init__.py             # Loader factory
│   ├── base_loader.py          # Abstract base class
│   ├── csv_loader.py           # CSV implementation
│   └── json_loader.py          # JSON/JSONL implementation
└── corpus_samples/             # Sample data
```

### Processing Pipeline

1. **Load Corpus**: Read and parse input file
2. **Validate**: Check required fields
3. **Batch**: Group items for efficient processing
4. **Embed**: Generate embeddings via EmbeddingService
5. **Store**: Insert Evidence and Embedding records
6. **Checkpoint**: Save progress periodically
7. **Commit**: Atomic batch commits

### Database Schema

**Evidence Table:**

```sql
CREATE TABLE evidence (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    source_url VARCHAR,
    source_type VARCHAR(50),
    created_at TIMESTAMP
);
```

**Embeddings Table:**

```sql
CREATE TABLE embeddings (
    id UUID PRIMARY KEY,
    entity_type VARCHAR(20),  -- 'evidence'
    entity_id UUID,           -- evidence.id
    embedding VECTOR(1536),   -- or VECTOR(384) for MiniLM
    model_name VARCHAR(100),
    tenant_id VARCHAR(255),
    created_at TIMESTAMP
);
```

## Testing

### Unit Tests

Run corpus loader tests:

```bash
# All tests
pytest tests/scripts/test_corpus_loading.py -v

# Specific test class
pytest tests/scripts/test_corpus_loading.py::TestCSVCorpusLoader -v

# Specific test
pytest tests/scripts/test_corpus_loading.py::TestCSVCorpusLoader::test_basic_csv_loading -v
```

### Integration Testing

Test with sample data:

```bash
# Test CSV loading (dry run)
python scripts/embed_corpus.py scripts/corpus_samples/sample_evidence.csv --format csv --dry-run

# Test actual loading (requires database)
python scripts/embed_corpus.py scripts/corpus_samples/sample_evidence.csv --format csv --batch-size 10
```

## Troubleshooting

### Performance Issues

**Slow Embedding Generation:**

- Check if GPU is being used: Look for "CUDA available" in logs
- Increase batch size for GPU: `--batch-size 128`
- Verify embedding service is using singleton pattern (only one model load)

**Database Bottleneck:**

- Increase batch size to reduce commit frequency
- Check PostgreSQL connection pool settings
- Monitor database CPU/memory usage

**Memory Usage:**

- Use JSONL format instead of JSON array
- Reduce batch size
- Increase checkpoint interval to reduce I/O

### Data Quality Issues

**Validation Failures:**

Enable verbose logging to see which items fail:

```bash
python scripts/embed_corpus.py data/corpus.csv --format csv --verbose
```

**Encoding Issues:**

Ensure files are UTF-8 encoded:

```bash
file -i data/corpus.csv
# Should show: charset=utf-8
```

Convert if needed:

```bash
iconv -f ISO-8859-1 -t UTF-8 corpus.csv > corpus_utf8.csv
```

## Advanced Usage

### Custom Tenant IDs

For multi-tenant deployments:

```bash
python scripts/embed_corpus.py data/org1_data.csv --format csv --tenant-id org1
python scripts/embed_corpus.py data/org2_data.json --format json --tenant-id org2
```

### Parallel Loading

Load multiple files in parallel (separate processes):

```bash
# Terminal 1
python scripts/embed_corpus.py data/corpus_part1.jsonl --format jsonl --tenant-id part1 &

# Terminal 2
python scripts/embed_corpus.py data/corpus_part2.jsonl --format jsonl --tenant-id part2 &
```

Note: Ensure different checkpoint files by using different file names.

### Integration with Existing Scripts

Load FEVER dataset after processing:

```bash
# Process FEVER data
python scripts/process_fever_data.py

# Load with embeddings
python scripts/embed_corpus.py data/fever_evidence_processed.jsonl --format jsonl
```

## Best Practices

1. **Always validate first**: Use `--dry-run` before loading large datasets
2. **Use JSONL for large datasets**: Better memory efficiency than JSON arrays
3. **Enable checkpointing**: Use reasonable checkpoint intervals (100-500 items)
4. **Monitor first batch**: Watch the first batch to estimate total time
5. **Tune batch size**: Start with defaults, then optimize for your hardware
6. **Use GPU when available**: 4-10x faster embedding generation
7. **Plan for failures**: Always use `--resume` for large loads
8. **Validate data quality**: Check sample items before bulk loading

## Performance Benchmarks

**Typical Performance (CPU):**

- Small batches (8): ~200 items/sec
- Medium batches (32): ~500 items/sec
- Large batches (64): ~600 items/sec

**Typical Performance (GPU):**

- Small batches (32): ~1,000 items/sec
- Medium batches (128): ~2,500 items/sec
- Large batches (256): ~3,500 items/sec

**Memory Usage:**

- CSV/JSONL: ~100MB baseline + (batch_size * 50KB)
- JSON array: ~100MB + (total_items * 10KB)

## Support and Contributing

For issues or questions:

1. Check this documentation
2. Review test cases in `tests/scripts/test_corpus_loading.py`
3. Check sample data in `scripts/corpus_samples/`
4. Enable verbose logging for debugging

## License

Apache 2.0 - See LICENSE file for details.
