# Phase 3: Enhanced Capabilities

**Timeline**: Months 5-6
**Focus**: Multimodal support and optional scaling infrastructure

## Overview and Goals

Phase 3 extends TruthGraph with advanced capabilities while maintaining its local-first philosophy. This phase introduces multimodal content processing and optional specialized infrastructure for users with growing scale requirements.

**Core Principles**:

- Multimodal support (OCR, PDF extraction) is a first-class feature
- Advanced infrastructure (Neo4j, OpenSearch) remains optional
- System gracefully degrades to PostgreSQL when optional services unavailable
- Docker Compose manages all optional services (local AND cloud deployments)
- Users choose their own scaling path
- **Cloud-ready architecture**: Optional services follow same cloud-ready patterns as core services
- **Cloud-optional design**: Optional services can run locally, in the cloud, or in hybrid configurations
- **Repository pattern**: Abstract storage and service implementations for seamless local/cloud switching

**Key Deliverables**:

1. OCR and document text extraction pipeline with cloud storage support
2. Optional Neo4j graph database with migration tooling (local or AuraDB cloud)
3. Optional OpenSearch for hybrid retrieval (local, AWS OpenSearch, or Elastic Cloud)
4. Updated documentation for all deployment configurations
5. Repository abstractions for media storage, graph operations, and search
6. Docker Compose profiles enabling/disabling services locally AND in cloud

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

**Media File Storage with Cloud Support**:

- Original files stored via MediaRepository abstraction (local filesystem or S3-compatible)
- **Local path**: `data/media/{tenant_id}/{source_id}/{hash}.{ext}`
- **Cloud path (S3)**: `s3://{bucket}/media/{tenant_id}/{source_id}/{hash}.{ext}`
- Deduplication via content hash (SHA256)
- Size limits configurable (default: 50MB per file)
- Multi-tenancy support via tenant_id in storage paths

**MediaRepository Abstraction**:

```python
# src/storage/media_repository.py
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional

class MediaRepository(ABC):
    """Abstract interface for media file storage (local or cloud)"""

    @abstractmethod
    async def store_file(
        self,
        file_data: BinaryIO,
        tenant_id: str,
        source_id: str,
        file_hash: str,
        extension: str
    ) -> str:
        """Store media file and return storage path"""
        pass

    @abstractmethod
    async def retrieve_file(self, path: str) -> BinaryIO:
        """Retrieve media file by path"""
        pass

    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """Delete media file"""
        pass

    @abstractmethod
    async def file_exists(self, path: str) -> bool:
        """Check if file exists"""
        pass


class LocalMediaRepository(MediaRepository):
    """Local filesystem storage for development and single-server deployments"""

    def __init__(self, base_path: str = "data/media"):
        self.base_path = Path(base_path)

    async def store_file(
        self,
        file_data: BinaryIO,
        tenant_id: str,
        source_id: str,
        file_hash: str,
        extension: str
    ) -> str:
        path = self.base_path / tenant_id / source_id / f"{file_hash}.{extension}"
        path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(path, 'wb') as f:
            await f.write(file_data.read())

        return str(path)


class S3MediaRepository(MediaRepository):
    """S3-compatible cloud storage for production deployments"""

    def __init__(self, bucket: str, region: str = "us-east-1"):
        self.s3_client = boto3.client('s3', region_name=region)
        self.bucket = bucket

    async def store_file(
        self,
        file_data: BinaryIO,
        tenant_id: str,
        source_id: str,
        file_hash: str,
        extension: str
    ) -> str:
        key = f"media/{tenant_id}/{source_id}/{file_hash}.{extension}"

        await asyncio.to_thread(
            self.s3_client.upload_fileobj,
            file_data,
            self.bucket,
            key,
            ExtraArgs={'ServerSideEncryption': 'AES256'}
        )

        return f"s3://{self.bucket}/{key}"
```

**Configuration for Media Storage**:

```yaml
# config/storage.yaml
media_storage:
  provider: local  # 'local' or 's3'

  local:
    base_path: data/media

  s3:
    bucket: truthgraph-media-prod
    region: us-east-1
    # Optional: use IAM roles, or provide credentials
    access_key_id: ${AWS_ACCESS_KEY_ID}
    secret_access_key: ${AWS_SECRET_ACCESS_KEY}
```

**OCR Processing Events**:

```python
# src/events/media_events.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class MediaFileProcessed:
    """Event emitted when media file is uploaded and stored"""
    media_file_id: str
    tenant_id: str
    source_id: str
    file_path: str
    mime_type: str
    file_size_bytes: int
    processed_at: datetime

@dataclass
class OCRCompleted:
    """Event emitted when OCR processing completes successfully"""
    media_file_id: str
    tenant_id: str
    pages_processed: int
    total_confidence: float
    text_length: int
    completed_at: datetime

@dataclass
class OCRFailed:
    """Event emitted when OCR processing fails"""
    media_file_id: str
    tenant_id: str
    error_message: str
    retry_count: int
    failed_at: datetime
```

**Extracted Content Storage**:

```sql
-- PostgreSQL schema addition (updated with tenant_id)
CREATE TABLE media_files (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    source_id UUID REFERENCES sources(id),
    file_hash TEXT NOT NULL,
    file_path TEXT NOT NULL,  -- Local or S3 path
    storage_provider TEXT NOT NULL,  -- 'local' or 's3'
    mime_type TEXT NOT NULL,
    file_size_bytes BIGINT,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_media_tenant (tenant_id),
    INDEX idx_media_hash (file_hash)
);

CREATE TABLE extracted_content (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    media_file_id UUID REFERENCES media_files(id),
    content_type TEXT, -- 'ocr', 'pdf_text', 'metadata'
    page_number INTEGER,
    text_content TEXT,
    confidence_score FLOAT,
    bounding_boxes JSONB,
    extracted_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_extracted_tenant (tenant_id)
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

**Cloud-Ready Neo4j Architecture**:

Phase 3 introduces Neo4j support with full cloud-ready capabilities. The GraphRepository abstraction allows seamless switching between local Neo4j, managed AuraDB (Neo4j's cloud service), or other compatible graph databases.

**GraphRepository Abstraction**:

```python
# src/storage/graph_repository.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class GraphRepository(ABC):
    """Abstract interface for graph database operations (local or cloud)"""

    @abstractmethod
    async def execute_query(self, cypher: str, parameters: Dict[str, Any] = None):
        """Execute Cypher query and return results"""
        pass

    @abstractmethod
    async def create_node(self, labels: List[str], properties: Dict[str, Any]):
        """Create graph node"""
        pass

    @abstractmethod
    async def create_relationship(
        self,
        from_node_id: str,
        to_node_id: str,
        rel_type: str,
        properties: Dict[str, Any] = None
    ):
        """Create graph relationship"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check database connectivity and health"""
        pass


class Neo4jGraphRepository(GraphRepository):
    """Local Neo4j instance (Docker) for development and single-server deployments"""

    def __init__(self, uri: str = "bolt://localhost:7687", auth: tuple = ("neo4j", "truthgraph")):
        from neo4j import AsyncGraphDatabase
        self.driver = AsyncGraphDatabase.driver(uri, auth=auth)

    async def execute_query(self, cypher: str, parameters: Dict[str, Any] = None):
        async with self.driver.session() as session:
            result = await session.run(cypher, parameters or {})
            return await result.data()


class AuraDBGraphRepository(GraphRepository):
    """Neo4j AuraDB (managed cloud) for production deployments"""

    def __init__(self, uri: str, username: str, password: str):
        from neo4j import AsyncGraphDatabase
        # AuraDB requires encrypted connections
        self.driver = AsyncGraphDatabase.driver(
            uri,
            auth=(username, password),
            encrypted=True,
            trust="TRUST_SYSTEM_CA_SIGNED_CERTIFICATES"
        )

    async def execute_query(self, cypher: str, parameters: Dict[str, Any] = None):
        async with self.driver.session() as session:
            result = await session.run(cypher, parameters or {})
            return await result.data()
```

**Configuration for Graph Storage**:

```yaml
# config/graph.yaml
graph_storage:
  provider: postgres  # 'postgres', 'neo4j', 'auradb'

  neo4j:
    uri: bolt://localhost:7687
    username: neo4j
    password: truthgraph

  auradb:
    uri: neo4j+s://xxxxx.databases.neo4j.io
    username: neo4j
    password: ${NEO4J_PASSWORD}  # Stored in secrets/environment
    database: neo4j  # AuraDB database name
```

**When to Use Managed Neo4j (AuraDB) vs Self-Hosted**:

| Factor | Self-Hosted Neo4j (Docker) | Managed AuraDB |
|--------|---------------------------|----------------|
| **Setup Complexity** | Medium (Docker Compose) | Low (cloud console) |
| **Operational Overhead** | High (backups, updates, monitoring) | Low (fully managed) |
| **Cost** | Infrastructure only (~$50-200/mo for VM) | $65+/mo for smallest instance |
| **Performance** | Depends on VM specs | Guaranteed SLA, optimized hardware |
| **Scalability** | Manual vertical scaling | Automatic scaling options |
| **High Availability** | Manual clustering setup | Built-in HA/clustering |
| **Backups** | Manual scripts needed | Automated daily backups |
| **Security** | Self-managed | SOC2, ISO 27001 certified |
| **Best For** | Development, small teams, cost-sensitive | Production, enterprise, mission-critical |

**Note on Cypher Query Compatibility**:
The same Cypher queries work with both local Neo4j and AuraDB cloud. The GraphRepository abstraction handles connection details, allowing you to develop locally and deploy to AuraDB without code changes.

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

| Resource | Local Neo4j (Docker) | Managed AuraDB Cloud Equivalent |
|----------|---------------------|--------------------------------|
| **RAM** | 2GB minimum, 4-8GB recommended | AuraDB Professional: 8GB instance |
| **CPU** | 1-4 cores | AuraDB Professional: 2-4 vCPUs |
| **Disk** | 2-5GB for 100K nodes | Included in AuraDB pricing |
| **IOPS** | SSD recommended (3000+ IOPS) | High-performance SSD (included) |
| **Cost** | VM cost only (~$50-200/mo) | Starting at $65/mo |

**Detailed Resource Breakdown**:

- **Local RAM**: 2GB minimum, 4-8GB recommended for production
  - Heap: 512MB-2GB (Java heap for Neo4j engine)
  - Page cache: 1GB+ (caches graph data from disk)
  - OS buffer: 1GB+ for file system operations
- **Local CPU**: 1 core minimum, 2-4 cores recommended
- **Local Disk**: 2-5GB for 100K nodes (1.5-2x your PostgreSQL graph data)
- **Cloud Alternative**: AuraDB instances auto-scale storage, include backups

**Enable with**: `docker compose --profile graph up -d` (local) or configure AuraDB connection in `config/graph.yaml` (cloud)

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

**Migration Script Structure (Using Repository Pattern)**:

```python
# src/db/migrations/neo4j_migration.py
from src.storage.graph_repository import GraphRepository

class Neo4jMigration:
    """Migration script that works with any GraphRepository implementation"""

    def __init__(self, graph_repo: GraphRepository, postgres_conn):
        self.graph_repo = graph_repo
        self.postgres = postgres_conn

    async def migrate_claims(self):
        """Migrate claims table to Neo4j nodes with batch processing"""
        # Batch size: 1000 nodes to balance memory and performance
        # Works with both Neo4jGraphRepository and AuraDBGraphRepository

        async with self.postgres.cursor() as cursor:
            await cursor.execute("SELECT * FROM claims")
            batch = []

            async for row in cursor:
                batch.append({
                    'id': str(row['id']),
                    'content': row['content'],
                    'tenant_id': row['tenant_id']
                })

                if len(batch) >= 1000:
                    await self._bulk_create_claims(batch)
                    batch = []

            if batch:
                await self._bulk_create_claims(batch)

    async def _bulk_create_claims(self, claims: List[Dict]):
        """Use repository pattern for bulk node creation"""
        cypher = """
        UNWIND $claims AS claim
        CREATE (c:Claim {
            id: claim.id,
            content: claim.content,
            tenant_id: claim.tenant_id
        })
        """
        await self.graph_repo.execute_query(cypher, {'claims': claims})

    async def migrate_relationships(self):
        """Migrate claim_relationships to Neo4j edges"""
        # Uses UNWIND for efficient bulk edge creation via repository

    async def migrate_provenance(self):
        """Migrate PROV-O entities and activities"""
        # Creates proper PROV-O node types and relationships via repository

    async def create_indexes(self):
        """Create Neo4j indexes for performance"""
        # Index on: claim.id, entity.id, activity.timestamp
        indexes = [
            "CREATE INDEX claim_id IF NOT EXISTS FOR (c:Claim) ON (c.id)",
            "CREATE INDEX claim_tenant IF NOT EXISTS FOR (c:Claim) ON (c.tenant_id)",
            "CREATE INDEX entity_id IF NOT EXISTS FOR (e:prov_Entity) ON (e.id)",
        ]

        for index_query in indexes:
            await self.graph_repo.execute_query(index_query)

    async def verify_migration(self):
        """Compare PostgreSQL and Neo4j for data consistency"""
        # Checks: node counts, relationship counts, sample data integrity
        # Works regardless of Neo4j deployment (local or AuraDB)
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

**Cloud-Ready Search Architecture**:

Phase 3 introduces OpenSearch support with full cloud-ready capabilities. The SearchRepository abstraction allows seamless switching between PostgreSQL FTS (default), local OpenSearch, AWS OpenSearch Service, or Elastic Cloud.

**SearchRepository Abstraction**:

```python
# src/storage/search_repository.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class SearchResult:
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]

class SearchRepository(ABC):
    """Abstract interface for search operations (local or cloud)"""

    @abstractmethod
    async def index_document(
        self,
        doc_id: str,
        content: str,
        metadata: Dict[str, Any] = None
    ):
        """Index a single document"""
        pass

    @abstractmethod
    async def bulk_index(self, documents: List[Dict[str, Any]]):
        """Bulk index multiple documents"""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Execute search query"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check search service health"""
        pass


class PostgresFTSRepository(SearchRepository):
    """PostgreSQL Full-Text Search (default, no extra services)"""

    def __init__(self, db_pool):
        self.db = db_pool

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[SearchResult]:
        async with self.db.acquire() as conn:
            results = await conn.fetch("""
                SELECT
                    id,
                    content,
                    ts_rank(to_tsvector('english', content), query) as score
                FROM claims, to_tsquery('english', $1) query
                WHERE to_tsvector('english', content) @@ query
                ORDER BY score DESC
                LIMIT $2
            """, query, top_k)

            return [
                SearchResult(
                    id=str(row['id']),
                    content=row['content'],
                    score=row['score'],
                    metadata={}
                )
                for row in results
            ]


class OpenSearchRepository(SearchRepository):
    """Local OpenSearch (Docker) for development and single-server deployments"""

    def __init__(self, hosts: List[str] = ["http://localhost:9200"]):
        from opensearchpy import AsyncOpenSearch
        self.client = AsyncOpenSearch(hosts=hosts)
        self.index_name = "truthgraph_claims"

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[SearchResult]:
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["content^2", "metadata.title"]
                }
            },
            "size": top_k
        }

        response = await self.client.search(
            index=self.index_name,
            body=search_body
        )

        return [
            SearchResult(
                id=hit['_id'],
                content=hit['_source']['content'],
                score=hit['_score'],
                metadata=hit['_source'].get('metadata', {})
            )
            for hit in response['hits']['hits']
        ]


class ElasticsearchCloudRepository(SearchRepository):
    """Elasticsearch Cloud (managed) for production deployments"""

    def __init__(self, cloud_id: str, api_key: str):
        from opensearchpy import AsyncOpenSearch
        # Elastic Cloud uses cloud_id and API keys
        self.client = AsyncOpenSearch(
            cloud_id=cloud_id,
            api_key=api_key
        )
        self.index_name = "truthgraph_claims"

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[SearchResult]:
        # Same search logic as OpenSearchRepository
        # API is compatible between OpenSearch and Elasticsearch
        pass


class AWSOpenSearchRepository(SearchRepository):
    """AWS OpenSearch Service (managed) for cloud deployments"""

    def __init__(self, endpoint: str, region: str = "us-east-1"):
        from opensearchpy import AsyncOpenSearch, RequestsHttpConnection
        from requests_aws4auth import AWS4Auth
        import boto3

        credentials = boto3.Session().get_credentials()
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            'es',
            session_token=credentials.token
        )

        self.client = AsyncOpenSearch(
            hosts=[{'host': endpoint, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
        self.index_name = "truthgraph_claims"

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[SearchResult]:
        # Same search logic as OpenSearchRepository
        pass
```

**Configuration for Search Storage**:

```yaml
# config/search.yaml
search:
  provider: postgres  # 'postgres', 'opensearch', 'aws-opensearch', 'elastic-cloud'

  postgres:
    # Uses existing database connection

  opensearch:
    hosts:
      - http://localhost:9200
    index_name: truthgraph_claims

  aws-opensearch:
    endpoint: search-truthgraph-xxxxx.us-east-1.es.amazonaws.com
    region: us-east-1
    # Uses IAM credentials from environment

  elastic-cloud:
    cloud_id: ${ELASTIC_CLOUD_ID}
    api_key: ${ELASTIC_API_KEY}
```

**When to Use Managed OpenSearch vs Self-Hosted**:

| Factor | Self-Hosted OpenSearch (Docker) | AWS OpenSearch Service | Elastic Cloud |
|--------|--------------------------------|----------------------|---------------|
| **Setup Complexity** | Medium (Docker Compose) | Low (AWS console) | Low (Elastic console) |
| **Operational Overhead** | High (backups, scaling, monitoring) | Low (fully managed) | Low (fully managed) |
| **Cost** | Infrastructure only (~$50-200/mo) | $50-500+/mo based on size | $95+/mo for smallest instance |
| **Performance** | Depends on VM specs | SSD-backed, optimized | SSD-backed, optimized |
| **Scalability** | Manual vertical/horizontal scaling | Easy horizontal scaling | Easy horizontal scaling |
| **High Availability** | Manual multi-node setup | Built-in multi-AZ | Built-in multi-region |
| **Backups** | Manual snapshots | Automated snapshots | Automated snapshots |
| **Security** | Self-managed | VPC, IAM integration | SAML, RBAC |
| **Best For** | Development, small teams | Production on AWS | Production, multi-cloud |

**Note on Search Query Compatibility**:
The same search queries work across all SearchRepository implementations. The abstraction handles connection details and authentication, allowing you to develop with PostgreSQL FTS, test with local OpenSearch, and deploy to AWS OpenSearch Service without code changes.

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

| Resource | Local OpenSearch (Docker) | AWS OpenSearch Service | Elastic Cloud |
|----------|--------------------------|----------------------|---------------|
| **RAM** | 1.5-5GB total | t3.small.search (2GB) or m6g.large.search (8GB) | 4GB minimum instance |
| **CPU** | 1-2 cores | 2 vCPUs (t3.small) or 2-4 vCPUs (m6g) | 2 vCPUs minimum |
| **Disk** | 2-3x data size (~5GB for 100K docs) | EBS storage (pay per GB) | Included in pricing |
| **IOPS** | SSD recommended (2000+ IOPS) | GP3 SSD with provisioned IOPS | High-performance SSD |
| **Cost** | VM cost only (~$50-200/mo) | $50-500+/mo based on instance | $95+/mo minimum |

**Detailed Resource Breakdown**:

- **Local RAM**:
  - OpenSearch: 1GB minimum, 2-4GB recommended (JVM heap: 512MB-2GB)
  - Dashboards: 512MB minimum, 1GB recommended
  - Total: 1.5-5GB depending on dataset size
- **Local CPU**: 1-2 cores (benefits from multiple cores for indexing)
- **Local Disk**: 2-3x document data size (100K documents ~5GB indexed data)
- **Cloud Alternative**: Managed instances include monitoring, backups, and auto-scaling

**Enable with**: `docker compose --profile search up -d` (local) or configure cloud endpoint in `config/search.yaml` (cloud)

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

**Fallback Logic (Using Repository Pattern)**:

```python
# src/retrieval/keyword.py
from src.storage.search_repository import SearchRepository, PostgresFTSRepository

class KeywordRetriever:
    """Keyword retrieval with automatic fallback using repository pattern"""

    def __init__(self, config):
        # Primary search repository (could be OpenSearch, AWS, Elastic Cloud, etc.)
        self.primary_repo = self._create_search_repository(config)

        # Always have PostgreSQL FTS as fallback
        self.fallback_repo = PostgresFTSRepository(config.db_pool)

    def _create_search_repository(self, config) -> SearchRepository:
        """Factory method to create appropriate SearchRepository"""
        provider = config.search.provider

        if provider == 'postgres':
            from src.storage.search_repository import PostgresFTSRepository
            return PostgresFTSRepository(config.db_pool)

        elif provider == 'opensearch':
            from src.storage.search_repository import OpenSearchRepository
            return OpenSearchRepository(config.search.opensearch.hosts)

        elif provider == 'aws-opensearch':
            from src.storage.search_repository import AWSOpenSearchRepository
            return AWSOpenSearchRepository(
                endpoint=config.search.aws_opensearch.endpoint,
                region=config.search.aws_opensearch.region
            )

        elif provider == 'elastic-cloud':
            from src.storage.search_repository import ElasticsearchCloudRepository
            return ElasticsearchCloudRepository(
                cloud_id=config.search.elastic_cloud.cloud_id,
                api_key=config.search.elastic_cloud.api_key
            )

        else:
            # Default to PostgreSQL FTS
            return PostgresFTSRepository(config.db_pool)

    async def search(self, query: str, top_k: int = 10):
        """Try primary repository, fallback to PostgreSQL FTS on failure"""

        # If primary is already PostgreSQL, no need for fallback
        if isinstance(self.primary_repo, PostgresFTSRepository):
            return await self.primary_repo.search(query, top_k)

        # Try primary repository with health check
        if await self.primary_repo.health_check():
            try:
                return await self.primary_repo.search(query, top_k)
            except Exception as e:
                logger.warning(
                    f"Primary search repository failed: {e}, "
                    f"falling back to PostgreSQL FTS"
                )

        # Fallback to PostgreSQL FTS
        logger.info("Using PostgreSQL FTS fallback")
        return await self.fallback_repo.search(query, top_k)
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

## Cost Optimization for Optional Services

**Local vs Managed Service Cost Comparison**:

This section helps you make informed decisions about when to use local (self-hosted) vs managed (cloud) services based on cost, scale, and operational considerations.

### Neo4j: Local vs AuraDB

| Scenario | Local Neo4j (Docker) | Managed AuraDB | Recommendation |
|----------|---------------------|----------------|----------------|
| **Development** | Free (existing VM) | $65/mo minimum | Use local |
| **Small Production** (< 100K nodes) | $50-100/mo VM | $65-150/mo | Local if you have ops expertise |
| **Medium Production** (100K-1M nodes) | $200-500/mo VM + ops time | $200-500/mo fully managed | AuraDB (saves ops time) |
| **Large Production** (> 1M nodes) | $500-1000/mo VM + significant ops | $500-2000/mo with HA | AuraDB (better reliability, HA) |

**When to Enable Managed Neo4j (AuraDB)**:

- Production workloads requiring high availability
- Limited DevOps resources for database operations
- Need for guaranteed SLAs and support
- Regulatory compliance requirements (SOC2, ISO 27001)
- Rapid scaling requirements

### OpenSearch: Local vs AWS/Elastic Cloud

| Scenario | Local OpenSearch (Docker) | AWS OpenSearch | Elastic Cloud | Recommendation |
|----------|--------------------------|----------------|---------------|----------------|
| **Development** | Free (existing VM) | N/A | N/A | Use local or PostgreSQL FTS |
| **Small Production** (< 100K docs) | $50-100/mo VM | $50-150/mo | $95-200/mo | Local or PostgreSQL FTS |
| **Medium Production** (100K-1M docs) | $200-400/mo VM + ops | $150-500/mo | $200-600/mo | AWS/Elastic (ops savings) |
| **Large Production** (> 1M docs) | $500-1000/mo VM + significant ops | $500-2000/mo with multi-AZ | $600-2500/mo | AWS/Elastic (better scale) |

**When to Enable Managed OpenSearch**:

- Dataset exceeds 500K documents (difficult to self-manage at scale)
- Need for horizontal scaling and high availability
- Integration with cloud ecosystem (AWS Lambda, CloudWatch, etc.)
- Limited search expertise in-house
- Compliance and security requirements

### OCR/Tesseract: Local vs Cloud OCR Services

| Scenario | Local Tesseract (Docker) | AWS Textract | Google Cloud Vision | Recommendation |
|----------|-------------------------|--------------|---------------------|----------------|
| **Development** | Free (existing VM) | Pay per page (~$0.0015/page) | Pay per page (~$0.0015/page) | Use local |
| **Low Volume** (< 10K pages/mo) | $20-50/mo VM | $15-30/mo | $15-30/mo | Local (more control) |
| **Medium Volume** (10K-100K pages/mo) | $50-100/mo VM | $150-300/mo | $150-300/mo | Hybrid: Local for bulk, Cloud for quality |
| **High Volume** (> 100K pages/mo) | $100-200/mo VM | $300-1500/mo | $300-1500/mo | Local (significant cost savings) |

**When to Use Cloud OCR Services**:

- Need superior accuracy for handwriting or complex layouts
- Processing forms with structured data extraction
- Multi-language documents requiring advanced language models
- Low volume with bursty workloads (no always-on infrastructure)

### Media Storage: Local vs S3

| Scenario | Local Filesystem | AWS S3 | S3-Compatible (MinIO, etc.) | Recommendation |
|----------|-----------------|--------|----------------------------|----------------|
| **Development** | Free (existing VM) | $0.023/GB/mo + requests | Free (self-hosted) | Use local filesystem |
| **Small Dataset** (< 100GB) | Included in VM cost | $2-5/mo | Included in VM cost | Local or S3 (negligible cost diff) |
| **Medium Dataset** (100GB-1TB) | Included in VM cost | $23-250/mo | Included in VM cost | Local if single-server, S3 if distributed |
| **Large Dataset** (> 1TB) | Need expensive storage | $250+/mo (with lifecycle rules) | Self-hosted cluster | S3 with lifecycle policies |

**When to Use S3 for Media Storage**:

- Multi-region deployments requiring global access
- Need for automatic backups and versioning
- Cost-effective archival with Glacier/Deep Archive
- Integration with CloudFront for CDN delivery
- Compliance requirements for data durability (11 9's)

### Hybrid Approach: Develop Local, Deploy Managed

**Recommended Development-to-Production Path**:

1. **Local Development** (Months 1-3):
   - PostgreSQL only (no optional services)
   - Local filesystem for media
   - Understand core functionality and patterns
   - **Cost**: Existing laptop/desktop (no additional cost)

2. **Local Testing with Optional Services** (Month 4):
   - Enable local Neo4j and OpenSearch via Docker profiles
   - Test with production-like data volumes
   - Benchmark performance to understand limits
   - **Cost**: $0 (development machine)

3. **Small Production Deployment** (Months 5-6):
   - Self-hosted on single VM or small cluster
   - PostgreSQL, local Neo4j, local OpenSearch
   - Local filesystem or S3 for media based on size
   - **Cost**: $100-300/mo (VM + storage)

4. **Scale to Managed Services** (Months 7+):
   - Migrate Neo4j to AuraDB when graph complexity increases
   - Migrate OpenSearch to AWS when dataset > 500K docs
   - Use S3 for media when multi-region or > 500GB
   - Keep PostgreSQL as source of truth (can use RDS for HA)
   - **Cost**: $300-1000+/mo (fully managed stack)

**Key Principle**: Start local, migrate to managed services based on scale signals, not upfront assumptions.

### Cost-Saving Strategies

**Use Spot Instances for Development/Testing**:

```yaml
# Development environment on AWS spot instances (70% cost savings)
# infra/terraform/dev/ec2.tf
resource "aws_instance" "truthgraph_dev" {
  instance_type = "t3.xlarge"
  spot_price    = "0.08"  # ~70% cheaper than on-demand ($0.1664)

  tags = {
    Environment = "development"
    Service     = "truthgraph"
  }
}
```

**S3 Lifecycle Policies for Media**:

```yaml
# Move old media to cheaper storage tiers
# infra/s3-lifecycle-policy.json
{
  "Rules": [
    {
      "Id": "ArchiveOldMedia",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "STANDARD_IA"  # ~50% cheaper after 90 days
        },
        {
          "Days": 365,
          "StorageClass": "GLACIER"  # ~80% cheaper after 1 year
        }
      ]
    }
  ]
}
```

**Right-Size Cloud Instances**:

- Start small, monitor metrics, scale up based on actual usage
- Use auto-scaling groups for OpenSearch and application servers
- Schedule shutdown of dev/test environments during off-hours
- Use reserved instances for predictable workloads (up to 60% savings)

## Docker Compose Profiles: Flexible Deployment Configurations

TruthGraph uses Docker Compose profiles to manage optional services. This allows you to run only the services you need, reducing resource consumption and deployment complexity. The same profiles work for local Docker deployments and can be adapted for cloud deployments via repository abstractions.

### Available Profiles

**Profile Overview**:

| Profile | Services Enabled | Use Case | RAM Required | Disk Required |
|---------|------------------|----------|--------------|---------------|
| `default` (no profile) | postgres, app, tesseract | Core TruthGraph with OCR | 3-4GB | 5GB |
| `graph` | + neo4j | Complex graph queries, provenance visualization | +3GB (6-7GB total) | +5GB (10GB total) |
| `search` | + opensearch, dashboards | Advanced keyword search, hybrid retrieval | +4GB (7-8GB total) | +8GB (13GB total) |
| `full` | All services | Maximum capabilities, large-scale deployment | 10-12GB | 20GB |
| `cloud-minimal` | postgres, app (cloud adapters) | Cloud deployment with managed services | 2-3GB | 3GB |
| `cloud-full` | postgres, app (all cloud services) | Full cloud with AuraDB, AWS OpenSearch, S3 | 2-3GB | 3GB |

**Note on Cloud Profiles**: Cloud profiles (`cloud-minimal`, `cloud-full`) use repository abstractions to connect to managed services instead of running them in Docker. The application configures connections to AuraDB, AWS OpenSearch, and S3 via environment variables.

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

**6. Cloud Deployment with Managed Services**:

```bash
# Deploy to cloud using managed services (no local Neo4j/OpenSearch)
docker compose --profile cloud-full up -d

# Services running: postgres, app (with cloud adapters)
# RAM: ~2-3GB (app only, no heavy services)

# Configure cloud services via environment variables
export GRAPH_PROVIDER=auradb
export NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
export NEO4J_PASSWORD=your-secure-password

export SEARCH_PROVIDER=aws-opensearch
export AWS_OPENSEARCH_ENDPOINT=search-truthgraph-xxxxx.us-east-1.es.amazonaws.com

export MEDIA_STORAGE_PROVIDER=s3
export S3_BUCKET=truthgraph-media-prod
export AWS_REGION=us-east-1

# Application connects to managed services, no Docker overhead for them
```

**7. Hybrid Deployment (Local PostgreSQL + Cloud Services)**:

```bash
# Use local PostgreSQL but cloud Neo4j and OpenSearch
docker compose up -d  # Start PostgreSQL and app

# Configure mixed local/cloud setup
export DATABASE_URL=postgresql://localhost:5432/truthgraph  # Local
export GRAPH_PROVIDER=auradb  # Cloud
export SEARCH_PROVIDER=aws-opensearch  # Cloud
export MEDIA_STORAGE_PROVIDER=local  # Local

# Best of both worlds: local data control, cloud service scalability
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

```text
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

## Cloud Migration Considerations

**When to Migrate Optional Services to Cloud**:

This section provides guidance on when and how to migrate each optional service from local (self-hosted) to managed cloud services.

### Migration Timing Signals

**Neo4j → AuraDB Migration Signals**:

- Graph queries taking > 2 seconds consistently
- Dataset exceeds 500K nodes
- Need for high availability (99.95%+ uptime)
- DevOps team spending > 4 hours/week on Neo4j maintenance
- Requirement for multi-region graph replication
- Compliance needs (SOC2, HIPAA, ISO 27001)

**OpenSearch → AWS/Elastic Cloud Migration Signals**:

- Search latency exceeds 500ms for 95th percentile
- Dataset exceeds 500K documents
- Need for advanced features (ML, anomaly detection)
- Horizontal scaling required (multi-node cluster)
- DevOps team spending > 4 hours/week on OpenSearch ops
- Integration requirements with cloud ecosystem

**Local Storage → S3 Migration Signals**:

- Media storage exceeds 500GB
- Need for multi-region access
- Backup/disaster recovery requirements
- Team distributed across multiple locations
- Cost of local storage > S3 cost (typically at 1TB+)

### Decision Matrix for Each Service

**Neo4j Migration Decision Matrix**:

| Factor | Stay Local | Migrate to AuraDB |
|--------|-----------|------------------|
| **Dataset Size** | < 500K nodes | > 500K nodes |
| **Query Complexity** | Simple 1-2 hop queries | Complex 4+ hop traversals |
| **Uptime SLA** | Best effort (99%) | Guaranteed 99.95%+ |
| **DevOps Resources** | Dedicated team | Limited resources |
| **Budget** | Cost-sensitive | Value-optimized |
| **Growth Rate** | Stable | Rapid growth (> 2x/year) |

**OpenSearch Migration Decision Matrix**:

| Factor | Stay Local or Use PostgreSQL FTS | Migrate to Managed OpenSearch |
|--------|----------------------------------|------------------------------|
| **Dataset Size** | < 500K documents | > 500K documents |
| **Search Features** | Basic keyword | Advanced (ML, facets, highlighting) |
| **Latency Requirements** | < 1 second acceptable | < 200ms required |
| **Scale Pattern** | Stable | Unpredictable spikes |
| **DevOps Resources** | Elasticsearch expertise | Limited search expertise |
| **Integration Needs** | Standalone | Cloud ecosystem (Lambda, etc.) |

**Media Storage Migration Decision Matrix**:

| Factor | Stay Local | Migrate to S3 |
|--------|-----------|---------------|
| **Storage Size** | < 500GB | > 500GB |
| **Access Pattern** | Single region | Multi-region |
| **Durability Needs** | Local backups sufficient | 99.999999999% required |
| **Cost** | Cheap local disk available | Variable, archival needs |
| **Team Distribution** | Centralized | Distributed globally |
| **Compliance** | Basic | Regulatory requirements |

### Migration Path with Zero Downtime

**Parallel Validation Strategy**:

The key to zero-downtime migration is running old and new systems in parallel, validating consistency, then cutting over.

#### Phase 1: Parallel Deployment (1-2 weeks)

```bash
# Enable both local and cloud services simultaneously
# Example: Local Neo4j + AuraDB in parallel

# 1. Set up AuraDB instance
# (via cloud console)

# 2. Configure dual-write to both local and cloud
export GRAPH_PROVIDER=neo4j  # Primary (local)
export GRAPH_PROVIDER_SHADOW=auradb  # Shadow (cloud)
export NEO4J_URI=bolt://localhost:7687
export AURADB_URI=neo4j+s://xxxxx.databases.neo4j.io

# 3. Application writes to both, reads from primary
# src/storage/graph_repository.py implements shadow writing
```

#### Phase 2: Data Migration & Validation (1-2 weeks)

```bash
# Migrate existing data to cloud
truthgraph db migrate --source neo4j --target auradb --full

# Continuous validation (runs in background)
truthgraph db validate --compare neo4j auradb --interval 1h

# Validation checks:
# - Node count matches
# - Relationship count matches
# - Sample queries return same results
# - Latency within acceptable range
```

#### Phase 3: Shadow Reads (1 week)

```bash
# Dual-read mode: read from both, compare results, serve from primary
export GRAPH_READ_MODE=dual  # Read from both local and cloud
export GRAPH_PRIMARY=neo4j  # Serve results from local (for now)
export GRAPH_SHADOW=auradb  # Validate against cloud

# Application logs discrepancies, alerts if > 1% mismatch
# Fix any sync issues discovered
```

#### Phase 4: Cutover (1 day)

```bash
# Switch primary to cloud
export GRAPH_PROVIDER=auradb  # Primary is now cloud
export GRAPH_PROVIDER_SHADOW=neo4j  # Local becomes shadow

# Monitor for 24-48 hours
# If issues arise, revert with single config change:
# export GRAPH_PROVIDER=neo4j
```

#### Phase 5: Cleanup (1 week later)

```bash
# After successful migration, stop dual-write
export GRAPH_PROVIDER=auradb  # Cloud only
unset GRAPH_PROVIDER_SHADOW

# Decommission local Neo4j
docker compose --profile graph down neo4j

# Keep local data for 30 days before deletion (safety buffer)
```

### Migration Checklist

**Pre-Migration**:

- [ ] Benchmark current performance (latency, throughput, error rate)
- [ ] Set up cloud service (AuraDB/AWS OpenSearch/S3)
- [ ] Configure repository abstraction for cloud service
- [ ] Test cloud service connection from application
- [ ] Document rollback procedures
- [ ] Set up monitoring for both local and cloud

**During Migration**:

- [ ] Enable dual-write mode (writes go to both)
- [ ] Migrate historical data to cloud
- [ ] Run validation jobs continuously
- [ ] Monitor for discrepancies and fix sync issues
- [ ] Enable shadow reads for validation
- [ ] Gradually increase traffic to cloud (10%, 25%, 50%, 100%)

**Post-Migration**:

- [ ] Verify all metrics (latency, error rate) within acceptable range
- [ ] Confirm cost is within budget
- [ ] Update documentation and runbooks
- [ ] Train team on cloud service management
- [ ] Decommission local service (after safety buffer period)
- [ ] Celebrate successful migration!

### Rollback Plan

**Critical Principle**: Always maintain ability to instantly rollback to local service.

```bash
# Single-command rollback (reverts to local)
truthgraph config set --graph-provider neo4j
truthgraph config set --search-provider opensearch
truthgraph config set --media-storage local

# Restart application
docker compose restart app

# Verify system operational
truthgraph health-check --verbose
```

**Rollback Scenarios**:

- Cloud service outage (> 5 minutes)
- Latency degradation (> 2x baseline)
- Cost overruns (> 150% of estimate)
- Data inconsistencies (> 1% mismatch rate)
- Team unable to troubleshoot cloud service issues

### Testing with Cloud Service Emulators

**LocalStack for AWS Services** (S3, OpenSearch):

```yaml
# docker-compose.localstack.yml
localstack:
  image: localstack/localstack:latest
  ports:
    - "4566:4566"  # LocalStack edge port
  environment:
    - SERVICES=s3,opensearch
    - DEBUG=1
  volumes:
    - localstack-data:/var/lib/localstack

# Test S3 operations without AWS costs
export AWS_ENDPOINT_URL=http://localhost:4566
aws s3 mb s3://truthgraph-media-test --endpoint-url http://localhost:4566
```

**Neo4j Community Edition** (simulates AuraDB):

```bash
# Local Neo4j mimics AuraDB API (Cypher queries identical)
docker compose --profile graph up -d neo4j

# Test migration scripts against local Neo4j before AuraDB
truthgraph db migrate --target neo4j --dry-run
```

**Benefits of Emulator Testing**:

- Zero cloud costs during development
- Fast iteration on migration scripts
- Offline development capability
- CI/CD pipeline integration without cloud credentials

## TODO Checklist

### Multimodal Support (Required)

- [ ] Set up Tesseract Docker service in docker-compose.yml
- [ ] Implement OCR service wrapper (src/multimodal/ocr.py)
- [ ] Add language pack management (download/cache)
- [ ] Create PDF extraction module using PyPDF2/pdfplumber
- [ ] Implement image text extraction pipeline
- [ ] Add media file upload endpoints to API
- [ ] Create media_files and extracted_content tables (with tenant_id)
- [ ] Implement content hash deduplication
- [ ] Add CLI commands for file/directory ingestion
- [ ] Integrate extracted text with existing ingestion pipeline
- [ ] Add confidence scoring for OCR quality
- [ ] Implement page-level extraction for multi-page docs
- [ ] **Create MediaRepository abstraction (src/storage/media_repository.py)**
- [ ] **Implement LocalMediaRepository for filesystem storage**
- [ ] **Implement S3MediaRepository for cloud storage**
- [ ] **Add OCR processing events (MediaFileProcessed, OCRCompleted, OCRFailed)**
- [ ] **Configure media storage provider via config/storage.yaml**
- [ ] Add configurable retention policies
- [ ] Write integration tests for OCR pipeline
- [ ] **Test media storage with both local and S3 implementations**
- [ ] Document supported formats and limitations
- [ ] Add example notebooks for multimodal ingestion

### Neo4j Integration (Optional)

- [ ] Add Neo4j service to docker-compose.yml with profile
- [ ] Install Neo4j Python driver (neo4j package)
- [ ] **Create GraphRepository abstraction (src/storage/graph_repository.py)**
- [ ] **Implement Neo4jGraphRepository for local Neo4j**
- [ ] **Implement AuraDBGraphRepository for managed cloud**
- [ ] **Configure graph storage provider via config/graph.yaml**
- [ ] Implement PROV-O schema in Neo4j (Cypher scripts)
- [ ] **Update migration scripts to use GraphRepository pattern**
- [ ] Create initial migration script (PostgreSQL -> Neo4j/AuraDB)
- [ ] Add incremental sync mechanism with CDC
- [ ] Implement bidirectional conflict resolution
- [ ] Create rollback/verification tooling
- [ ] Add Neo4j indexes for performance (via repository)
- [ ] Write graph query utilities using repository abstraction
- [ ] Update CLI with Neo4j/AuraDB migration commands
- [ ] Add health checks for Neo4j/AuraDB connectivity
- [ ] **Document when to use local Neo4j vs managed AuraDB**
- [ ] **Add cost comparison table for local vs AuraDB**
- [ ] Create example Cypher queries for common patterns
- [ ] Add performance benchmarks (Neo4j vs PostgreSQL)
- [ ] **Test with both local Neo4j and AuraDB**
- [ ] Write migration guide with screenshots

### OpenSearch Integration (Optional)

- [ ] Add OpenSearch service to docker-compose.yml with profile
- [ ] Add OpenSearch Dashboards for visualization
- [ ] Install OpenSearch Python client
- [ ] **Create SearchRepository abstraction (src/storage/search_repository.py)**
- [ ] **Implement PostgresFTSRepository (default, no extra services)**
- [ ] **Implement OpenSearchRepository for local OpenSearch**
- [ ] **Implement AWSOpenSearchRepository for AWS OpenSearch Service**
- [ ] **Implement ElasticsearchCloudRepository for Elastic Cloud**
- [ ] **Configure search provider via config/search.yaml**
- [ ] Create index mappings for claims and sources
- [ ] Implement initial bulk indexing from PostgreSQL
- [ ] Add incremental indexing on data updates
- [ ] **Update keyword search module to use SearchRepository pattern**
- [ ] Implement RRF hybrid retrieval
- [ ] **Update fallback logic to use repository pattern**
- [ ] Enhance PostgreSQL FTS with GIN indexes
- [ ] Create retrieval configuration system (config/retrieval.yaml)
- [ ] Add health checks for all search implementations
- [ ] Implement search analytics tracking
- [ ] Write performance benchmarks (all retrieval modes)
- [ ] **Document when to use local vs managed OpenSearch**
- [ ] **Add cost comparison for local vs AWS/Elastic Cloud**
- [ ] **Test with PostgreSQL FTS, local OpenSearch, and AWS OpenSearch**
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

### Cloud Services & Migration

- [ ] **Add cloud deployment profiles (cloud-minimal, cloud-full) to docker-compose**
- [ ] **Create configuration examples for AuraDB connection**
- [ ] **Create configuration examples for AWS OpenSearch Service**
- [ ] **Create configuration examples for Elastic Cloud**
- [ ] **Create configuration examples for S3 media storage**
- [ ] **Document cloud service setup procedures (AuraDB, AWS, etc.)**
- [ ] **Implement dual-write mode for zero-downtime migrations**
- [ ] **Implement shadow-read mode for migration validation**
- [ ] **Create migration validation tools (compare local vs cloud)**
- [ ] **Write cloud migration guide with timing signals**
- [ ] **Add decision matrices for when to migrate each service**
- [ ] **Document rollback procedures for failed migrations**
- [ ] **Set up LocalStack for testing AWS services locally**
- [ ] **Add CI/CD tests with cloud service emulators**
- [ ] **Create cost optimization guide with spot instances, lifecycle policies**

### Configuration & DevOps

- [ ] Add environment variables for all optional services (local and cloud)
- [ ] Create docker-compose profiles (base, graph, search, full, cloud-minimal, cloud-full)
- [ ] Implement feature flags for optional capabilities
- [ ] Add monitoring for OCR service health
- [ ] Configure log aggregation for all services
- [ ] Set up alerts for service failures
- [ ] Document backup procedures for Neo4j/OpenSearch (local and cloud)
- [ ] Create resource sizing recommendations (local and cloud equivalents)
- [ ] Add cost estimation guide for different configs (local vs cloud)
- [ ] **Add health check endpoints for all repository implementations**
- [ ] **Configure repository factory pattern for dynamic provider selection**

---

**Phase 3 Success Criteria**:

- OCR pipeline processes PDFs and images with >90% accuracy
- Optional services start/stop cleanly via profiles (local and cloud)
- System degrades gracefully when optional services unavailable
- Clear documentation helps users choose their infrastructure (local vs cloud)
- Migration scripts preserve all data integrity (local to local, local to cloud)
- Performance benchmarks validate scaling decisions
- **Repository abstractions work seamlessly across local and cloud implementations**
- **Same code runs with local services (Docker) or cloud services (AuraDB, AWS, S3)**
- **Zero-downtime migration path validated with dual-write/shadow-read modes**
- **Cost optimization guide helps users make informed local vs cloud decisions**
- **Users can develop locally and deploy to cloud without code changes**
