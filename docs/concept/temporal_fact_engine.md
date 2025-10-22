# Temporal Fact Engine

## Core Idea

Facts evolve over time. The Temporal Fact Engine enables fact-checking systems to evaluate claims relative to a point in time. It answers: *Was this true when it was said?*

Example:
> "Angela Merkel is the Chancellor of Germany."  
> ✅ True (2005–2021) | ❌ False (2025)

## Key Features

- Time-bounded fact validity intervals `{start_date, end_date}`
- "As of" queries (`/check?as_of=YYYY-MM-DD`)
- Historical truth simulation and replay
- Temporal consistency and fact drift analysis

## Architecture

- **Temporal Knowledge Graph:** HyTE, T-TransE, or TeRo embeddings
- **Versioned Fact Store:** immutable, date-snapshotted corpora
- **Temporal Retrieval Layer:** FAISS/OpenSearch with date filters
- **Recency Calibration:** time-weighted confidence metrics

## Datasets & References

- Wikidata5m-T, T-REx, TimeQA (temporal QA)
- KILT (versioned Wikipedia)
- OWL-Time, ISO 8601 intervals for date encoding
- ClaimReview’s `datePublished` and `itemReviewed.datePublished`

## Unique Value

Solves “once-true but outdated” misinformation and enables historical fact-checking. Supports longitudinal truth tracking and temporal analysis of evolving claims.
