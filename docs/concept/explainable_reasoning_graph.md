# Explainable Reasoning Graph

## Core Idea

A reasoning graph transforms fact-checking outputs from binary labels into auditable chains of reasoning. Each claim is represented as a graph:

```text
Claim: "The Eiffel Tower is taller than Big Ben."
 ├── Premise A: "Eiffel Tower height = 330m" (Wikipedia)
 ├── Premise B: "Big Ben height = 96m" (Britannica)
 └── Comparison: 330 > 96 → Supported ✅
```

Each node includes evidence sources, confidence levels, and validity time ranges.

## Key Features

- Transparent, human-auditable reasoning chains
- Logical and numeric reasoning support
- Machine-readable provenance metadata (PROV-O, ClaimReview-compatible)
- GraphQL/SPARQL API access for exploration

## Architecture

- **Graph Layer:** Neo4j or RDF triple store (PROV-O ontology)
- **Reasoning Layer:** symbolic + neural hybrid
- **Query Layer:** SPARQL or GraphQL endpoints

## Datasets & References

- FEVER, FEVEROUS, HoVer, MultiRC, HotpotQA (reasoning traces)
- PROV-O, W3C Open Provenance Model for interoperability

## Unique Value

Turns fact-checking into explainable reasoning. Enables users to visualize and audit how conclusions are derived, creating transparency and trust in automated verification.
