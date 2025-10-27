# Phase 2: Core Features (Months 3-4)

**Status:** Not Started
**Duration:** 2 months
**Dependencies:**

- Phase 1 MVP must be complete (see [Phase 1](phase_01_local_mvp.md))
- PostgreSQL with pgvector extension operational
- Redis Streams event processing working
- FAISS index infrastructure established
- FastAPI server and worker services running
- Basic NLI verification pipeline functional
- **Phase 1 cloud-ready patterns operational:**
  - Repository pattern for data access (ClaimRepository, EvidenceRepository)
  - CloudEvents infrastructure for event publishing/consumption
  - Observability framework (structured logging, metrics, tracing with correlation IDs)
  - Multi-tenancy support (tenant_id in all data access patterns)

---

## 1. Overview and Goals

Phase 2 expands the MVP foundation into a production-ready fact-checking system with three critical capabilities:

1. **Corpus Management:** Automated ingestion, processing, and indexing of diverse document sources
2. **Temporal Awareness:** Time-bounded fact validity and historical truth evaluation
3. **Compound Reasoning:** Multi-step claim verification with decomposition and logical inference

**Building on Phase 1 Cloud-Ready Foundations:**

Phase 2 extends the cloud-ready architecture patterns established in Phase 1. The repository pattern, CloudEvents integration, and observability infrastructure from Phase 1 enable Phase 2 features to work seamlessly in both local and cloud environments. Retrieval and reasoning abstractions introduced here prepare the system for horizontal scaling, making corpus management and multi-hop reasoning cloud-native from the start without sacrificing local development simplicity.

These abstractions make the code cleaner and more testable, not just "cloud-ready" - they provide clear interfaces, enable mocking for tests, and separate business logic from infrastructure concerns.

### Key Deliverables

- CLI tool for document ingestion supporting PDFs, HTML, text, and KILT Wikipedia
- Chunk-embed-index pipeline with Parquet storage and FAISS indexing
- Temporal schema extensions with `as_of` query support
- Claim decomposition engine using spaCy and rule-based parsing
- Numeric reasoning operators (comparison, arithmetic)
- Multi-step verification with reasoning chain storage

### Success Metrics

- Ingest and index 10,000+ Wikipedia articles from KILT snapshot
- Support temporal queries with date filtering at <50ms latency
- Successfully decompose 80%+ of multi-premise test claims
- Process compound claims with 2-3 subclaims end-to-end

---

## 2. Corpus Management System

### 2.1 Overview

Build a scalable ingestion pipeline that transforms raw documents into searchable, embedded chunks stored in Parquet files and indexed in FAISS.

### 2.2 Document Ingestion CLI

**Location:** `src/corpus/ingest.py`

**Command Interface:**

```bash
# Single file ingestion
python -m truthgraph.corpus.ingest --file path/to/doc.pdf --type pdf

# Batch directory ingestion
python -m truthgraph.corpus.ingest --dir path/to/docs --type auto

# KILT Wikipedia snapshot (full corpus)
python -m truthgraph.corpus.ingest \
  --kilt data/kilt/kilt_wikipedia.jsonl \
  --batch-size 100 \
  --workers 4 \
  --output data/corpus/kilt

# Subset for testing (first 1000 articles)
python -m truthgraph.corpus.ingest \
  --kilt data/kilt/kilt_wikipedia.jsonl \
  --batch-size 100 \
  --limit 1000 \
  --output data/corpus/kilt_test

# Resume interrupted ingestion
python -m truthgraph.corpus.ingest \
  --kilt data/kilt/kilt_wikipedia.jsonl \
  --batch-size 100 \
  --resume data/corpus/kilt/.checkpoint

# Ingest with custom chunking parameters
python -m truthgraph.corpus.ingest \
  --file documents/research_papers/ \
  --type pdf \
  --chunk-size 300 \
  --overlap 75 \
  --batch-size 32
```

**Key Components:**

- **File Parser Router:** Detects file type and routes to appropriate parser
  - PDF: `PyMuPDF` or `pdfminer.six` for text extraction
  - HTML: `trafilatura` or `readability-lxml` for clean text
  - Plain text: Direct UTF-8 reading with encoding detection fallback
  - KILT: Custom JSONL parser with Wikipedia metadata extraction

- **Metadata Extraction:**
  - Title, author, published date (from PDF metadata, HTML meta tags, or filename parsing)
  - Source URL or file path
  - Document hash (SHA-256) for deduplication
  - KILT-specific: Wikipedia article ID, revision timestamp, categories

### 2.3 Chunk-Embed-Index Pipeline

**Location:** `src/corpus/pipeline.py`

**Pipeline Stages:**

1. **Chunking Strategy:**
   - Sentence-based chunking with 200-300 token windows
   - 50-token overlap to preserve context at boundaries
   - Paragraph-aware splitting (preserve semantic units)
   - Libraries: `spaCy` sentencizer or `langchain.text_splitter`

2. **Embedding Generation:**
   - Model: `sentence-transformers/all-MiniLM-L6-v2` (384-dim baseline)
   - Batch size: 32 chunks per forward pass
   - GPU acceleration if available (CUDA), CPU fallback
   - Normalize embeddings for cosine similarity

3. **Storage Layer (Repository Pattern):**
   - **Use CorpusRepository from Phase 1 pattern:**

     ```python
     # src/corpus/repository.py
     class CorpusRepository(ABC):
         @abstractmethod
         async def store_chunks(self, chunks: List[Chunk], tenant_id: str) -> None: ...
         @abstractmethod
         async def get_chunk(self, chunk_id: str, tenant_id: str) -> Optional[Chunk]: ...

     class ParquetCorpusRepository(CorpusRepository):
         # V1: Local file storage
         async def store_chunks(self, chunks: List[Chunk], tenant_id: str) -> None:
             # Store to data/corpus/chunks/{tenant_id}/{date}.parquet

     class S3CorpusRepository(CorpusRepository):
         # V2: S3 storage (stub for now, tested with LocalStack)
         async def store_chunks(self, chunks: List[Chunk], tenant_id: str) -> None:
             # Store to s3://corpus-bucket/{tenant_id}/chunks/{date}.parquet
     ```

   - **Parquet Schema:**

     ```text
     - chunk_id: string (UUID)
     - document_id: string (references documents table)
     - tenant_id: string (multi-tenancy support)
     - chunk_index: int (position in document)
     - text: string
     - embedding: binary (serialized float32 array)
     - char_start: int
     - char_end: int
     - created_at: timestamp
     ```

   - Storage path: `data/corpus/chunks/{tenant_id}/{document_id_prefix}/{date}.parquet`
   - Partition by tenant and document date for efficient temporal queries
   - **Event Publishing:** Publish `CorpusDocumentIndexed` and `EmbeddingGenerated` CloudEvents after successful storage

4. **Vector Store Abstraction (See Section 2.5):**
   - Interface for vector operations: index, search, delete
   - V1 implementation: FAISS (local file-based)
   - V2 stubs: Pinecone, Weaviate (tested with emulators)
   - Configuration-based selection via environment variables

### 2.4 KILT Wikipedia Integration

**Dataset:** KILT (Knowledge Intensive Language Tasks) Wikipedia snapshot

**Processing Steps:**

1. Download KILT snapshot (JSONL format, ~5.9M articles)
2. Parse each article:
   - Extract: `wikipedia_id`, `wikipedia_title`, `text`, `categories`, `timestamp`
   - Split long articles into sections using heading markers
3. Extract published/revision date from timestamp
4. Run through chunk-embed-index pipeline
5. Store metadata in PostgreSQL `documents` table

**Schema Addition:**

```sql
ALTER TABLE documents ADD COLUMN kilt_id VARCHAR(255);
ALTER TABLE documents ADD COLUMN wikipedia_categories TEXT[];
CREATE INDEX idx_documents_kilt_id ON documents(kilt_id);
```

### 2.5 Vector Store Abstraction

**Location:** `src/corpus/vector_store.py`

**Goal:** Abstract vector operations to enable switching between FAISS (v1), Pinecone, and Weaviate (v2) without changing business logic.

**Interface Design:**

```python
# src/corpus/vector_store.py
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class SearchResult:
    chunk_id: str
    score: float
    distance: float

class VectorStore(ABC):
    """Abstract interface for vector similarity search."""

    @abstractmethod
    async def index(self, chunk_ids: List[str], embeddings: List[List[float]],
                   metadata: Optional[dict] = None) -> None:
        """Add vectors to the index with associated chunk IDs."""
        pass

    @abstractmethod
    async def search(self, query_embedding: List[float], top_k: int = 10,
                    filters: Optional[dict] = None) -> List[SearchResult]:
        """Search for similar vectors, optionally with metadata filters."""
        pass

    @abstractmethod
    async def delete(self, chunk_ids: List[str]) -> None:
        """Remove vectors from the index."""
        pass

    @abstractmethod
    async def get_stats(self) -> dict:
        """Return index statistics (count, dimension, etc.)."""
        pass


class FAISSVectorStore(VectorStore):
    """V1: Local FAISS implementation."""

    def __init__(self, index_path: str, dimension: int = 384):
        self.index_path = index_path
        self.dimension = dimension
        # IndexFlatIP for dev, IndexIVFFlat for production
        self.index = None  # Load from index_path or create new
        self.id_mapping = {}  # FAISS index → chunk_id

    async def index(self, chunk_ids: List[str], embeddings: List[List[float]],
                   metadata: Optional[dict] = None) -> None:
        # Add to FAISS index, update ID mapping
        # Persist index to disk after batch
        pass

    async def search(self, query_embedding: List[float], top_k: int = 10,
                    filters: Optional[dict] = None) -> List[SearchResult]:
        # FAISS search, map indices to chunk_ids
        # Post-filter by metadata (temporal, tenant_id) since FAISS doesn't support native filtering
        pass


class PineconeVectorStore(VectorStore):
    """V2: Cloud-based Pinecone implementation (stub for now)."""

    def __init__(self, api_key: str, index_name: str, environment: str):
        self.api_key = api_key
        self.index_name = index_name
        # Initialize Pinecone client

    async def search(self, query_embedding: List[float], top_k: int = 10,
                    filters: Optional[dict] = None) -> List[SearchResult]:
        # Native metadata filtering supported
        # filters = {"tenant_id": "...", "valid_from": {"$lte": as_of_date}}
        pass


class WeaviateVectorStore(VectorStore):
    """V2: Self-hosted or cloud Weaviate implementation (stub for now)."""
    pass
```

**Configuration-Based Selection:**

```python
# src/corpus/config.py
from enum import Enum

class VectorStoreType(Enum):
    FAISS = "faiss"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"

def get_vector_store(config: dict) -> VectorStore:
    store_type = VectorStoreType(config.get("VECTOR_STORE_TYPE", "faiss"))

    if store_type == VectorStoreType.FAISS:
        return FAISSVectorStore(
            index_path=config["FAISS_INDEX_PATH"],
            dimension=config.get("EMBEDDING_DIMENSION", 384)
        )
    elif store_type == VectorStoreType.PINECONE:
        return PineconeVectorStore(
            api_key=config["PINECONE_API_KEY"],
            index_name=config["PINECONE_INDEX_NAME"],
            environment=config["PINECONE_ENVIRONMENT"]
        )
    else:
        raise ValueError(f"Unsupported vector store: {store_type}")
```

**Environment Variables:**

```bash
# V1: Local FAISS
VECTOR_STORE_TYPE=faiss
FAISS_INDEX_PATH=data/corpus/faiss/v2/index.faiss
FAISS_INDEX_TYPE=IndexIVFFlat
FAISS_INDEX_CLUSTERS=100

# V2: Cloud Pinecone (for future)
VECTOR_STORE_TYPE=pinecone
PINECONE_API_KEY=xxx
PINECONE_INDEX_NAME=truthgraph-prod
PINECONE_ENVIRONMENT=us-west1-gcp
```

**Benefits:**

- **Testability:** Mock VectorStore interface in unit tests
- **Flexibility:** Switch backends via config without code changes
- **Cloud-ready:** Pinecone/Weaviate stubs prepared for v2
- **Local development:** FAISS works without external dependencies

**Testing with Emulators (V2):**

- Use local Weaviate Docker container for integration tests
- Pinecone doesn't have emulator, but interface allows mocking

---

## 3. Temporal Basics

### 3.1 Database Schema Additions

**Documents Table:**

```sql
ALTER TABLE documents
  ADD COLUMN published_at TIMESTAMP,
  ADD COLUMN valid_from TIMESTAMP,
  ADD COLUMN valid_to TIMESTAMP,
  ADD COLUMN is_superseded BOOLEAN DEFAULT FALSE,
  ADD COLUMN superseded_by UUID REFERENCES documents(id);

CREATE INDEX idx_documents_temporal ON documents(tenant_id, valid_from, valid_to);
CREATE INDEX idx_documents_published ON documents(tenant_id, published_at);
```

**Claims Table:**

```sql
ALTER TABLE claims
  ADD COLUMN claim_date TIMESTAMP,  -- Date the claim refers to
  ADD COLUMN verified_at TIMESTAMP, -- When we verified it
  ADD COLUMN as_of_date TIMESTAMP;  -- Historical verification point

CREATE INDEX idx_claims_temporal ON claims(tenant_id, claim_date, verified_at);
```

**Note on Multi-Tenancy:** All temporal queries include `tenant_id` filter to ensure data isolation. This pattern works identically whether using local PostgreSQL or cloud-managed databases (RDS, Cloud SQL), making the code portable without modification.

**Chunk Metadata:**

- Add `valid_from` and `valid_to` to Parquet schema
- Inherit from parent document by default
- Allow manual override for time-sensitive facts within documents

**Temporal Event Schemas (CloudEvents):**

```python
# Published when document temporal metadata changes
{
  "type": "com.truthgraph.claim.temporal.state-changed",
  "source": "/temporal/processor",
  "subject": "claim/{claim_id}",
  "datacontenttype": "application/json",
  "data": {
    "claim_id": "uuid",
    "tenant_id": "tenant-123",
    "previous_state": {
      "claim_date": "2020-01-01T00:00:00Z",
      "as_of_date": "2024-01-01T00:00:00Z"
    },
    "new_state": {
      "claim_date": "2020-01-01T00:00:00Z",
      "as_of_date": "2024-06-01T00:00:00Z"
    },
    "correlation_id": "request-correlation-id"
  }
}
```

These events enable:

- Audit trail for temporal state changes
- Triggering re-verification when temporal context changes
- Cross-service coordination (works same in local Redis or cloud message queue)

### 3.2 As-Of Query Parameter

**API Endpoint:**

```json
POST /api/v1/verify
{
  "claim": "Angela Merkel is the Chancellor of Germany",
  "as_of": "2015-06-01"  // Optional ISO 8601 date
}
```

**Implementation:** `src/api/verify.py`

**Query Logic:**

1. Parse `as_of` parameter (default: current date)
2. Filter documents: `valid_from <= as_of <= valid_to`
3. Apply filter at FAISS search result post-processing:
   - Retrieve top-k chunks from FAISS
   - Lookup chunk metadata from Parquet
   - Filter by temporal validity
   - Re-rank remaining chunks
4. Return temporal context in response:

   ```json
   {
     "verdict": "SUPPORTED",
     "as_of": "2015-06-01",
     "evidence": [{
       "text": "...",
       "valid_from": "2005-11-22",
       "valid_to": "2021-12-08"
     }]
   }
   ```

### 3.3 Date Filtering in Retrieval

**FAISS Integration:**

Since FAISS doesn't support temporal filtering natively, implement a two-stage approach:

1. **Over-retrieve:** Fetch top-100 candidates from FAISS (10x normal)
2. **Temporal filter:** Apply date constraints in Python
3. **Re-rank:** Keep top-10 after filtering

**Optimization (Future):**

- Pre-build separate FAISS indices per time period (e.g., year-based)
- Route queries to appropriate index based on `as_of` date
- Reduces over-retrieval overhead

**Date Extraction Utilities:** `src/corpus/temporal.py`

- Parse common date formats from text (ISO 8601, MDY, DMY)
- Extract "valid from" hints (e.g., "as of 2020", "since March 2019")
- NER-based date detection using spaCy `DATE` entity type

### 3.4 Temporal Query Examples

#### Example 1: Historical Political Claims

```bash
# Query about Angela Merkel's position in 2015
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "claim": "Angela Merkel is the Chancellor of Germany",
    "as_of": "2015-06-01"
  }'

# Expected response:
{
  "verdict": "SUPPORTED",
  "confidence": 0.94,
  "as_of": "2015-06-01",
  "evidence": [
    {
      "text": "Angela Merkel has served as Chancellor of Germany since 2005...",
      "valid_from": "2005-11-22",
      "valid_to": "2021-12-08",
      "source": "Wikipedia: Angela Merkel"
    }
  ]
}

# Same query for current date would return different validity period
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "claim": "Angela Merkel is the Chancellor of Germany",
    "as_of": "2024-01-01"
  }'

# Expected response:
{
  "verdict": "REFUTED",
  "confidence": 0.89,
  "as_of": "2024-01-01",
  "evidence": [
    {
      "text": "Olaf Scholz became Chancellor of Germany on December 8, 2021...",
      "valid_from": "2021-12-08",
      "valid_to": null,
      "source": "Wikipedia: Olaf Scholz"
    }
  ]
}
```

#### Example 2: Scientific Data with Temporal Context

```bash
# Query about historical CO2 levels
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "claim": "Atmospheric CO2 levels are above 400 ppm",
    "as_of": "2013-05-01"
  }'

# Expected: SUPPORTED (CO2 crossed 400 ppm in May 2013)

curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "claim": "Atmospheric CO2 levels are above 400 ppm",
    "as_of": "2012-01-01"
  }'

# Expected: REFUTED (CO2 was ~393 ppm in 2012)
```

#### Example 3: Corporate Information Changes

```bash
# Query about historical company CEO
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "claim": "Steve Jobs is the CEO of Apple",
    "as_of": "2010-06-01"
  }'

# Expected: SUPPORTED (Jobs was CEO 2007-2011)
```

---

## 4. Compound Reasoning

### 4.1 Claim Decomposition

**Goal:** Break complex claims into verifiable atomic subclaims

#### Example 1: Causal Claims

```text
Input: "Since CO₂ levels increased from 350ppm to 420ppm, ocean pH decreased"

Output Subclaims:
[
  "CO₂ levels increased from 350ppm to 420ppm",
  "Ocean pH decreased",
  "CO₂ increase causes ocean pH decrease"  // causal inference
]
```

#### Example 2: Conjunctive Claims

```text
Input: "The Eiffel Tower is in Paris and it was completed in 1889"

Output Subclaims:
[
  "The Eiffel Tower is in Paris",
  "The Eiffel Tower was completed in 1889"
]
```

#### Example 3: Comparative Claims

```text
Input: "Mount Everest is taller than K2 and both are in the Himalayas"

Output Subclaims:
[
  "Mount Everest height measurement",
  "K2 height measurement",
  "Mount Everest is taller than K2",
  "Mount Everest is in the Himalayas",
  "K2 is in the Himalayas"
]
```

**Implementation:** `src/reasoning/decomposition.py`

**Strategy:**

1. **Dependency Parsing (spaCy):**
   - Parse claim into syntactic tree
   - Identify conjunctions (AND, OR), causation markers ("because", "since", "therefore")
   - Split at coordination boundaries

2. **Rule-Based Patterns:**
   - Comparative: "X is greater than Y" → ["X value", "Y value", "X > Y"]
   - Temporal: "X happened before Y" → ["X occurred", "Y occurred", "X.time < Y.time"]
   - Quantitative: "X increased from A to B" → ["X was A", "X is B", "B > A"]

3. **Coreference Resolution:**
   - Resolve pronouns and entity mentions within subclaims
   - Ensure subclaims are self-contained

**Libraries:**

- `spaCy` with `en_core_web_trf` (transformer-based)
- Custom patterns using `Matcher` API
- Fallback: prompt-based decomposition using local LLM (future)

### 4.2 Numeric Operators

**Location:** `src/reasoning/numeric.py`

**Supported Operators:**

- **Comparison:** `>`, `<`, `>=`, `<=`, `=`, `!=`
- **Arithmetic:** `+`, `-`, `*`, `/`, `%`
- **Aggregation:** `sum`, `avg`, `min`, `max`, `count`

**Numeric Claim Schema:**

```python
@dataclass
class NumericClaim:
    subject: str          # "GDP of US"
    operator: str         # ">"
    value: float          # 20_000_000_000_000
    unit: Optional[str]   # "USD"
    comparand: Optional[str]  # "GDP of China" (for relative comparisons)
```

**Implementation Steps:**

1. **Extraction:**
   - Regex patterns for numbers (with separators, scientific notation)
   - NER for quantities and units (`QUANTITY`, `MONEY`, `PERCENT`)
   - Operator detection from text ("greater than", "exceeds", "is more than")

2. **Normalization:**
   - Unit conversion (e.g., "million" → 1e6, "km" → "m")
   - Currency conversion (optional, requires exchange rates)
   - Time normalization (Q1 2023 → 2023-01-01 to 2023-03-31)

3. **Verification:**
   - Extract numeric values from evidence chunks
   - Parse into comparable format
   - Evaluate operator: `evaluate(claim.value, claim.operator, evidence.value)`
   - Return confidence based on exact match, range overlap, or approximation

**Example:**

```python
claim = "US GDP in 2023 was over $25 trillion"
# Decompose: subject="US GDP", time="2023", operator=">", value=25e12, unit="USD"

evidence = "The United States GDP reached $25.5 trillion in 2023"
# Extract: value=25.5e12, unit="USD"

verify_numeric(claim, evidence)
# → True (25.5e12 > 25e12), confidence=0.95
```

### 4.3 Multi-Step Verification

**Workflow:** `src/reasoning/multi_step.py`

**Process:**

1. **Decompose:** Break claim into subclaims (see 4.1)
2. **Verify Each Subclaim:**
   - Run retrieval for each subclaim independently
   - Use NLI model (DeBERTa) for entailment scoring
   - Assign verdict: SUPPORTED, REFUTED, NOT_ENOUGH_INFO
3. **Aggregate Verdicts:**
   - AND logic: All must be SUPPORTED → claim SUPPORTED
   - OR logic: Any SUPPORTED → claim SUPPORTED
   - Causal: Premises SUPPORTED + inference valid → conclusion SUPPORTED
4. **Build Reasoning Chain:** Link subclaims → evidence → inference steps

**Inference Rules:**

```python
def aggregate_verdicts(subclaims: List[VerificationResult], logic: str) -> Verdict:
    if logic == "AND":
        return "SUPPORTED" if all(sc.verdict == "SUPPORTED" for sc in subclaims) else "REFUTED"
    elif logic == "OR":
        return "SUPPORTED" if any(sc.verdict == "SUPPORTED" for sc in subclaims) else "NOT_ENOUGH_INFO"
    elif logic == "CAUSAL":
        # All premises supported + causal link verified
        premises_ok = all(sc.verdict == "SUPPORTED" for sc in subclaims[:-1])
        causal_ok = verify_causal_link(subclaims[-1])
        return "SUPPORTED" if premises_ok and causal_ok else "REFUTED"
```

### 4.4 Compound Reasoning Examples with Actual Claims

#### Example 1: Environmental Claim with Numeric Reasoning

```bash
# Complex claim with multiple numeric facts
POST /api/v1/verify
{
  "claim": "Global temperatures increased by 1.1°C since 1850 and Arctic sea ice decreased by 13% per decade",
  "detailed": true
}

# Decomposition:
{
  "root_claim": "Global temperatures increased by 1.1°C since 1850 and Arctic sea ice decreased by 13% per decade",
  "subclaims": [
    {
      "id": "sc1",
      "text": "Global temperatures increased by 1.1°C since 1850",
      "type": "numeric",
      "numeric_components": {
        "subject": "global temperature",
        "change": 1.1,
        "unit": "°C",
        "baseline": "1850",
        "operator": "increased"
      }
    },
    {
      "id": "sc2",
      "text": "Arctic sea ice decreased by 13% per decade",
      "type": "numeric",
      "numeric_components": {
        "subject": "Arctic sea ice extent",
        "change": 13,
        "unit": "%",
        "timeframe": "per decade",
        "operator": "decreased"
      }
    }
  ],
  "logic": "AND"
}

# Verification Result:
{
  "verdict": "SUPPORTED",
  "confidence": 0.88,
  "reasoning_chain": {
    "steps": [
      {
        "subclaim": "Global temperatures increased by 1.1°C since 1850",
        "verdict": "SUPPORTED",
        "confidence": 0.92,
        "evidence": [
          {
            "text": "According to NASA and NOAA, global average temperature has increased by approximately 1.1°C (2°F) since the late 19th century",
            "source": "NASA Climate Change",
            "numeric_match": {
              "extracted_value": 1.1,
              "claim_value": 1.1,
              "tolerance": 0.1,
              "match": "exact"
            }
          }
        ]
      },
      {
        "subclaim": "Arctic sea ice decreased by 13% per decade",
        "verdict": "SUPPORTED",
        "confidence": 0.84,
        "evidence": [
          {
            "text": "Arctic sea ice extent has declined by about 13 percent per decade since satellite observations began in 1979",
            "source": "NSIDC Arctic Sea Ice News",
            "numeric_match": {
              "extracted_value": 13,
              "claim_value": 13,
              "tolerance": 1,
              "match": "exact"
            }
          }
        ]
      }
    ],
    "aggregate": "Both subclaims supported with high confidence → AND logic → SUPPORTED"
  }
}
```

#### Example 2: Historical Claim with Temporal Context

```bash
# Claim with historical facts requiring temporal awareness
POST /api/v1/verify
{
  "claim": "World War II began in 1939 and ended in 1945, lasting 6 years",
  "detailed": true
}

# Decomposition:
{
  "subclaims": [
    {
      "id": "sc1",
      "text": "World War II began in 1939",
      "type": "temporal"
    },
    {
      "id": "sc2",
      "text": "World War II ended in 1945",
      "type": "temporal"
    },
    {
      "id": "sc3",
      "text": "World War II lasted 6 years",
      "type": "numeric_temporal",
      "derived_from": ["sc1", "sc2"],
      "computation": "1945 - 1939 = 6"
    }
  ],
  "logic": "AND"
}

# Verification Result:
{
  "verdict": "SUPPORTED",
  "confidence": 0.96,
  "reasoning_chain": {
    "steps": [
      {
        "subclaim": "World War II began in 1939",
        "verdict": "SUPPORTED",
        "confidence": 0.98,
        "evidence": [{
          "text": "World War II began on September 1, 1939, when Germany invaded Poland",
          "temporal_match": {"year": 1939}
        }]
      },
      {
        "subclaim": "World War II ended in 1945",
        "verdict": "SUPPORTED",
        "confidence": 0.97,
        "evidence": [{
          "text": "The war in Europe ended with Germany's surrender on May 8, 1945, and in Asia with Japan's surrender on September 2, 1945",
          "temporal_match": {"year": 1945}
        }]
      },
      {
        "subclaim": "World War II lasted 6 years",
        "verdict": "SUPPORTED",
        "confidence": 0.93,
        "reasoning": "Computed from verified start (1939) and end (1945) dates: 1945 - 1939 = 6 years",
        "computation_verified": true
      }
    ]
  }
}
```

#### Example 3: Comparative Scientific Claim

```bash
# Claim comparing multiple values
POST /api/v1/verify
{
  "claim": "Jupiter is larger than Saturn, and both are gas giants with masses exceeding 300 Earth masses",
  "detailed": true
}

# Decomposition:
{
  "subclaims": [
    {
      "id": "sc1",
      "text": "Jupiter is larger than Saturn",
      "type": "comparative"
    },
    {
      "id": "sc2",
      "text": "Jupiter is a gas giant",
      "type": "categorical"
    },
    {
      "id": "sc3",
      "text": "Saturn is a gas giant",
      "type": "categorical"
    },
    {
      "id": "sc4",
      "text": "Jupiter mass exceeds 300 Earth masses",
      "type": "numeric",
      "numeric_components": {
        "subject": "Jupiter mass",
        "operator": ">",
        "value": 300,
        "unit": "Earth masses"
      }
    },
    {
      "id": "sc5",
      "text": "Saturn mass exceeds 300 Earth masses",
      "type": "numeric",
      "numeric_components": {
        "subject": "Saturn mass",
        "operator": ">",
        "value": 300,
        "unit": "Earth masses"
      }
    }
  ],
  "logic": "AND"
}

# Verification Result:
{
  "verdict": "REFUTED",
  "confidence": 0.91,
  "reasoning_chain": {
    "steps": [
      {
        "subclaim": "Jupiter is larger than Saturn",
        "verdict": "SUPPORTED",
        "confidence": 0.98
      },
      {
        "subclaim": "Jupiter is a gas giant",
        "verdict": "SUPPORTED",
        "confidence": 0.99
      },
      {
        "subclaim": "Saturn is a gas giant",
        "verdict": "SUPPORTED",
        "confidence": 0.99
      },
      {
        "subclaim": "Jupiter mass exceeds 300 Earth masses",
        "verdict": "SUPPORTED",
        "confidence": 0.96,
        "evidence": [{
          "text": "Jupiter has a mass of approximately 318 Earth masses",
          "numeric_match": {"extracted": 318, "claim": 300, "comparison": "318 > 300 = TRUE"}
        }]
      },
      {
        "subclaim": "Saturn mass exceeds 300 Earth masses",
        "verdict": "REFUTED",
        "confidence": 0.94,
        "evidence": [{
          "text": "Saturn's mass is approximately 95 Earth masses",
          "numeric_match": {"extracted": 95, "claim": 300, "comparison": "95 > 300 = FALSE"}
        }]
      }
    ],
    "aggregate": "Subclaim sc5 REFUTED → AND logic fails → Overall REFUTED"
  }
}
```

### 4.5 Reasoning Chain Storage

**Schema:** `src/db/models/reasoning_chain.py`

```sql
CREATE TABLE reasoning_chains (
  id UUID PRIMARY KEY,
  claim_id UUID REFERENCES claims(id),
  tenant_id VARCHAR(255) NOT NULL,
  chain_type VARCHAR(50),  -- 'compound', 'numeric', 'temporal'
  root_claim TEXT,
  correlation_id VARCHAR(255),  -- For tracing multi-hop reasoning across services
  created_at TIMESTAMP
);

CREATE TABLE reasoning_steps (
  id UUID PRIMARY KEY,
  chain_id UUID REFERENCES reasoning_chains(id),
  tenant_id VARCHAR(255) NOT NULL,
  step_index INT,
  subclaim TEXT,
  verdict VARCHAR(50),
  evidence_ids UUID[],
  confidence FLOAT,
  reasoning TEXT,  -- Human-readable explanation
  metadata JSONB,
  correlation_id VARCHAR(255)  -- Inherit from parent chain
);

CREATE INDEX idx_reasoning_chains_claim ON reasoning_chains(tenant_id, claim_id);
CREATE INDEX idx_reasoning_steps_chain ON reasoning_steps(chain_id, step_index);
CREATE INDEX idx_reasoning_correlation ON reasoning_chains(correlation_id);
```

**Repository Pattern Implementation:**

```python
# src/reasoning/repository.py
class ReasoningChainRepository(ABC):
    @abstractmethod
    async def save_chain(self, chain: ReasoningChain, tenant_id: str) -> None: ...

    @abstractmethod
    async def get_chain(self, claim_id: str, tenant_id: str) -> Optional[ReasoningChain]: ...

class PostgresReasoningChainRepository(ReasoningChainRepository):
    # V1: Local PostgreSQL
    async def save_chain(self, chain: ReasoningChain, tenant_id: str) -> None:
        # Store to local PostgreSQL with tenant_id filter

class CloudSQLReasoningChainRepository(ReasoningChainRepository):
    # V2: Cloud SQL (identical interface, different connection)
    # Works with Google Cloud SQL, AWS RDS, etc.
    pass
```

**Storage Logic with Event Publishing:**

1. Create `reasoning_chain` record for compound claim
2. For each verification step, create `reasoning_step` record
3. Publish `ReasoningStepCompleted` event after each step
4. Publish `ReasoningChainGenerated` event when entire chain completes
5. Use correlation_id to trace multi-hop reasoning across distributed services

**Reasoning Event Schemas (CloudEvents):**

```python
# Published after each reasoning step completes
{
  "type": "com.truthgraph.reasoning.step-completed",
  "source": "/reasoning/multi-step",
  "subject": "chain/{chain_id}/step/{step_index}",
  "datacontenttype": "application/json",
  "data": {
    "chain_id": "uuid",
    "step_index": 0,
    "subclaim": "CO₂ levels increased from 350ppm to 420ppm",
    "verdict": "SUPPORTED",
    "confidence": 0.92,
    "evidence_ids": ["chunk-uuid-1", "chunk-uuid-2"],
    "tenant_id": "tenant-123",
    "correlation_id": "request-correlation-id"
  }
}

# Published when entire reasoning chain completes
{
  "type": "com.truthgraph.reasoning.chain-generated",
  "source": "/reasoning/multi-step",
  "subject": "chain/{chain_id}",
  "datacontenttype": "application/json",
  "data": {
    "chain_id": "uuid",
    "claim_id": "uuid",
    "chain_type": "compound",
    "total_steps": 3,
    "final_verdict": "SUPPORTED",
    "final_confidence": 0.88,
    "tenant_id": "tenant-123",
    "correlation_id": "request-correlation-id"
  }
}
```

**Retrieval API:**

```json
GET /api/v1/reasoning/{claim_id}
{
  "chain_id": "uuid",
  "correlation_id": "request-correlation-id",
  "steps": [
    {
      "subclaim": "CO₂ levels increased",
      "verdict": "SUPPORTED",
      "evidence": ["chunk1", "chunk2"],
      "confidence": 0.92
    },
    ...
  ]
}
```

**Benefits:**

- **Traceability:** Correlation IDs enable distributed tracing
- **Observability:** Events published at each step for monitoring
- **Multi-tenancy:** tenant_id ensures data isolation
- **Cloud-ready:** Repository pattern works with any SQL backend

---

## 5. Performance Benchmarks and Targets

### 5.1 Ingestion Pipeline Performance

**Target Throughput:**

- PDF documents: 50-100 pages/minute (single worker)
- HTML pages: 200-300 pages/minute
- KILT Wikipedia: 100-150 articles/minute
- Embedding generation: 500-1000 chunks/minute (CPU), 5000+ chunks/minute (GPU)

**KILT Full Corpus Estimates:**

- Total articles: ~5.9M
- Estimated chunks (avg 10 per article): ~59M chunks
- Full ingestion time:
  - Single worker (CPU): 15-20 hours
  - 4 workers (CPU): 4-5 hours
  - GPU-accelerated: 2-3 hours

**Storage Requirements:**

- Raw KILT JSONL: ~40GB compressed, ~100GB uncompressed
- Parquet chunks: ~150GB (including text + metadata)
- Embeddings (384-dim float32): ~90GB (59M \* 384 \* 4 bytes)
- FAISS index (IndexFlatIP): ~90GB
- FAISS index (IndexIVFFlat, 100 clusters): ~45GB (with compression)
- Total storage: ~400-500GB

### 5.2 Retrieval Performance

**Latency Targets (Local Configuration - FAISS):**

- PostgreSQL FTS query: <10ms
- pgvector similarity search (100k vectors): <50ms
- FAISS search (10M vectors, IndexFlatIP): <20ms
- FAISS search (10M vectors, IndexIVFFlat): <5ms
- End-to-end retrieval (parallel, top-10): <100ms

**Latency Targets (Cloud Configuration - Pinecone):**

- Pinecone similarity search (10M vectors): 20-50ms (network + query)
- Pinecone with metadata filtering: 30-60ms
- End-to-end retrieval (parallel, top-10): 150-200ms
- Note: Higher latency due to network, but gains native metadata filtering

**Temporal Query Overhead:**

- Temporal filtering (over-retrieve + filter): +20-40ms (FAISS)
- Temporal filtering (native): +5-10ms (Pinecone with metadata filters)
- Target: Keep temporal queries under 150ms (local) / 250ms (cloud)

**Memory Requirements (Local FAISS):**

- FAISS index loaded in memory: ~45-90GB (depends on index type)
- Embedding model (all-MiniLM-L6-v2): ~120MB
- PostgreSQL working memory: 2-4GB
- Redis memory: 1-2GB (for event streams)
- Total system memory: 16GB minimum, 32GB recommended for production

**Memory Requirements (Cloud Pinecone):**

- Pinecone index: Managed externally (no local memory)
- Embedding model (all-MiniLM-L6-v2): ~120MB
- PostgreSQL working memory: 2-4GB
- Redis memory: 1-2GB (for event streams)
- Total system memory: 8GB sufficient (vector index offloaded to Pinecone)

**Testing Strategy:**

- **V1:** Test with local FAISS for development
- **V2:** Test with LocalStack S3 + Pinecone emulator (or mock) to validate cloud paths
- **CI/CD:** Run integration tests against both configurations to ensure portability

### 5.3 Verification Performance

**NLI Inference Latency:**

- DeBERTa-v3-base (CPU): 300-400ms per claim-evidence pair
- Batch processing (10 pairs): 500-700ms
- Target: Verify claim with 10 evidence items in <1 second

**Compound Reasoning Latency:**

- Claim decomposition (spaCy): 50-100ms
- 2-subclaim verification: 2-3 seconds
- 3-subclaim verification: 3-5 seconds
- Target: Keep compound claims under 10 seconds end-to-end

### 5.4 Accuracy Targets

**Retrieval Quality (Recall@10):**

- Simple factual claims: >80%
- Temporal claims: >70%
- Numeric claims: >75%
- Compound claims: >65%

**Verification Quality:**

- Simple claims (FEVER-style): >75% accuracy
- Temporal claims: >70% accuracy
- Numeric claims: >65% accuracy
- Compound claims (2-3 subclaims): >60% accuracy

**Target Metrics by Phase 2 End:**

- Overall system accuracy: >70% on test set
- False positive rate: <15%
- False negative rate: <20%

### 5.5 Scalability Benchmarks

**Document Corpus Scaling:**

| Corpus Size | FAISS Index | Query Latency | Memory Required |
|------------|-------------|---------------|-----------------|
| 10K docs   | 500MB       | 10ms          | 2GB             |
| 100K docs  | 5GB         | 15ms          | 8GB             |
| 1M docs    | 50GB        | 25ms          | 64GB            |
| 5.9M docs  | 90GB        | 40ms          | 128GB           |

**Concurrent Request Handling:**

- Target: 10 concurrent claim verifications
- Expected latency increase: <20% at 10 concurrent requests
- Redis queue depth: Monitor for backlog (alert if >100 pending claims)

---

## 6. Migration Path from Phase 1

### 6.1 Database Schema Migrations

#### Step 1: Add Temporal Columns

```sql
-- Migration: 001_add_temporal_columns.sql
-- Depends on: Phase 1 schema (claims, evidence, verdicts tables)

BEGIN;

-- Add temporal columns to documents table
ALTER TABLE documents
  ADD COLUMN published_at TIMESTAMP,
  ADD COLUMN valid_from TIMESTAMP,
  ADD COLUMN valid_to TIMESTAMP,
  ADD COLUMN is_superseded BOOLEAN DEFAULT FALSE,
  ADD COLUMN superseded_by UUID REFERENCES documents(id);

-- Add temporal columns to claims table
ALTER TABLE claims
  ADD COLUMN claim_date TIMESTAMP,
  ADD COLUMN verified_at TIMESTAMP DEFAULT NOW(),
  ADD COLUMN as_of_date TIMESTAMP;

-- Add temporal indexes
CREATE INDEX idx_documents_temporal ON documents(valid_from, valid_to);
CREATE INDEX idx_documents_published ON documents(published_at);
CREATE INDEX idx_claims_temporal ON claims(claim_date, verified_at);

COMMIT;
```

#### Step 2: Add KILT Metadata

```sql
-- Migration: 002_add_kilt_metadata.sql

BEGIN;

ALTER TABLE documents
  ADD COLUMN kilt_id VARCHAR(255),
  ADD COLUMN wikipedia_categories TEXT[];

CREATE INDEX idx_documents_kilt_id ON documents(kilt_id);
CREATE INDEX idx_documents_categories ON documents USING GIN(wikipedia_categories);

COMMIT;
```

#### Step 3: Add Reasoning Chain Tables

```sql
-- Migration: 003_add_reasoning_chains.sql

BEGIN;

CREATE TABLE reasoning_chains (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id UUID REFERENCES claims(id) ON DELETE CASCADE,
  chain_type VARCHAR(50) NOT NULL,
  root_claim TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE reasoning_steps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chain_id UUID REFERENCES reasoning_chains(id) ON DELETE CASCADE,
  step_index INT NOT NULL,
  subclaim TEXT NOT NULL,
  verdict VARCHAR(50),
  evidence_ids UUID[],
  confidence FLOAT,
  reasoning TEXT,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_reasoning_chains_claim ON reasoning_chains(claim_id);
CREATE INDEX idx_reasoning_steps_chain ON reasoning_steps(chain_id, step_index);

COMMIT;
```

### 6.2 Parquet Schema Evolution

**Phase 1 Parquet Schema:**

```python
# chunks_v1.parquet
{
    "chunk_id": "string",
    "document_id": "string",
    "chunk_index": "int32",
    "text": "string",
    "embedding": "binary",
    "char_start": "int32",
    "char_end": "int32",
    "created_at": "timestamp[ms]"
}
```

**Phase 2 Parquet Schema:**

```python
# chunks_v2.parquet
{
    "chunk_id": "string",
    "document_id": "string",
    "chunk_index": "int32",
    "text": "string",
    "embedding": "binary",
    "char_start": "int32",
    "char_end": "int32",
    "created_at": "timestamp[ms]",
    # New fields in Phase 2:
    "valid_from": "timestamp[ms]",
    "valid_to": "timestamp[ms]",
    "kilt_id": "string",
    "categories": "list<string>"
}
```

**Migration Strategy:**

1. Keep Phase 1 Parquet files unchanged
2. Write new ingestions to Phase 2 schema
3. Query logic handles both schemas (check for presence of temporal fields)
4. Optional: Batch reprocess Phase 1 files to Phase 2 schema during off-peak hours

### 6.3 API Changes

**New Endpoints:**

```text
POST /api/v1/corpus/ingest      # Trigger document ingestion
GET  /api/v1/corpus/status/{job_id}  # Check ingestion job status
GET  /api/v1/reasoning/{claim_id}     # Retrieve reasoning chain
```

**Modified Endpoints:**

```text
POST /api/v1/verify
# New optional parameters:
# - as_of: ISO 8601 date (for temporal queries)
# - detailed: boolean (return reasoning chain)
```

**Backward Compatibility:**

- All Phase 1 endpoints remain functional
- New parameters are optional with sensible defaults
- Response schema extended (new fields added, old fields unchanged)

### 6.4 Configuration Changes

**New Environment Variables:**

```bash
# Phase 2 additions to .env

# Corpus ingestion
CORPUS_INGEST_WORKERS=4
CORPUS_BATCH_SIZE=100
CORPUS_OUTPUT_DIR=data/corpus

# Chunking parameters
CHUNK_SIZE=300
CHUNK_OVERLAP=50
CHUNK_MIN_LENGTH=50

# FAISS configuration
FAISS_INDEX_TYPE=IndexIVFFlat  # or IndexFlatIP for exact search
FAISS_INDEX_CLUSTERS=100
FAISS_INDEX_PATH=data/corpus/faiss/v2

# Temporal settings
TEMPORAL_OVERRETRIEVAL_FACTOR=10
TEMPORAL_DEFAULT_ASOF=current  # or fixed date like 2024-01-01

# Reasoning configuration
DECOMPOSITION_MAX_SUBCLAIMS=5
REASONING_TIMEOUT_SECONDS=30
NUMERIC_TOLERANCE=0.1
```

### 6.5 Data Migration Checklist

**Pre-Migration:**

- [ ] Backup PostgreSQL database
- [ ] Backup existing Parquet files and FAISS indices
- [ ] Document current corpus size and metrics
- [ ] Test migrations on copy of production data

**Migration Steps:**

- [ ] Run database schema migrations (apply 001, 002, 003)
- [ ] Update application code to handle new schema
- [ ] Deploy new API and worker services
- [ ] Test backward compatibility with Phase 1 requests
- [ ] Ingest KILT corpus (or subset for testing)
- [ ] Rebuild FAISS index with temporal metadata
- [ ] Run end-to-end tests with temporal and compound claims
- [ ] Monitor performance metrics (latency, memory usage)

**Post-Migration:**

- [ ] Verify all Phase 1 functionality still works
- [ ] Run regression tests on known claims
- [ ] Update API documentation
- [ ] Train team on new features (corpus ingestion, temporal queries)

---

## 7. Cloud Migration Notes

### 7.1 Corpus Storage Migration (Local Files → S3)

**Current State (V1):** Parquet files stored locally at `data/corpus/chunks/{tenant_id}/{date}.parquet`

**Target State (V2):** Parquet files stored in S3 at `s3://corpus-bucket/{tenant_id}/chunks/{date}.parquet`

**Migration Strategy:**

```python
# Use CorpusRepository abstraction - business logic unchanged
# Only swap implementation:

# V1: Local development
repository = ParquetCorpusRepository(base_path="data/corpus/chunks")

# V2: Cloud deployment
repository = S3CorpusRepository(bucket="corpus-bucket", prefix="chunks")

# Application code remains identical:
await repository.store_chunks(chunks, tenant_id="tenant-123")
```

**Testing with LocalStack:**

```bash
# Start LocalStack S3 emulator
docker run -d -p 4566:4566 localstack/localstack

# Configure S3CorpusRepository to use LocalStack endpoint
export AWS_ENDPOINT_URL=http://localhost:4566
export CORPUS_BUCKET=test-corpus-bucket

# Run integration tests - code works identically with real S3 or LocalStack
pytest tests/integration/test_corpus_s3.py
```

**Benefits:**

- No code changes required in business logic
- Test cloud paths locally with LocalStack
- Gradual migration: run both local and S3 repositories side-by-side during transition

### 7.2 Vector Index Migration (FAISS → Pinecone/Weaviate)

**Current State (V1):** FAISS index stored locally, loaded into memory

**Target State (V2):** Managed vector database (Pinecone, Weaviate Cloud)

**Migration Strategy:**

1. **Export FAISS vectors to new index:**

   ```python
   # Read from FAISS + Parquet
   faiss_store = FAISSVectorStore(index_path="data/corpus/faiss/v2/index.faiss")
   chunks = load_all_chunks_from_parquet()

   # Push to Pinecone
   pinecone_store = PineconeVectorStore(
       api_key=os.environ["PINECONE_API_KEY"],
       index_name="truthgraph-prod"
   )

   for batch in chunks.batches(1000):
       await pinecone_store.index(
           chunk_ids=[c.chunk_id for c in batch],
           embeddings=[c.embedding for c in batch],
           metadata=[{"tenant_id": c.tenant_id, "valid_from": c.valid_from} for c in batch]
       )
   ```

2. **Parallel run for validation:**
   - Query both FAISS and Pinecone
   - Compare results for consistency
   - Log discrepancies for investigation

3. **Cutover:**
   - Update `VECTOR_STORE_TYPE=pinecone` in config
   - Deploy new version
   - Monitor latency and recall metrics

**Testing with Weaviate Local:**

```bash
# Run local Weaviate for integration tests
docker run -d -p 8080:8080 semitechnologies/weaviate:latest

# Configure WeaviateVectorStore for local endpoint
export WEAVIATE_URL=http://localhost:8080
export VECTOR_STORE_TYPE=weaviate

# Run same integration tests - interface is identical
pytest tests/integration/test_vector_store.py
```

#### Comparison: Local vs Cloud Vector Stores

| Feature | FAISS (Local) | Pinecone (Cloud) | Weaviate (Self-hosted/Cloud) |
|---------|---------------|------------------|------------------------------|
| **Setup** | Simple (pip install) | Managed service | Docker or cloud |
| **Metadata filtering** | Post-filter in Python | Native (fast) | Native (fast) |
| **Scalability** | Limited by RAM | Horizontal autoscaling | Manual scaling |
| **Latency** | 5-20ms (local) | 20-50ms (network) | 10-30ms (depends on hosting) |
| **Cost** | Free (local compute) | $$ (per query/storage) | $ (infrastructure) |
| **Multi-tenancy** | Manual (tenant_id filter) | Native namespaces | Native multi-tenancy |
| **Best for** | V1 local dev, small scale | V2 production, large scale | V2 production, cost-conscious |

### 7.3 Database Migration (Local PostgreSQL → Cloud SQL)

**Current State (V1):** Local PostgreSQL via Docker Compose

**Target State (V2):** Google Cloud SQL, AWS RDS, or Azure Database for PostgreSQL

**Migration Strategy:**

1. **No schema changes required** - Repository pattern abstracts connection details
2. **Update connection string:**

   ```bash
   # V1: Local
   DATABASE_URL=postgresql://truthgraph:password@localhost:5432/truthgraph

   # V2: Cloud SQL (example)
   DATABASE_URL=postgresql://user:pass@cloud-sql-proxy:5432/truthgraph
   ```

3. **Use Cloud SQL Proxy for secure connections**
4. **Enable connection pooling (pgBouncer) for scalability**

**Repository pattern ensures identical behavior:**

```python
# Same code works with local PostgreSQL or Cloud SQL
repository = PostgresReasoningChainRepository(connection_string=DATABASE_URL)
await repository.save_chain(chain, tenant_id="tenant-123")
```

### 7.4 Event Stream Migration (Local Redis → Cloud Pub/Sub)

**Current State (V1):** Redis Streams for event processing

**Target State (V2):** Google Cloud Pub/Sub, AWS SQS/SNS, or Azure Service Bus

**Migration Strategy:**

```python
# CloudEvents abstraction enables swapping message brokers

# V1: Redis Streams
class RedisEventPublisher(EventPublisher):
    async def publish(self, event: CloudEvent) -> None:
        await redis.xadd("events", event.to_json())

# V2: Cloud Pub/Sub
class PubSubEventPublisher(EventPublisher):
    async def publish(self, event: CloudEvent) -> None:
        await pubsub_client.publish(topic="truthgraph-events", data=event.to_json())

# Application code unchanged:
publisher = get_event_publisher()  # Factory based on config
await publisher.publish(CorpusDocumentIndexedEvent(...))
```

### 7.5 Testing Strategy for Cloud Migration

#### Phase 1: Local Emulators

- LocalStack for S3
- Local Weaviate for vector store
- Use mocks for Pinecone (no local emulator)

#### Phase 2: Staging Environment

- Deploy to cloud staging with real services
- Run full integration test suite
- Compare performance metrics with local baseline

#### Phase 3: Gradual Rollout

- Blue-green deployment: run V1 (local) and V2 (cloud) in parallel
- Route 10% traffic to V2, monitor metrics
- Gradual increase to 100% if metrics acceptable

**Key Principle:** Abstractions make migration low-risk. Each component can be migrated independently without affecting others.

---

## 8. TODO Checklist

### Corpus Management

> **Prerequisite:** Phase 1 complete with PostgreSQL, Redis, and basic FAISS setup working

**Ingestion CLI:**

- [ ] Create `src/corpus/ingest.py` with click interface
- [ ] Implement PDF parser using PyMuPDF (requires: `pymupdf`)
- [ ] Implement HTML parser using trafilatura (requires: `trafilatura`)
- [ ] Implement plain text parser with encoding detection (requires: `chardet`)
- [ ] Implement KILT JSONL parser
- [ ] Add file type auto-detection logic (depends on: all parsers above)
- [ ] Implement document deduplication (SHA-256 hash check, depends on: Phase 1 `documents` table)
- [ ] Add progress bars for batch ingestion (requires: `tqdm`)
- [ ] Write integration tests for each file type (depends on: all parsers)

**Chunk-Embed-Index Pipeline:**

- [ ] Design Parquet schema for chunks v2 with tenant_id (depends on: Phase 1 schema, Section 2.3)
- [ ] Implement CorpusRepository interface (depends on: Phase 1 repository pattern)
- [ ] Create ParquetCorpusRepository for local file storage (depends on: repository interface)
- [ ] Create S3CorpusRepository stub for cloud storage (depends on: repository interface)
- [ ] Add corpus event schemas: CorpusDocumentIndexed, EmbeddingGenerated (depends on: Phase 1 CloudEvents)
- [ ] Integrate event publishing in storage layer (depends on: event schemas, repository)
- [ ] Implement sentence-based chunking with overlap (requires: `spacy` or `langchain`)
- [ ] Add paragraph-aware splitting logic (depends on: chunking implementation)
- [ ] Integrate sentence-transformers embedding model (depends on: Phase 1 embedding setup)
- [ ] Add batch processing for embeddings with GPU support (depends on: embedding integration)
- [ ] Implement Parquet writer with temporal partitioning (depends on: schema design, Section 3.1)
- [ ] Write unit tests for chunking, embedding, indexing (depends on: implementations above)

**Vector Store Abstraction:**

- [ ] Create VectorStore interface with index, search, delete methods (see Section 2.5)
- [ ] Implement FAISSVectorStore for V1 local development (depends on: interface, Phase 1 FAISS)
- [ ] Create ID mapping layer FAISS ↔ chunk_id (depends on: FAISS implementation)
- [ ] Add incremental index updates to FAISS (depends on: ID mapping, FAISS utilities)
- [ ] Create PineconeVectorStore stub for V2 cloud (depends on: interface)
- [ ] Create WeaviateVectorStore stub for V2 cloud (depends on: interface)
- [ ] Implement configuration-based vector store selection (depends on: all implementations)
- [ ] Write unit tests with mocked vector store interface (depends on: interface)
- [ ] Write integration tests with local FAISS (depends on: FAISS implementation)
- [ ] Write integration tests with local Weaviate Docker (depends on: Weaviate stub)
- [ ] Add LocalStack S3 integration tests for corpus storage (depends on: S3CorpusRepository)

**KILT Integration:**

- [ ] Download KILT Wikipedia snapshot (coordinate with data team, ~40GB)
- [ ] Add PostgreSQL schema for `kilt_id` and `wikipedia_categories` (depends on: Phase 1 `documents` table, see Section 6.1 Migration 002)
- [ ] Implement KILT-specific metadata extraction (depends on: KILT JSONL parser)
- [ ] Run pilot ingestion (1000 articles) and validate quality (depends on: full pipeline above)
- [ ] Full ingestion and indexing 5.9M articles (depends on: pilot validation, estimated 4-5 hours with 4 workers)
- [ ] Verify vector store performance recall@10 on test queries (depends on: full ingestion)

### Temporal Basics

> **Prerequisite:** Phase 1 database schema and retrieval pipeline operational

**Schema & Migrations:**

- [ ] Create PostgreSQL migration 001 for temporal columns with tenant_id indexes (depends on: Phase 1 `documents` and `claims` tables, see Section 3.1)
- [ ] Add indexes for temporal queries with tenant_id (`idx_documents_temporal`, `idx_claims_temporal`)
- [ ] Update Parquet schema with `valid_from`, `valid_to`, `tenant_id` fields (see Section 6.2)
- [ ] Add temporal event schema: ClaimTemporalStateChanged (depends on: Phase 1 CloudEvents, see Section 3.1)
- [ ] Implement event publishing for temporal state changes (depends on: event schema)
- [ ] Backfill temporal metadata for existing documents (set defaults: published_at to present)
- [ ] Write migration rollback script (test on staging database first)

**As-Of Queries:**

- [ ] Add `as_of` parameter to POST `/api/v1/verify` endpoint (depends on: Phase 1 API structure)
- [ ] Implement temporal filtering in retrieval pipeline (depends on: temporal schema migration)
- [ ] Build two-stage FAISS retrieval: over-retrieve + filter (depends on: Phase 1 FAISS retrieval, see Section 3.3)
- [ ] Add temporal context to API response schema (`as_of`, `valid_from`, `valid_to` in evidence)
- [ ] Write unit tests for date parsing and filtering (depends on: temporal utilities)
- [ ] Add integration tests with sample temporal claims (depends on: API implementation, see Section 3.4 examples)

**Date Extraction:**

- [ ] Create `src/corpus/temporal.py` utilities module
- [ ] Implement regex patterns for common date formats (ISO 8601, MDY, DMY)
- [ ] Integrate spaCy DATE entity recognition (requires: `spacy` with `en_core_web_trf` model)
- [ ] Extract validity hints from text ("as of", "since", "from X to Y")
- [ ] Add date normalization and validation (handle ambiguous dates, timezone conversions)
- [ ] Write tests with diverse date formats (20+ test cases covering edge cases)

### Compound Reasoning

> **Prerequisite:** Phase 1 NLI verification working, temporal queries implemented

**Claim Decomposition:**

- [ ] Create `src/reasoning/decomposition.py` module
- [ ] Integrate spaCy dependency parser (requires: `spacy` with `en_core_web_trf` model)
- [ ] Implement conjunction splitting logic for AND/OR (depends on: spaCy parser)
- [ ] Add causal marker detection ("because", "since", "therefore", see Section 4.1)
- [ ] Implement comparative claim patterns (greater than, less than, see Section 4.1 Example 3)
- [ ] Add quantitative patterns (increased from X to Y, see Section 4.1 Example 1)
- [ ] Implement coreference resolution for subclaims (depends on: spaCy NLP pipeline)
- [ ] Test on compound claim dataset (HoVer, FEVEROUS samples, 100+ examples)
- [ ] Measure decomposition accuracy (manual eval on 100 claims, target: 80% correct splits)

**Numeric Reasoning:**

- [ ] Create `src/reasoning/numeric.py` module
- [ ] Define `NumericClaim` dataclass (see Section 4.2 schema)
- [ ] Implement number extraction with regex + NER (depends on: spaCy QUANTITY, MONEY, PERCENT entities)
- [ ] Build operator detection logic (text → symbolic, e.g., "greater than" → ">")
- [ ] Add unit normalization (million, billion, km, etc., consider `pint` library)
- [ ] Implement numeric comparison verification (see Section 4.2 example)
- [ ] Add arithmetic operations support (+, -, *, /, % for derived claims)
- [ ] Test on numeric fact-checking datasets (create custom test set if needed, 50+ examples)

**Multi-Step Verification:**

- [ ] Create `src/reasoning/multi_step.py` workflow orchestrator
- [ ] Integrate decomposition → individual verification loop (depends on: decomposition module, Phase 1 NLI)
- [ ] Load DeBERTa NLI model for entailment scoring (depends on: Phase 1 NLI setup)
- [ ] Implement verdict aggregation logic (AND, OR, CAUSAL, see Section 4.3)
- [ ] Build causal inference validator (rule-based placeholder, log for future ML-based approach)
- [ ] Add confidence propagation through reasoning chain (multiply confidence scores with decay factor)
- [ ] Write end-to-end tests for 2-3 step claims (use Section 4.4 examples)

**Reasoning Chain Storage:**

- [ ] Create PostgreSQL migration 003 for `reasoning_chains` and `reasoning_steps` with tenant_id and correlation_id (see Section 4.5)
- [ ] Implement ReasoningChainRepository interface (depends on: Phase 1 repository pattern)
- [ ] Create PostgresReasoningChainRepository implementation (depends on: repository interface)
- [ ] Create CloudSQLReasoningChainRepository stub for V2 (depends on: repository interface)
- [ ] Add reasoning event schemas: ReasoningStepCompleted, ReasoningChainGenerated (depends on: Phase 1 CloudEvents, see Section 4.5)
- [ ] Integrate event publishing in reasoning pipeline with correlation IDs (depends on: event schemas)
- [ ] Implement ORM models for reasoning chain (SQLAlchemy models in `src/db/models/`)
- [ ] Add storage logic in multi-step verification (save after each step)
- [ ] Build retrieval API endpoint GET `/api/v1/reasoning/{claim_id}` with correlation_id in response (see Section 4.5)
- [ ] Add human-readable reasoning explanations (template-based for each logic type)
- [ ] Write tests for chain storage and retrieval (depends on: ORM models, API endpoint)

### Cross-Cutting Concerns

> **Prerequisite:** All Phase 2 features implemented

- [ ] Update API documentation with Phase 2 endpoints (OpenAPI/Swagger, add examples from Section 3.4, 4.4)
- [ ] Add CLI documentation and usage examples (see Section 2.2 command examples)
- [ ] Write corpus ingestion playbook (runbook for ops: KILT ingestion procedure, troubleshooting)
- [ ] Set up monitoring for ingestion pipeline (Prometheus metrics: docs/sec, chunks/sec, errors)
- [ ] Add structured logging for all new modules (JSON logs with claim_id, document_id, step_index, correlation_id context)
- [ ] Performance benchmarking: ingest 10k docs, measure latency (depends on: ingestion pipeline, see Section 5.1)
- [ ] Performance benchmarking: compare FAISS vs Pinecone latency (depends on: vector store abstraction, see Section 5.2)
- [ ] Memory profiling for FAISS indexing on large corpus (depends on: KILT full ingestion, see Section 5.2)
- [ ] Update integration tests to cover temporal + compound scenarios (depends on: all features, use Section 3.4 and 4.4 examples)
- [ ] Test cloud migration paths with emulators (LocalStack S3, local Weaviate) (depends on: all abstractions, see Section 7)
- [ ] Document cloud configuration patterns (environment variables for FAISS vs Pinecone, local vs S3, etc.) (see Section 2.5, 7)

### Dependencies on Phase 1

> **Critical:** These Phase 1 components must be verified working before starting Phase 2

- [ ] Verify PostgreSQL `documents` and `claims` tables exist (run: `docker compose exec postgres psql -U truthgraph -d truthgraph -c "\dt"`)
- [ ] Confirm Redis Streams event processing is operational (test: publish/consume test message)
- [ ] Ensure FAISS infrastructure is set up (Python bindings working, test IndexFlatIP creation)
- [ ] Check FastAPI server is running and accessible (test: `curl http://localhost:8000/health`)
- [ ] Validate embedding model storage and loading (test: embed sample text, verify 384-dim output)
- [ ] Confirm Phase 1 NLI verification works (test: verify known claim, check verdict logic)
- [ ] Verify pgvector extension installed (run: `docker compose exec postgres psql -U truthgraph -d truthgraph -c "\dx"`)

**Reference:** See [Phase 1 TODO Checklist](phase_01_local_mvp.md#todo-checklist) for Phase 1 requirements

---

## 9. Common Pitfalls

### 9.1 Corpus Ingestion Pitfalls

#### Problem: Out of Disk Space During KILT Ingestion

- **Cause:** KILT corpus expands significantly (40GB → 500GB with indices)
- **Prevention:** Check available disk space before starting (`df -h`)
- **Solution:** Use external storage or clean up old indices before ingestion

#### Problem: Character Encoding Errors

- **Cause:** Non-UTF8 documents (PDFs with weird encodings, legacy HTML)
- **Prevention:** Add encoding detection with `chardet` library
- **Solution:** Implement fallback encodings (latin-1, cp1252) with logging

#### Problem: Duplicate Documents in Index

- **Cause:** Reingesting same documents without deduplication
- **Prevention:** Check document hash (SHA-256) before ingestion
- **Solution:** Add unique constraint on `documents.content_hash` column

#### Problem: Memory Exhaustion During Embedding

- **Cause:** Large batch sizes or long documents
- **Prevention:** Monitor memory usage, use batch_size=16-32 max
- **Solution:** Process in smaller batches, enable garbage collection between batches

### 9.2 Temporal Query Pitfalls

#### Problem: Temporal Filter Returns No Results

- **Cause:** Documents missing `valid_from`/`valid_to` metadata
- **Prevention:** Set default validity ranges (e.g., published_at to present)
- **Solution:** Backfill temporal metadata for existing documents

#### Problem: Ambiguous Date References in Claims

- **Cause:** Claims like "Is X true?" without temporal context
- **Prevention:** Prompt user for temporal context or default to present
- **Solution:** Use NER to extract dates from claim text, infer temporal scope

#### Problem: Conflicting Evidence from Different Time Periods

- **Cause:** Over-retrieval includes documents outside temporal bounds
- **Prevention:** Increase over-retrieval factor (10x → 20x) for better filtering
- **Solution:** Add confidence penalty for evidence near temporal boundaries

#### Problem: Timezone Issues

- **Cause:** Inconsistent timezone handling (UTC vs local)
- **Prevention:** Store all timestamps in UTC, convert on display
- **Solution:** Use `TIMESTAMP WITH TIME ZONE` in PostgreSQL

### 9.3 Compound Reasoning Pitfalls

#### Problem: Poor Decomposition Quality

- **Cause:** Complex sentence structures that spaCy can't parse
- **Prevention:** Test on diverse claim types (causal, comparative, numeric)
- **Solution:** Add manual fallback rules for common patterns, log failures for analysis

#### Problem: Cascading Errors in Multi-Step Verification

- **Cause:** One incorrect subclaim verification poisons entire chain
- **Prevention:** Use confidence thresholds per step (reject low-confidence subclaims)
- **Solution:** Implement partial verification (report confidence per subclaim)

#### Problem: Numeric Extraction Failures

- **Cause:** Numbers with units ("5 million", "3.2B"), percentages, ranges
- **Prevention:** Use comprehensive regex + NER (QUANTITY, MONEY, PERCENT)
- **Solution:** Add unit normalization library (e.g., `pint` for unit conversion)

#### Problem: False Causal Inference

- **Cause:** Claim has "since" but it's temporal, not causal
- **Prevention:** Distinguish "since" (temporal) from "because" (causal)
- **Solution:** Use semantic role labeling (SRL) to identify causal relationships

#### Problem: Infinite Loops in Decomposition

- **Cause:** Recursive decomposition without termination condition
- **Prevention:** Set max_depth=3 and max_subclaims=5
- **Solution:** Add cycle detection (track already-decomposed claims)

### 9.4 Vector Store Pitfalls

#### Problem: Index Corruption After Crash

- **Cause:** FAISS index written partially during power failure
- **Prevention:** Write to temp file, atomic rename on success
- **Solution:** Keep backup index, rebuild from Parquet if corrupted

#### Problem: Index-Document ID Mismatch

- **Cause:** FAISS index and Parquet files get out of sync
- **Prevention:** Store FAISS ID → chunk_id mapping in separate file
- **Solution:** Rebuild ID mapping from Parquet, verify consistency

#### Problem: Poor Recall with IVF Index

- **Cause:** Too few clusters (nlist) or low nprobe during search
- **Prevention:** Use nlist=sqrt(N) rule, set nprobe=10-20 for good recall
- **Solution:** Benchmark recall@10 on test set, tune nprobe parameter

#### Problem: Slow Index Building

- **Cause:** Training IVF index on large corpus is O(N*d)
- **Prevention:** Use random sample for training (100k vectors sufficient)
- **Solution:** Train on representative subset, add remaining vectors to index

### 9.5 Performance Pitfalls

#### Problem: High Latency on First Query

- **Cause:** Cold start (loading models, FAISS index into memory)
- **Prevention:** Implement warmup queries on service startup
- **Solution:** Keep services running, use health check endpoint to trigger load

#### Problem: Memory Leak in Worker

- **Cause:** PyTorch/Transformers caching tensors
- **Prevention:** Call `torch.cuda.empty_cache()` after batches
- **Solution:** Restart worker periodically (e.g., after 1000 claims processed)

#### Problem: PostgreSQL Query Slowdown

- **Cause:** Missing indexes or table bloat
- **Prevention:** Create indexes on temporal columns, foreign keys
- **Solution:** Run `VACUUM ANALYZE` weekly, monitor query performance

#### Problem: Redis Stream Backlog

- **Cause:** Worker can't keep up with claim submission rate
- **Prevention:** Monitor stream length (`XLEN claims-submitted`)
- **Solution:** Scale workers horizontally (run multiple worker containers)

### 9.6 Data Quality Pitfalls

#### Problem: Low-Quality Wikipedia Articles

- **Cause:** KILT includes stubs, disambiguation pages, lists
- **Prevention:** Filter articles by length (min 500 chars) and categories
- **Solution:** Implement quality score (length, references, categories)

#### Problem: Outdated Information

- **Cause:** Wikipedia snapshots are static, facts become stale
- **Prevention:** Store snapshot date, warn users about data age
- **Solution:** Implement incremental updates (fetch new revisions periodically)

#### Problem: Noisy Chunks

- **Cause:** Tables, infoboxes, navigation text included in chunks
- **Prevention:** Clean HTML before chunking (remove nav, footers, tables)
- **Solution:** Post-filter chunks (remove if mostly non-text content)

#### Problem: Biased Evidence

- **Cause:** Corpus skewed toward certain topics or viewpoints
- **Prevention:** Diversify sources (not just Wikipedia)
- **Solution:** Implement source diversity score, rank diverse evidence higher

### 9.7 Testing and Debugging Pitfalls

#### Problem: Flaky Tests

- **Cause:** Tests depend on model outputs (non-deterministic)
- **Prevention:** Mock ML models in unit tests, use fixed seeds
- **Solution:** Use integration tests with deterministic test data

#### Problem: Cannot Reproduce Bug

- **Cause:** Missing logging context (claim ID, subclaim details)
- **Prevention:** Use structured logging with claim_id, step_index
- **Solution:** Add DEBUG log level with full reasoning chain

#### Problem: Tests Pass Locally, Fail in CI

- **Cause:** Docker resource limits different (memory, CPU)
- **Prevention:** Test with production-like resource constraints
- **Solution:** Add CI-specific configuration (.env.ci with smaller batches)

---

## 10. Notes

- **Corpus ingestion is I/O bound:** Use multiprocessing for parallel file parsing
- **Vector store abstraction enables flexibility:** Start with FAISS for simplicity, switch to Pinecone/Weaviate when scaling needs arise
- **Repository pattern reduces migration risk:** All data access goes through interfaces, making local-to-cloud migration transparent to business logic
- **CloudEvents provide observability:** Event publishing enables distributed tracing, auditing, and cross-service coordination
- **Temporal queries need optimization:** Consider time-based index partitioning if latency >100ms; Pinecone's native filtering helps here
- **Numeric reasoning is brittle:** Start with exact matches, iterate toward fuzzy/range matching
- **Decomposition accuracy is critical:** Allocate time for manual evaluation and pattern refinement
- **KILT snapshot is large:** Verify disk space (compressed ≈ 40GB, uncompressed + indices ≈ 200GB for local); S3 storage eliminates local disk constraints
- **Test cloud paths early:** Use LocalStack and local Weaviate to validate cloud migration paths before deploying to production
- **Correlation IDs are essential:** Enable tracing multi-hop reasoning across distributed services, critical for debugging complex reasoning chains

---

**Next Phase:** Phase 3 will focus on multimodal verification (images, OCR, reverse search) and explainability (provenance graphs, JSON-LD export).
