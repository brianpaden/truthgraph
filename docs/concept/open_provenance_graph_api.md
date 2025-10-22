# Open Provenance Graph API

## Core Idea

An open, auditable, and interoperable API for sharing machine-verifiable fact-check data. It exposes verified claims, evidence, reasoning chains, and metadata as a queryable knowledge graph.

## Key Features

- Public, read-only API for verified claims and evidence
- Standardized schema using PROV-O and ClaimReview JSON-LD
- Includes confidence scores, timestamps, sources, and reasoning traces
- Enables synchronization across organizations and domains

## Architecture

- **Core Storage:** RDF triple store (GraphDB, Blazegraph) or Neo4j
- **Schema:** PROV-O + ClaimReview + Nanopublications + OpenFactGraph
- **API Layer:** GraphQL/SPARQL endpoints for /check, /trace, /asof queries
- **Versioning:** immutable claim records, Git-like provenance history

## Datasets & References

- W3C PROV-O, ClaimReview/Report schema.org, Nanopublications
- Open Fact Graph (2023), Wikidata provenance modeling

## Unique Value

Creates a shared backbone for verifiable truth infrastructure. Encourages federated fact-checking networks with transparency, reproducibility, and interoperability. Empowers civic tech, journalism, and research through open, standardized truth graphs.
