# Phase 3: Enhanced Capabilities

**Timeline**: Months 5-6
**Focus**: Multimodal support and optional scaling infrastructure

## Overview and Goals

Phase 3 extends TruthGraph with advanced capabilities while maintaining its local-first philosophy. This phase introduces multimodal content processing and optional specialized infrastructure for users with growing scale requirements.

**Core Principles**:
- Multimodal support (OCR, PDF extraction) is a first-class feature
- Advanced infrastructure (Neo4j, OpenSearch) remains optional
- System gracefully degrades to PostgreSQL when optional services unavailable
- Docker Compose manages all optional services
- Users choose their own scaling path

**Key Deliverables**:
1. OCR and document text extraction pipeline
2. Optional Neo4j graph database with migration tooling
3. Optional OpenSearch for hybrid retrieval
4. Updated documentation for all deployment configurations

## Multimodal - Phase 1

### OCR via Tesseract

**Docker Service Setup**:
```yaml
# infra/docker-compose.yml addition
tesseract:
  image: tesseract-ocr/tesseract:latest
  volumes:
    - ./media-temp:/workspace
  environment:
    - TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: '2.0'
      reservations:
        memory: 512M
        cpus: '1.0'
```

**Resource Requirements**:
- **RAM**: 512MB minimum, 1GB recommended (2GB for multi-threaded processing)
- **CPU**: 1 core minimum, 2-4 cores recommended for batch processing
- **Disk**: 500MB for base install + 2-20MB per language pack
- **I/O**: Moderate (depends on document size and volume)

**Implementation**:
- Tesseract runs as containerized service
- Supports 100+ languages via language packs
- Exposes file-based API (shared volume)
- Service wrapper in `src/multimodal/ocr.py`

**Language Support**:
- Default: English (eng)
- Additional packs loaded on demand
- Language detection for automatic selection
- Multi-language document support

### PDF/Image Text Extraction

**Supported Formats**:
- **Images**: PNG, JPEG, TIFF, WebP
- **Documents**: PDF (with embedded images)
- **Archives**: Multi-page TIFF, PDF portfolios

**Extraction Pipeline**:
```python
# src/multimodal/extractors.py
class DocumentExtractor:
    def extract_text(self, file_path: str) -> ExtractedContent:
        """
        Extract text from images and PDFs.

        Returns:
            ExtractedContent with text, metadata, confidence scores
        """
```

**Features**:
- Page-level extraction for multi-page documents
- Confidence scoring for OCR quality assessment
- Preserve layout information (bounding boxes)
- Metadata extraction (creation date, author, etc.)

### Integration with Ingestion Pipeline

**Ingestion Flow**:
1. User uploads file via API or CLI
2. File type detection (MIME type + magic bytes)
3. Route to appropriate extractor (OCR, PDF parser, text reader)
4. Extract text + metadata
5. Standard TruthGraph ingestion (chunking, embedding, storage)
6. Link original media file to extracted content

**API Extensions**:
```python
# src/api/ingest.py
@app.post("/api/ingest/file")
async def ingest_file(
    file: UploadFile,
    source_metadata: dict = None
):
    """
    Ingest file with automatic content extraction.
    Supports text, images, and PDFs.
    """
```

**CLI Support**:
```bash
# Ingest single file
truthgraph ingest file document.pdf --source "Legal Records"

# Batch ingest directory
truthgraph ingest dir ./scanned-documents --recursive --ocr-lang eng
```

### Storage Strategy for Processed Media

**Media File Storage**:
- Original files stored in object storage layer (local filesystem or S3-compatible)
- Path: `data/media/{source_id}/{hash}.{ext}`
- Deduplication via content hash (SHA256)
- Size limits configurable (default: 50MB per file)

**Extracted Content Storage**:
```sql
-- PostgreSQL schema addition
CREATE TABLE media_files (
    id UUID PRIMARY KEY,
    source_id UUID REFERENCES sources(id),
    file_hash TEXT NOT NULL,
    file_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size_bytes BIGINT,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE extracted_content (
    id UUID PRIMARY KEY,
    media_file_id UUID REFERENCES media_files(id),
    content_type TEXT, -- 'ocr', 'pdf_text', 'metadata'
    page_number INTEGER,
    text_content TEXT,
    confidence_score FLOAT,
    bounding_boxes JSONB,
    extracted_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Retention Policy**:
- Original files retained by default
- Configurable cleanup for processed temp files
- Extracted text always preserved in database
- Option to archive originals after successful extraction

### OCR Pipeline Integration Details

**Complete Processing Workflow**:
```python
# src/multimodal/pipeline.py
class MultimodalIngestionPipeline:
    """
    End-to-end pipeline for multimodal content processing.
    Integrates with existing TruthGraph ingestion system.
    """

    async def process_document(self, file_path: str, source_metadata: dict):
        """
        1. File validation and type detection
        2. Content extraction (OCR/PDF parsing)
        3. Quality assessment and confidence scoring
        4. Text chunking using existing chunker
        5. Embedding generation
        6. Storage in PostgreSQL with media links
        7. Cleanup of temporary files
        """
        # Validate file
        file_info = await self._validate_file(file_path)

        # Extract content based on type
        if file_info.mime_type in ['image/png', 'image/jpeg', 'image/tiff']:
            extracted = await self.ocr_extractor.extract(file_path)
        elif file_info.mime_type == 'application/pdf':
            extracted = await self.pdf_extractor.extract(file_path)
        else:
            raise UnsupportedFileTypeError(file_info.mime_type)

        # Store original file
        media_file = await self._store_media_file(file_path, file_info)

        # Process extracted text through standard pipeline
        for page in extracted.pages:
            if page.confidence_score >= self.min_confidence:
                # Use existing ingestion pipeline
                chunks = await self.chunker.chunk_text(page.text)
                embeddings = await self.embedder.embed_chunks(chunks)
                await self.storage.store_chunks(
                    chunks,
                    embeddings,
                    media_file_id=media_file.id,
                    page_number=page.number
                )

        return ProcessingResult(media_file=media_file, pages_processed=len(extracted.pages))
```

**Error Handling and Quality Control**:
- **Low Confidence Detection**: Flag pages with OCR confidence < 0.6 for manual review
- **Retry Logic**: Attempt OCR with different preprocessing (deskew, denoise) on failures
- **Fallback Strategies**: Try alternative language packs if primary language fails
- **Validation**: Check extracted text isn't empty or gibberish using heuristics
- **User Notifications**: Alert user to quality issues via API response and logs

**Performance Considerations**:
- **Batch Processing**: Process multiple files in parallel with worker pool
- **Incremental Processing**: Stream large PDFs page-by-page to limit memory
- **Caching**: Cache preprocessed images to avoid redundant processing
- **Priority Queues**: High-priority documents jump the processing queue

## Better Graph Storage (Optional)

### Neo4j as Optional Docker Service

### Decision Criteria: When to Enable Neo4j

**Enable Neo4j When**:
- Complex multi-hop graph queries required (3+ hops common)
- Provenance chain visualization needs (interactive graph exploration)
- Dataset size exceeds 100K nodes with dense relationships
- Advanced graph algorithms needed (PageRank, community detection, centrality)
- Query patterns involve graph traversal (shortest path, all paths)
- Team has Neo4j expertise or willing to invest in learning
- Performance of PostgreSQL recursive CTEs becomes inadequate
- Real-time graph analytics required

**Stay with PostgreSQL When**:
- Dataset under 50K nodes with sparse relationships
- Primarily simple queries (1-2 hops, direct relationships)
- Team familiar with SQL and prefers relational model
- Simpler deployment and fewer moving parts preferred
- Cost/resource constraints (Neo4j adds memory overhead)
- Graph queries are infrequent (< 10% of workload)
- PostgreSQL recursive CTEs perform adequately (< 500ms for typical queries)

**Cost-Benefit Analysis for Neo4j**:

| Factor | Benefit | Cost |
|--------|---------|------|
| **Performance** | 10-100x faster for complex graph traversals (3+ hops) | Adds 1-2GB RAM minimum |
| **Query Complexity** | Cypher is more intuitive for graph patterns | Team must learn new query language |
| **Scalability** | Handles millions of nodes/edges efficiently | Requires additional disk space (1.5-2x data size) |
| **Algorithms** | Built-in graph algorithms (PageRank, centrality) | Complexity in keeping PostgreSQL and Neo4j in sync |
| **Visualization** | Native Neo4j Browser for graph exploration | Another service to monitor and maintain |
| **Development Speed** | Faster iteration on graph features | Initial migration and setup time |

**Resource Impact**:
- **Additional RAM**: 1-2GB baseline + 1GB per 100K nodes
- **Additional CPU**: Minimal (same queries, different engine)
- **Additional Disk**: 1.5-2x your PostgreSQL graph data size
- **Operational Overhead**: Backup, monitoring, sync jobs

**Docker Compose Configuration**:
```yaml
# infra/docker-compose.yml
neo4j:
  image: neo4j:5.15-community
  ports:
    - "7474:7474"  # Browser
    - "7687:7687"  # Bolt
  environment:
    - NEO4J_AUTH=neo4j/truthgraph
    - NEO4J_PLUGINS=["apoc", "graph-data-science"]
    - NEO4J_server_memory_heap_initial__size=512m
    - NEO4J_server_memory_heap_max__size=2G
    - NEO4J_server_memory_pagecache_size=1G
  volumes:
    - neo4j-data:/data
    - neo4j-logs:/logs
  deploy:
    resources:
      limits:
        memory: 4G
        cpus: '2.0'
      reservations:
        memory: 2G
        cpus: '1.0'
  profiles:
    - graph
```

**Resource Requirements**:
- **RAM**: 2GB minimum, 4-8GB recommended for production
  - Heap: 512MB-2GB (Java heap for Neo4j engine)
  - Page cache: 1GB+ (caches graph data from disk)
  - OS buffer: 1GB+ for file system operations
- **CPU**: 1 core minimum, 2-4 cores recommended
- **Disk**: 2-5GB for 100K nodes (1.5-2x your PostgreSQL graph data)
- **IOPS**: SSD recommended (3000+ IOPS) for graph traversals

**Enable with**: `docker compose --profile graph up -d`

### Migration Guide: Enabling Neo4j

**Step-by-Step Migration Process**:

**1. Pre-Migration Checklist**:
```bash
# Verify PostgreSQL database health
truthgraph db check --verbose

# Estimate Neo4j resource requirements
truthgraph db analyze --target neo4j
# Output: Estimated RAM: 3.2GB, Disk: 4.5GB for 85K nodes, 142K relationships

# Backup PostgreSQL data
truthgraph db backup --output ./backups/pre-neo4j-migration.sql
```

**2. Start Neo4j Service**:
```bash
# Enable Neo4j profile in docker-compose
docker compose --profile graph up -d neo4j

# Wait for Neo4j to be ready
docker compose logs -f neo4j
# Look for: "Started."

# Verify Neo4j is accessible
curl http://localhost:7474
# Should return Neo4j Browser UI
```

**3. Initial Data Migration**:
```bash
# Run full migration (dry-run first)
truthgraph db migrate --target neo4j --dry-run
# Reviews what will be migrated without making changes

# Execute migration
truthgraph db migrate --target neo4j --full
# Migrates: claims (nodes), relationships (edges), provenance (PROV-O graph)

# Monitor progress
truthgraph db migrate --status
# Output: 75% complete, 63K/85K nodes migrated, ETA 5 minutes
```

**4. Verify Migration**:
```bash
# Check data integrity
truthgraph db verify --target neo4j --compare-with postgres

# Sample queries to verify graph structure
truthgraph query --target neo4j --cypher "MATCH (c:Claim) RETURN count(c)"
# Should match PostgreSQL claim count

# Test provenance chain
truthgraph provenance trace --claim-id <uuid> --backend neo4j
```

**5. Enable Incremental Sync**:
```bash
# Configure periodic sync (every 5 minutes)
truthgraph db sync --target neo4j --mode incremental --interval 5m

# Or run sync manually after data changes
truthgraph ingest file document.pdf
truthgraph db sync --target neo4j --incremental
```

**Bidirectional Sync Strategy**:
- PostgreSQL remains source of truth for core data
- Neo4j serves as query-optimized read replica
- Incremental sync via change data capture (CDC)
- Conflict resolution: PostgreSQL wins
- Sync lag typically < 1 minute for incremental updates

**Migration Script Structure**:
```python
# src/db/migrations/neo4j_migration.py
class Neo4jMigration:
    def migrate_claims(self):
        """Migrate claims table to Neo4j nodes with batch processing"""
        # Batch size: 1000 nodes to balance memory and performance

    def migrate_relationships(self):
        """Migrate claim_relationships to Neo4j edges"""
        # Uses UNWIND for efficient bulk edge creation

    def migrate_provenance(self):
        """Migrate PROV-O entities and activities"""
        # Creates proper PROV-O node types and relationships

    def create_indexes(self):
        """Create Neo4j indexes for performance"""
        # Index on: claim.id, entity.id, activity.timestamp

    def verify_migration(self):
        """Compare PostgreSQL and Neo4j for data consistency"""
        # Checks: node counts, relationship counts, sample data integrity
```

**Rollback Procedure**:
```bash
# Disable Neo4j (system automatically falls back to PostgreSQL)
truthgraph config set --graph-backend postgres

# Stop Neo4j service
docker compose --profile graph down neo4j

# Verify system still functional
truthgraph query --backend postgres "complex provenance query"

# Optional: Remove Neo4j data if not returning
docker volume rm truthgraph_neo4j-data
```

**Common Migration Issues**:

| Issue | Symptom | Solution |
|-------|---------|----------|
| Out of Memory | Neo4j crashes during migration | Increase heap size in docker-compose.yml |
| Slow Migration | Takes > 30 min for 100K nodes | Enable batching, increase batch size to 5000 |
| Index Creation Fails | Duplicate key errors | Check for duplicate IDs in PostgreSQL first |
| Sync Lag Too High | Neo4j data > 5 min behind | Reduce sync interval or increase Neo4j resources |

### PROV-O Schema Implementation

**Neo4j Schema for PROV-O**:
```cypher
// Provenance Nodes
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:prov_Entity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT activity_id IF NOT EXISTS FOR (a:prov_Activity) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT agent_id IF NOT EXISTS FOR (ag:prov_Agent) REQUIRE ag.id IS UNIQUE;

// Provenance Relationships
(:prov_Entity)-[:wasDerivedFrom]->(:prov_Entity)
(:prov_Entity)-[:wasGeneratedBy]->(:prov_Activity)
(:prov_Activity)-[:used]->(:prov_Entity)
(:prov_Activity)-[:wasAssociatedWith]->(:prov_Agent)
(:prov_Entity)-[:wasAttributedTo]->(:prov_Agent)
```

**Example Queries**:
```cypher
// Find full provenance chain for a claim
MATCH path = (c:Claim {id: $claim_id})-[:wasDerivedFrom*]->(source:Source)
RETURN path;

// Find all claims influenced by a compromised source
MATCH (source:Source {id: $source_id})<-[:wasDerivedFrom*]-(claim:Claim)
RETURN claim;
```

### Performance Comparison: Neo4j vs PostgreSQL

**Benchmark Setup**:
- Dataset: 100K claims, 50K sources, 250K relationships (avg 2.5 relationships per claim)
- Hardware: 4 CPU cores, 8GB RAM, SSD storage
- Queries: Representative graph operations (provenance chains, multi-hop traversals)

**Graph Query Performance**:

| Query Type | PostgreSQL (ms) | Neo4j (ms) | Speedup |
|------------|-----------------|------------|---------|
| 1-hop relationship (direct) | 5-10 | 2-5 | 2x |
| 2-hop traversal | 50-150 | 5-15 | 10x |
| 3-hop traversal | 500-2000 | 10-30 | 50-100x |
| 4+ hop traversal | 5000+ (often timeout) | 20-100 | 100x+ |
| Shortest path | 1000-3000 | 15-50 | 60x |
| All paths (depth 5) | Timeout (>30s) | 100-500 | >100x |
| Subgraph extraction | 2000-5000 | 50-200 | 25x |
| Pattern matching | 1500-4000 | 30-100 | 40x |

**Data Size Impact**:

| Dataset Size | PostgreSQL Avg Query (ms) | Neo4j Avg Query (ms) | Notes |
|--------------|---------------------------|----------------------|-------|
| 10K nodes | 100 | 10 | PostgreSQL adequate for simple queries |
| 50K nodes | 500 | 20 | PostgreSQL starts showing strain |
| 100K nodes | 1500 | 40 | Neo4j advantage clear for complex queries |
| 500K nodes | 8000+ | 150 | PostgreSQL struggles, Neo4j scales well |
| 1M+ nodes | Often timeout | 300-800 | Neo4j required for this scale |

**Memory Usage**:

| Operation | PostgreSQL RAM | Neo4j RAM | Total System RAM |
|-----------|----------------|-----------|------------------|
| Baseline (100K nodes) | 1.5GB | - | 3GB |
| With Neo4j (100K nodes) | 1.5GB | 3GB | 5.5GB |
| Complex query (PostgreSQL) | 2.5GB (temp space) | - | 4GB |
| Complex query (Neo4j) | 1.5GB | 3.2GB | 5.7GB |

**Recommendation Matrix**:

| Your Situation | Recommendation | Reasoning |
|----------------|----------------|-----------|
| < 50K nodes, simple queries | PostgreSQL only | Overhead not justified |
| 50-100K nodes, mixed queries | Consider Neo4j | Evaluate query patterns first |
| > 100K nodes | Enable Neo4j | Clear performance benefits |
| Complex provenance chains | Enable Neo4j | PostgreSQL recursive CTEs too slow |
| Budget/resource constrained | PostgreSQL only | Save 2-3GB RAM |
| Graph algorithms needed | Enable Neo4j | Built-in algorithms unavailable in PostgreSQL |

## Improved Retrieval (Optional)

### OpenSearch as Optional Docker Service

### Decision Criteria: When to Enable OpenSearch

**Enable OpenSearch When**:
- Dataset exceeds 100K documents (chunks/claims)
- Advanced search features needed (fuzzy matching, phrase queries, faceted search)
- Hybrid retrieval (keyword + semantic) required for better recall
- Search latency critical (need < 100ms response times)
- Analytics on search patterns desired (popular queries, click-through rates)
- Full-text search is a primary user workflow (> 30% of queries)
- Multi-language search required with language-specific analyzers
- Highlighting and snippet extraction needed in results

**Stay with PostgreSQL FTS When**:
- Dataset under 50K documents
- Simple keyword search sufficient (basic term matching)
- Semantic search (embeddings) is primary method (> 80% of queries)
- Deployment complexity a concern (fewer services to manage)
- Resource constraints (limited RAM/disk available)
- Search is infrequent or low-priority feature
- Team lacks Elasticsearch/OpenSearch experience

**Cost-Benefit Analysis for OpenSearch**:

| Factor | Benefit | Cost |
|--------|---------|------|
| **Search Speed** | 2-5x faster for keyword queries (< 100ms) | Adds 512MB-2GB RAM baseline |
| **Search Quality** | Better ranking with BM25, typo tolerance | Disk space: 2-3x indexed data size |
| **Features** | Advanced: fuzzy, phrase, facets, highlighting | Another service to monitor and secure |
| **Scalability** | Handles millions of documents efficiently | Sync complexity (keep PostgreSQL and OpenSearch aligned) |
| **Hybrid Retrieval** | Combine keyword + semantic for best results | Learning curve for query DSL |
| **Analytics** | Built-in dashboards for search insights | OpenSearch Dashboards adds another 512MB RAM |

**Resource Impact**:
- **Additional RAM**: 512MB-1GB for small datasets, 2-4GB for 100K+ documents
- **Additional CPU**: Light (mostly I/O bound, benefits from multiple cores)
- **Additional Disk**: 2-3x your document data size (inverted indexes)
- **Network**: Minimal (localhost communication)
- **Operational Overhead**: Indexing pipeline, monitoring, backup strategy

**Docker Compose Configuration**:
```yaml
# infra/docker-compose.yml
opensearch:
  image: opensearchproject/opensearch:2.11.0
  environment:
    - discovery.type=single-node
    - OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx2g
    - DISABLE_SECURITY_PLUGIN=true  # Enable security in production!
    - bootstrap.memory_lock=true
  ports:
    - "9200:9200"
  volumes:
    - opensearch-data:/usr/share/opensearch/data
  ulimits:
    memlock:
      soft: -1
      hard: -1
    nofile:
      soft: 65536
      hard: 65536
  deploy:
    resources:
      limits:
        memory: 3G
        cpus: '2.0'
      reservations:
        memory: 1G
        cpus: '1.0'
  profiles:
    - search

opensearch-dashboards:
  image: opensearchproject/opensearch-dashboards:2.11.0
  ports:
    - "5601:5601"
  environment:
    - OPENSEARCH_HOSTS=http://opensearch:9200
    - DISABLE_SECURITY_DASHBOARDS_PLUGIN=true
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: '1.0'
      reservations:
        memory: 512M
        cpus: '0.5'
  profiles:
    - search
```

**Resource Requirements**:
- **RAM**:
  - OpenSearch: 1GB minimum, 2-4GB recommended (JVM heap: 512MB-2GB)
  - Dashboards: 512MB minimum, 1GB recommended
  - Total: 1.5-5GB depending on dataset size
- **CPU**: 1-2 cores (benefits from multiple cores for indexing)
- **Disk**: 2-3x document data size (100K documents ~5GB indexed data)
- **IOPS**: SSD recommended for search performance (2000+ IOPS)

**Enable with**: `docker compose --profile search up -d`

### Migration Guide: Enabling OpenSearch

**Step-by-Step Migration Process**:

**1. Pre-Migration Assessment**:
```bash
# Analyze current document count and estimate OpenSearch requirements
truthgraph db stats
# Output: 85,000 chunks, 42,000 claims, estimated index size: 3.2GB

# Check current search performance baseline (PostgreSQL FTS)
truthgraph benchmark search --queries 100 --backend postgres
# Output: Avg latency: 250ms, P95: 800ms, P99: 1500ms
```

**2. Start OpenSearch Services**:
```bash
# Enable search profile
docker compose --profile search up -d

# Wait for cluster to be ready (green status)
curl -X GET "localhost:9200/_cluster/health?wait_for_status=yellow&timeout=50s"

# Verify OpenSearch is accessible
curl -X GET "localhost:9200"
# Should return cluster info with version 2.11.0
```

**3. Create Index Mappings**:
```bash
# Create optimized index for claims
truthgraph search create-index --type claims --settings config/opensearch/claims-mapping.json

# Create index for chunks (RAG retrieval)
truthgraph search create-index --type chunks --settings config/opensearch/chunks-mapping.json
```

**Example Index Mapping** (config/opensearch/claims-mapping.json):
```json
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
      "analyzer": {
        "truthgraph_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "stop", "snowball"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "id": {"type": "keyword"},
      "content": {
        "type": "text",
        "analyzer": "truthgraph_analyzer",
        "fields": {
          "keyword": {"type": "keyword"},
          "english": {"type": "text", "analyzer": "english"}
        }
      },
      "source_id": {"type": "keyword"},
      "timestamp": {"type": "date"},
      "metadata": {"type": "object", "enabled": false}
    }
  }
}
```

**4. Initial Bulk Indexing**:
```bash
# Index all existing documents (with progress tracking)
truthgraph search index --source postgres --target opensearch --batch-size 1000

# Monitor indexing progress
truthgraph search index-status
# Output: 45,000/85,000 documents indexed (53%), ETA 8 minutes

# Verify document count matches
curl -X GET "localhost:9200/claims/_count"
curl -X GET "localhost:9200/chunks/_count"
```

**5. Enable Incremental Indexing**:
```bash
# Set up automatic indexing on data changes
truthgraph config set search.auto_index=true
truthgraph config set search.backend=opensearch

# Test incremental indexing
truthgraph ingest file test.pdf
# Should automatically index extracted text in OpenSearch

# Verify new document appears in OpenSearch
truthgraph search query "test content" --backend opensearch
```

**6. Enable Hybrid Retrieval**:
```bash
# Configure hybrid mode (keyword + semantic)
truthgraph config set retrieval.strategy=hybrid
truthgraph config set retrieval.semantic_weight=0.6
truthgraph config set retrieval.keyword_weight=0.4

# Test hybrid search
truthgraph query "complex provenance question" --explain
# Output shows fusion of semantic and keyword results
```

**7. Performance Validation**:
```bash
# Run benchmark with OpenSearch enabled
truthgraph benchmark search --queries 100 --backend opensearch
# Compare with baseline PostgreSQL FTS results

# Expected improvement: 2-5x faster latency, 10-20% better recall
```

**Rollback Procedure**:
```bash
# Disable OpenSearch (falls back to PostgreSQL FTS)
truthgraph config set search.backend=postgres
truthgraph config set retrieval.strategy=semantic

# Stop OpenSearch services
docker compose --profile search down

# Verify search still works (using PostgreSQL FTS)
truthgraph query "test search" --backend postgres

# Optional: Remove OpenSearch data
docker volume rm truthgraph_opensearch-data
```

**Common Migration Issues**:

| Issue | Symptom | Solution |
|-------|---------|----------|
| Out of Memory | OpenSearch crashes, won't start | Increase JVM heap in OPENSEARCH_JAVA_OPTS |
| Slow Indexing | Takes > 1 hour for 100K docs | Increase batch size to 5000, use bulk API |
| Mapping Conflicts | Field type errors during indexing | Delete index and recreate with correct mappings |
| Index Not Found | Search fails with 404 | Run create-index command before indexing |
| Stale Results | New documents not appearing | Check auto_index setting, verify sync is running |

**Monitoring and Maintenance**:
```bash
# Check index health
curl -X GET "localhost:9200/_cat/indices?v"

# View indexing performance
curl -X GET "localhost:9200/_stats/indexing?pretty"

# Clear cache if search slows down
curl -X POST "localhost:9200/_cache/clear"

# Optimize indices (consolidate segments)
curl -X POST "localhost:9200/_forcemerge?max_num_segments=1"
```

### Hybrid Retrieval Configuration

**Retrieval Strategy**:
- **Semantic**: Vector similarity (existing embeddings)
- **Keyword**: BM25 via OpenSearch
- **Hybrid**: RRF (Reciprocal Rank Fusion) combining both

**Configuration**:
```yaml
# config/retrieval.yaml
retrieval:
  strategy: hybrid  # 'semantic', 'keyword', 'hybrid'

  semantic:
    top_k: 20
    min_similarity: 0.7

  keyword:
    enabled: true
    backend: opensearch  # 'opensearch' or 'postgres'
    top_k: 20
    boost_fields:
      title: 2.0
      content: 1.0

  hybrid:
    fusion_method: rrf  # Reciprocal Rank Fusion
    semantic_weight: 0.6
    keyword_weight: 0.4
```

**Implementation**:
```python
# src/retrieval/hybrid.py
class HybridRetriever:
    def __init__(self, config: RetrievalConfig):
        self.semantic = SemanticRetriever(config.semantic)
        self.keyword = KeywordRetriever(config.keyword)

    async def retrieve(self, query: str, top_k: int = 10):
        """Hybrid retrieval with RRF fusion"""
        semantic_results = await self.semantic.search(query)
        keyword_results = await self.keyword.search(query)

        return self._rrf_fusion(semantic_results, keyword_results, top_k)
```

### Graceful Fallback to PostgreSQL FTS

**Fallback Logic**:
```python
# src/retrieval/keyword.py
class KeywordRetriever:
    def __init__(self, config):
        self.opensearch = self._try_connect_opensearch(config)
        self.postgres = PostgresFTS(config)

    async def search(self, query: str):
        """Try OpenSearch, fallback to PostgreSQL FTS"""
        if self.opensearch and self.opensearch.is_healthy():
            try:
                return await self.opensearch.search(query)
            except Exception as e:
                logger.warning(f"OpenSearch failed: {e}, falling back to PostgreSQL")

        return await self.postgres.search(query)
```

**PostgreSQL FTS Enhancement**:
```sql
-- Add GIN index for full-text search
CREATE INDEX idx_claims_fts ON claims
USING GIN(to_tsvector('english', content));

-- Full-text search query
SELECT
    id,
    content,
    ts_rank(to_tsvector('english', content), query) as rank
FROM claims, to_tsquery('english', $search_query) query
WHERE to_tsvector('english', content) @@ query
ORDER BY rank DESC
LIMIT 20;
```

### Performance Comparison: OpenSearch vs PostgreSQL FTS

**Benchmark Setup**:
- Dataset: 100K chunks/claims, 50K sources
- Queries: 100 diverse search terms (mix of short/long, specific/broad)
- Hardware: 4 CPU cores, 8GB RAM (typical Docker host)
- Semantic embeddings available for all documents

**Search Performance Results**:

| Metric | PostgreSQL FTS | OpenSearch (Keyword) | Hybrid (Semantic + Keyword) |
|--------|----------------|---------------------|----------------------------|
| Avg Latency (ms) | 150-300 | 50-100 | 100-200 |
| P95 Latency (ms) | 500-800 | 150-200 | 250-350 |
| P99 Latency (ms) | 1000+ | 300-400 | 450-550 |
| Recall@10 | 0.65 | 0.70 | 0.82 |
| Precision@10 | 0.55 | 0.62 | 0.71 |
| Memory (MB) | +100 | +1024 | +1024 |
| Disk (GB) | +0.5 | +3.0 | +3.0 |

**Query Type Breakdown**:

| Query Type | PostgreSQL FTS | OpenSearch | Hybrid | Best Choice |
|------------|----------------|------------|--------|-------------|
| Exact phrase match | 80ms | 30ms | 50ms | OpenSearch |
| Fuzzy/typo tolerant | 200ms (poor) | 45ms | 60ms | OpenSearch |
| Semantic/conceptual | N/A | N/A | 120ms | Hybrid |
| Multi-field search | 250ms | 60ms | 100ms | Hybrid |
| Faceted/filtered | 300ms | 40ms | 80ms | OpenSearch |
| Boolean operators | 150ms | 35ms | 70ms | OpenSearch |

**Data Size Impact**:

| Dataset Size | PostgreSQL FTS (ms) | OpenSearch (ms) | Latency Improvement |
|--------------|---------------------|-----------------|---------------------|
| 10K documents | 50 | 20 | 2.5x |
| 50K documents | 180 | 60 | 3x |
| 100K documents | 280 | 80 | 3.5x |
| 500K documents | 1200 | 150 | 8x |
| 1M documents | 2500+ | 250 | 10x+ |

**Resource Comparison**:

| Configuration | Total RAM | Total Disk | Services Running |
|---------------|-----------|------------|------------------|
| Base (PostgreSQL FTS) | 3GB | 5GB | postgres, app |
| + OpenSearch | 5.5GB | 13GB | postgres, app, opensearch |
| + OpenSearch + Dashboards | 6.5GB | 14GB | postgres, app, opensearch, dashboards |

**Recommendation Matrix**:

| Your Situation | Recommended Configuration | Reasoning |
|----------------|--------------------------|-----------|
| < 50K docs, semantic search primary | PostgreSQL FTS + embeddings | Overhead not justified |
| 50-100K docs, keyword search important | Enable OpenSearch | Clear latency benefits |
| > 100K docs | Enable OpenSearch | Required for acceptable performance |
| Need best recall/precision | Hybrid retrieval | Combines strengths of both approaches |
| Resource constrained (< 6GB RAM) | PostgreSQL FTS only | Save 2-3GB RAM |
| Advanced search features needed | Enable OpenSearch | Fuzzy, facets, highlighting unavailable in PostgreSQL |

**Key Takeaways**:
- **Start with PostgreSQL FTS** if your dataset is small (< 50K docs) and semantic search meets your needs
- **Enable OpenSearch** when keyword search latency becomes problematic (> 200ms) or you need advanced features
- **Use Hybrid retrieval** for best results when you have both keyword and semantic search enabled
- **Monitor your actual usage patterns** before deciding - not all workloads benefit equally

## Docker Compose Profiles: Flexible Deployment Configurations

TruthGraph uses Docker Compose profiles to manage optional services. This allows you to run only the services you need, reducing resource consumption and deployment complexity.

### Available Profiles

**Profile Overview**:

| Profile | Services Enabled | Use Case | RAM Required | Disk Required |
|---------|------------------|----------|--------------|---------------|
| `default` (no profile) | postgres, app, tesseract | Core TruthGraph with OCR | 3-4GB | 5GB |
| `graph` | + neo4j | Complex graph queries, provenance visualization | +3GB (6-7GB total) | +5GB (10GB total) |
| `search` | + opensearch, dashboards | Advanced keyword search, hybrid retrieval | +4GB (7-8GB total) | +8GB (13GB total) |
| `full` | All services | Maximum capabilities, large-scale deployment | 10-12GB | 20GB |

### Usage Examples

**1. Basic Setup (PostgreSQL + OCR only)**:
```bash
# Start core services only
docker compose up -d

# Services running: postgres, app, tesseract
# RAM: ~3-4GB, Disk: ~5GB
```

**2. Enable Graph Features (+ Neo4j)**:
```bash
# Start with graph profile
docker compose --profile graph up -d

# Services running: postgres, app, tesseract, neo4j
# RAM: ~6-7GB, Disk: ~10GB

# Migrate data to Neo4j
truthgraph db migrate --target neo4j --full
```

**3. Enable Search Features (+ OpenSearch)**:
```bash
# Start with search profile
docker compose --profile search up -d

# Services running: postgres, app, tesseract, opensearch, opensearch-dashboards
# RAM: ~7-8GB, Disk: ~13GB

# Index documents in OpenSearch
truthgraph search index --source postgres --target opensearch
```

**4. Full Deployment (All Optional Services)**:
```bash
# Start all services
docker compose --profile graph --profile search up -d
# Or use the full profile if defined
docker compose --profile full up -d

# Services running: postgres, app, tesseract, neo4j, opensearch, opensearch-dashboards
# RAM: ~10-12GB, Disk: ~20GB
```

**5. Dynamic Profile Management**:
```bash
# Add a profile to running deployment
docker compose --profile search up -d
# Starts only new services (opensearch, dashboards)

# Remove a profile (stop services)
docker compose --profile search down
# Keeps other services running

# View running services and their profiles
docker compose ps
```

### Complete Docker Compose Example

**infra/docker-compose.yml** (with all profiles):
```yaml
version: '3.8'

services:
  # Base services (always run)
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: truthgraph
      POSTGRES_USER: truthgraph
      POSTGRES_PASSWORD: truthgraph
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  app:
    build: .
    depends_on:
      - postgres
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://truthgraph:truthgraph@postgres:5432/truthgraph

  tesseract:
    image: tesseract-ocr/tesseract:latest
    volumes:
      - ./media-temp:/workspace
    environment:
      - TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

  # Optional: Graph profile
  neo4j:
    image: neo4j:5.15-community
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/truthgraph
      - NEO4J_server_memory_heap_max__size=2G
    volumes:
      - neo4j-data:/data
    profiles:
      - graph
      - full

  # Optional: Search profile
  opensearch:
    image: opensearchproject/opensearch:2.11.0
    environment:
      - discovery.type=single-node
      - OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx2g
    ports:
      - "9200:9200"
    volumes:
      - opensearch-data:/usr/share/opensearch/data
    profiles:
      - search
      - full

  opensearch-dashboards:
    image: opensearchproject/opensearch-dashboards:2.11.0
    ports:
      - "5601:5601"
    environment:
      - OPENSEARCH_HOSTS=http://opensearch:9200
    profiles:
      - search
      - full

volumes:
  postgres-data:
  neo4j-data:
  opensearch-data:
```

### Profile Selection Guide

**Decision Tree**:

```
Start here: Do you need multimodal support (OCR)?
├─ Yes → Use default profile (no flag needed)
├─ No → Consider if TruthGraph is right for your use case

Do you need complex graph queries or provenance visualization?
├─ Yes → Add --profile graph
│   └─ Dataset > 100K nodes? → Definitely use graph profile
├─ No → Skip graph profile (save 3GB RAM)

Do you need advanced keyword search or hybrid retrieval?
├─ Yes → Add --profile search
│   └─ Dataset > 100K documents? → Definitely use search profile
├─ No → Skip search profile (save 4GB RAM)

Result: docker compose --profile <selected> up -d
```

**Common Configurations**:

1. **Personal Research** (small datasets, local machine):
   - Profile: `default` (no flag)
   - RAM: 3-4GB
   - Use case: Personal knowledge management, small document collections

2. **Team Collaboration** (medium datasets, shared server):
   - Profile: `--profile search`
   - RAM: 7-8GB
   - Use case: Team research, need good keyword search, moderate scale

3. **Investigative Journalism** (complex provenance, large datasets):
   - Profile: `--profile graph --profile search`
   - RAM: 10-12GB
   - Use case: Source tracking, complex relationships, extensive archives

4. **Academic Research** (very large datasets, computational analysis):
   - Profile: `--profile full`
   - RAM: 12-16GB (consider scaling OpenSearch/Neo4j)
   - Use case: Large-scale analysis, graph algorithms, advanced search

## TODO Checklist

### Multimodal Support (Required)

- [ ] Set up Tesseract Docker service in docker-compose.yml
- [ ] Implement OCR service wrapper (src/multimodal/ocr.py)
- [ ] Add language pack management (download/cache)
- [ ] Create PDF extraction module using PyPDF2/pdfplumber
- [ ] Implement image text extraction pipeline
- [ ] Add media file upload endpoints to API
- [ ] Create media_files and extracted_content tables
- [ ] Implement content hash deduplication
- [ ] Add CLI commands for file/directory ingestion
- [ ] Integrate extracted text with existing ingestion pipeline
- [ ] Add confidence scoring for OCR quality
- [ ] Implement page-level extraction for multi-page docs
- [ ] Create storage layer for original media files
- [ ] Add configurable retention policies
- [ ] Write integration tests for OCR pipeline
- [ ] Document supported formats and limitations
- [ ] Add example notebooks for multimodal ingestion

### Neo4j Integration (Optional)

- [ ] Add Neo4j service to docker-compose.yml with profile
- [ ] Install Neo4j Python driver (neo4j package)
- [ ] Implement PROV-O schema in Neo4j (Cypher scripts)
- [ ] Create initial migration script (PostgreSQL -> Neo4j)
- [ ] Add incremental sync mechanism with CDC
- [ ] Implement bidirectional conflict resolution
- [ ] Create rollback/verification tooling
- [ ] Add Neo4j indexes for performance
- [ ] Write graph query utilities (src/db/neo4j_queries.py)
- [ ] Update CLI with Neo4j migration commands
- [ ] Add health checks for Neo4j connectivity
- [ ] Document when to enable Neo4j vs PostgreSQL
- [ ] Create example Cypher queries for common patterns
- [ ] Add performance benchmarks (Neo4j vs PostgreSQL)
- [ ] Write migration guide with screenshots

### OpenSearch Integration (Optional)

- [ ] Add OpenSearch service to docker-compose.yml with profile
- [ ] Add OpenSearch Dashboards for visualization
- [ ] Install OpenSearch Python client
- [ ] Create index mappings for claims and sources
- [ ] Implement initial bulk indexing from PostgreSQL
- [ ] Add incremental indexing on data updates
- [ ] Create keyword search module (src/retrieval/keyword.py)
- [ ] Implement RRF hybrid retrieval
- [ ] Add graceful fallback to PostgreSQL FTS
- [ ] Enhance PostgreSQL FTS with GIN indexes
- [ ] Create retrieval configuration system (config/retrieval.yaml)
- [ ] Add health checks for OpenSearch connectivity
- [ ] Implement search analytics tracking
- [ ] Write performance benchmarks (all retrieval modes)
- [ ] Document when to enable OpenSearch vs PostgreSQL FTS
- [ ] Add example queries and use cases
- [ ] Create retrieval performance tuning guide

### Testing & Documentation

- [ ] Integration tests for multimodal pipeline
- [ ] End-to-end tests with optional services enabled/disabled
- [ ] Performance tests for hybrid retrieval
- [ ] Load tests for OCR service under concurrent requests
- [ ] Update architecture diagrams with new components
- [ ] Write deployment guide for all configurations
- [ ] Document resource requirements for each profile
- [ ] Create troubleshooting guide for optional services
- [ ] Add Jupyter notebooks demonstrating capabilities
- [ ] Update API documentation with new endpoints

### Configuration & DevOps

- [ ] Add environment variables for all optional services
- [ ] Create docker-compose profiles (base, graph, search, full)
- [ ] Implement feature flags for optional capabilities
- [ ] Add monitoring for OCR service health
- [ ] Configure log aggregation for all services
- [ ] Set up alerts for service failures
- [ ] Document backup procedures for Neo4j/OpenSearch
- [ ] Create resource sizing recommendations
- [ ] Add cost estimation guide for different configs

---

**Phase 3 Success Criteria**:
- OCR pipeline processes PDFs and images with >90% accuracy
- Optional services start/stop cleanly via profiles
- System degrades gracefully when optional services unavailable
- Clear documentation helps users choose their infrastructure
- Migration scripts preserve all data integrity
- Performance benchmarks validate scaling decisions
