# Compound / Chained Fact Reasoning

## Core Idea

Compound reasoning verifies claims requiring multiple premises or logical inference. It decomposes a claim into subclaims, validates each, and synthesizes a final verdict through reasoning.

Example:
> "Since CO₂ levels increased and ocean pH decreased, acidification worsened."

### Process

1. Decompose into subclaims (CO₂ ↑, pH ↓)
2. Verify each subclaim individually
3. Combine using logical or numerical inference
4. Produce a reasoning proof graph

## Key Features

- Multi-premise and logical reasoning (AND, OR, implication)
- Quantitative reasoning (arithmetic, units, ratios)
- Premise discovery via semantic search
- Scientific and policy claim compatibility

## Architecture

- **Claim Parser:** converts natural language to logical form
- **Evidence Aggregator:** retrieves verified subclaims
- **Logic Engine:** symbolic (Prolog, DeepProbLog) or differentiable reasoning
- **Verifier:** NLI-based validation between premises and conclusion

## Datasets & References

- HoVer, FEVEROUS, ComplexFact (multi-hop reasoning)
- Numerical Fact Checking (NumClaim), EntailmentBank, SciFact
- Tools: DeepProbLog, PyKEEN, AllenNLP NLI

## Unique Value

Enables explainable verification for complex, multi-hop, and scientific claims. Bridges fact-checking with data-driven inference and policy reasoning, transforming AFC into structured, compositional truth synthesis.
