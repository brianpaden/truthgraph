# Core Shared Capabilities & Architecture

## Purpose

A unifying spine that all fact-checking modules plug into: parsing, retrieval, reasoning, provenance, temporal handling, and publishing. Designed for modular research and production hardening.

## System Principles

- **Evidence-first**: all conclusions must cite source spans.
- **Time-aware by default**: every datum/version carries a validity window.
- **Explainable**: store reasoning artifacts, not just verdicts.
- **Composable**: event-driven bus with well-specified contracts.
- **Standards-aligned**: PROV-O, ClaimReview, OWL-Time, JSON-LD/Nanopubs.

## High-Level Topology

- **Ingress Adapters**: text, URLs, PDFs, images, audio/video.
- **Fact Reasoning Bus (FRB)**: pub/sub events connecting services.
- **Shared Services**:
  - Claim Parsing & Canonicalization
  - Hybrid Retrieval (OpenSearch + FAISS)
  - Temporal Engine (indexing + filters)
  - Reasoning (symbolic + NLI)
  - Provenance/Graph Store
  - Evaluation & Telemetry
  - Publishing Gateway (ClaimReview/API)

## Shared Data Contracts (JSONL)

### `ClaimSubmitted`

```json
{
  "claim_id":"c_...",
  "as_of":"2025-10-22",
  "input":{"type":"text","content":"..."},
  "language":"en",
  "ingest_meta":{"source_url":null}
}
```

### `EvidenceCandidates`

```json
{
  "claim_id":"c_...",
  "candidates":[{"doc_id":"wiki:Eiffel_Tower#3","text":"...","url":"...","published_at":"2024-12-01"}],
  "retrieval_meta":{"bm25":10,"dense":128,"filters":{"before":"2025-10-22"}}
}
```

### `VerificationResult`

```json
{
  "claim_id":"c_...",
  "verdict":"SUPPORTED",
  "confidence":0.87,
  "rationales":[{"doc_id":"wiki:...","spans":[[120,165]]}],
  "reasoning_chain":[{"type":"numeric_compare","premises":[{"doc_id":"wiki:...","value":330}],"conclusion":true}],
  "temporal":{"valid_from":"2023-12-01","valid_to":null}
}
```

---

## Core Services

### 1. Claim Parsing & Canonicalization

- Sentence segmentation, check-worthiness classification.
- Atomic claim splitting into (subject, predicate, object, qualifiers).
- Entity linking to Wikidata; normalization of units, dates, and names.
- **APIs**: `/parse`, `/canonicalize`, `/atoms`.

### 2. Hybrid Retrieval Layer

- **Sparse**: OpenSearch (BM25/LM-based), fielded queries with filters.
- **Dense**: FAISS (HNSW/IVF) with Contriever-class encoders.
- **Rerank**: cross-encoder; return top-k passages + metadata.
- **Temporal filters**: `published_at <= as_of` and source-tier constraints.
- **Data**: Parquet shards + segment metadata; nightly snapshotting.

### 3. Temporal Engine

- Versioned corpus snapshots (KILT-style) and delta updates.
- Temporal KG embeddings (HyTE/T-TransE) for time-aware linking.
- **APIs**: `/filter_by_time`, `/asof`, `/validity`.

### 4. Reasoning Layer (Symbolic + NLI)

- Symbolic operators: `>, <, =, sum, ratio, delta, unit_convert, before/after`.
- Rule templates for comparisons, counts, thresholds, simple causal patterns.
- NLI verifier to check entailment/contradiction vs selected rationales.
- **APIs**: `/prove`, `/evaluate_rule`, `/nli`.

### 5. Provenance & Graph Store

- RDF/Neo4j with **PROV-O** relations: `wasDerivedFrom`, `used`, `wasGeneratedBy`.
- Nodes: `Claim`, `Premise`, `Evidence`, `Verdict`, `Agent`, `Activity`.
- Edges carry timestamps, confidence, and document anchors.
- **APIs**: `/trace/{claim_id}`, SPARQL, GraphQL.

### 6. Evaluation & Telemetry

- Retrieval (Recall\@k, MRR), Verification (Macro-F1, FEVER score), Faithfulness (FActScore), Editor disagreement.
- Prometheus metrics; dashboards (Grafana); audit logs (append-only).

### 7. Publishing Gateway

- ClaimReview JSON-LD generator; sitemaps for discoverability.
- Web UI: verdict + expandable reasoning chain with citations & dates.
- Webhooks for partner ingestion; Nanopublication export.

## Security & Policy Guardrails

- Source allowlists/denylists; duplicate evidence detection.
- PII scrubbing in logs; redaction pipeline.
- Conformal prediction for calibrated abstain thresholds.
- Rate limits and per-claim complexity caps.

## Storage Layout

- **Object Store**: raw docs, embeddings, OCR outputs (versioned paths).
- **Search**: OpenSearch clusters (hot/warm tiers), FAISS indices per snapshot.
- **Graph**: RDF/Neo4j with daily backups and snapshot tags.
- **Warehouse**: Parquet/Delta Lake for analytics and offline evals.

## Extensibility Hooks

- Plugin ABI for new retrievers, reasoners, or modalities.
- Event enrichers on the FRB (e.g., language detection, toxicity flags).
- Policy modules (election, health) with domain-specific rules.

## Interop & Standards Map

- **Provenance**: PROV-O
- **Temporal**: OWL-Time, ISO 8601 intervals
- **Publishing**: ClaimReview, Report schema.org, Nanopubs
- **Data Exchange**: JSONL (internal), JSON-LD (external)

## Rollout Plan

1. **MVP Spine**: FRB, Retrieval, Verifier, Provenance store, ClaimReview export.
2. **Temporalization**: snapshotting + as-of filters + validity intervals.
3. **Chaining**: symbolic reasoner + proof object UI.
4. **Multimodal**: OCR + chart parser + cross-modal checks.
5. **Federation**: Open Provenance Graph API with partner sync.

## Open Questions

- Confidence aggregation across heterogeneous premises.
- Best practice for storing span anchors across evolving document versions.
- Crowdsourced feedback integration without provenance contamination.
