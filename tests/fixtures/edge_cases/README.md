# Edge Case Corpus for TruthGraph v0 Phase 2

## Overview

The Edge Case Corpus provides specialized test data for validating the TruthGraph fact-checking system's robustness against challenging scenarios. This comprehensive collection includes 7 categories of edge cases with 34 total test claims covering diverse failure modes, boundary conditions, and adversarial scenarios.

**Status**: Complete - 34 test claims across 7 categories with full documentation and pytest fixtures.

## Edge Case Categories

### 1. Insufficient Evidence (5 claims)

Claims where no relevant evidence exists, claims too obscure to verify, or claims about private/non-public information.

**Expected System Behavior**: Return `INSUFFICIENT` verdict

**Examples**:
- Claims about private individuals' personal preferences
- Unpublished or proprietary research claims
- Future predictions with no present evidence
- Unknowable information claims
- Internal mental states

**Test Data**: `insufficient_evidence.json`

**Key Insight**: System should gracefully handle missing evidence without speculation.

---

### 2. Contradictory Evidence (4 claims)

Claims with equal supporting and refuting evidence, direct source conflicts, or competing interpretations of the same data.

**Expected System Behavior**: Return `CONFLICTING` verdict or manage evidence conflicts appropriately

**Examples**:
- Coffee consumption health effects (both beneficial and harmful evidence)
- Remote work productivity impact (conflicting study results)
- AI job creation predictions (competing expert forecasts)
- Historical interpretation debates (Napoleon's impact assessment)

**Test Data**: `contradictory_evidence.json`

**Key Insight**: System should recognize legitimate disagreement while maintaining confidence thresholds.

---

### 3. Ambiguous/Neutral Evidence (5 claims)

Claims where evidence is tangentially related, has unclear relevance, or requires significant inference to connect to the claim.

**Expected System Behavior**: Return `INSUFFICIENT` or `AMBIGUOUS` verdict recognizing weak relevance

**Examples**:
- Correlation vs. causation (social media depression correlation)
- Alternative explanations (color performance psychology)
- Inconclusive evidence (full moon sleep effects)
- Replication crises (Mozart Effect disputed studies)
- Scope limitation issues (positive thinking cures)

**Test Data**: `ambiguous_evidence.json`

**Key Insight**: System should distinguish correlation from causation and recognize alternative hypotheses.

---

### 4. Long-Form Claims (5 claims)

Paragraph-length claims exceeding 500 words, containing multiple sub-claims, or representing complex compound statements.

**Expected System Behavior**: Process without truncation or errors, ideally decompose for individual verification

**Examples**:
- Climate change (238 words, 8 sub-claims): Temperature, evidence, effects, implications
- AI history (234 words, 6 sub-claims): Founding, progress, revolution, challenges
- COVID-19 pathophysiology (278 words, 12 sub-claims): Mechanism, complications, vaccination, public health
- Quantum mechanics (256 words, 10 sub-claims): Principles, mathematics, experiments, interpretations
- Industrial Revolution (271 words, 11 sub-claims): Origins, impacts, disruptions, environmental effects

**Test Data**: `long_claims.json`

**Key Insight**: System should handle complex multi-premise claims without performance degradation.

---

### 5. Short Claims (5 claims)

Minimal context claims with less than 10 words, including single-word claims and very terse statements.

**Expected System Behavior**: Process minimal context and may return `INSUFFICIENT` or leverage knowledge base

**Examples**:
- "Water boils at 100C." (5 words)
- "Paris capital France." (3 words)
- "Gravity exists." (2 words)
- "Ice melts." (2 words)
- "Oxygen." (1 word - non-propositional)

**Test Data**: `short_claims.json`

**Key Insight**: System should recognize claim structure limits and may require baseline knowledge for verification.

---

### 6. Special Characters & Multilingual (5 claims)

Claims containing special characters (@#$%^&*), emojis, non-Latin scripts (Chinese, Arabic, Russian), and mixed-language content.

**Expected System Behavior**: Handle Unicode correctly without encoding errors, process non-Latin scripts

**Examples**:
- Social media conventions: "@username", "#hashtag", "&", multiple punctuation
- Mixed English-Chinese: "COVID-19疫苗 (vaccine)" with parallel translations
- Arabic-English: "الاحتباس الحراري" with right-to-left text handling
- Russian-English: "Изменение климата" with Cyrillic characters and chemical notation (CO₂)
- Emoji & symbols: "🐚 & 🐠" with mathematical notation (↓, →)

**Test Data**: `special_characters.json`

**Key Insight**: System should maintain robustness across Unicode, diverse scripts, and emoji handling.

---

### 7. Adversarial Examples (5 claims)

Near-false claims (technically true but misleading), subtle logical fallacies, and statements designed to confuse NLI models.

**Expected System Behavior**: Maintain robustness against misleading framing while recognizing technical truth/falsehood

**Examples**:
- Cherry-picked statistics: "More shark deaths than vaccine deaths" (technically true, extremely misleading)
- Selection bias: "99% parachute survival rate" (true by definition, causally confused)
- Temporal cherry-picking: "Stock markets rise 75% of the time" (true long-term, misleading for short-term)
- Missing baseline: "Drug X reduced symptoms 25%" (true but incomparable without placebo baseline)
- Correlation-causation confusion: "Coffee consumption → wealth" (correlation without causation)

**Test Data**: `adversarial_examples.json`

**Key Insight**: System should recognize misleading frames while distinguishing from factually false claims.

---

## Data Structure

Each edge case category follows this JSON structure:

```json
{
  "category": "category_name",
  "description": "Detailed description of edge case category",
  "expected_behavior": "What system should do with these claims",
  "claims": [
    {
      "id": "edge_category_###",
      "text": "The claim text",
      "expected_verdict": "SUPPORTED|REFUTED|INSUFFICIENT|CONFLICTING|AMBIGUOUS",
      "edge_case_type": "category_name",
      "reason": "Why this is an edge case",
      "expected_behavior": "Expected system behavior for this specific claim",
      "evidence_ids": ["ev_category_###"],
      "metadata": {
        "challenge": "What makes this challenging",
        "test_purpose": "What aspect we're testing",
        "...": "Category-specific metadata"
      }
    }
  ],
  "evidence": [
    {
      "id": "ev_category_###",
      "text": "Evidence text",
      "source": "Source attribution",
      "reliability": "high|medium|low",
      "...": "Additional evidence properties"
    }
  ]
}
```

## Pytest Fixtures

The `conftest.py` module provides session-scoped fixtures for each edge case category:

```python
# Individual category fixtures
@pytest.fixture(scope="session")
def edge_case_insufficient_evidence() -> Dict[str, Any]:
    """Load insufficient evidence edge cases."""

@pytest.fixture(scope="session")
def edge_case_contradictory() -> Dict[str, Any]:
    """Load contradictory evidence edge cases."""

@pytest.fixture(scope="session")
def edge_case_ambiguous() -> Dict[str, Any]:
    """Load ambiguous evidence edge cases."""

@pytest.fixture(scope="session")
def edge_case_long_claims() -> Dict[str, Any]:
    """Load long-form claims."""

@pytest.fixture(scope="session")
def edge_case_short_claims() -> Dict[str, Any]:
    """Load short claims."""

@pytest.fixture(scope="session")
def edge_case_special_characters() -> Dict[str, Any]:
    """Load special characters and multilingual claims."""

@pytest.fixture(scope="session")
def edge_case_adversarial() -> Dict[str, Any]:
    """Load adversarial examples."""

# Combined fixtures
@pytest.fixture(scope="session")
def all_edge_cases() -> Dict[str, Dict[str, Any]]:
    """Load all categories combined."""

# Factory fixtures
@pytest.fixture
def get_edge_case_by_id(all_edge_cases) -> Callable:
    """Get specific claim by ID."""

@pytest.fixture
def get_edge_case_claims_by_category(all_edge_cases) -> Callable:
    """Get all claims for a category."""

@pytest.fixture
def get_edge_case_evidence(all_edge_cases) -> Callable:
    """Get evidence for a category."""

@pytest.fixture
def edge_case_statistics(all_edge_cases) -> Dict[str, Any]:
    """Get statistics about all edge cases."""
```

## Usage Examples

### Loading Individual Categories

```python
def test_insufficient_evidence(edge_case_insufficient_evidence):
    """Test system handling of insufficient evidence."""
    claims = edge_case_insufficient_evidence["claims"]

    for claim in claims:
        # Verify system returns INSUFFICIENT verdict
        verdict = verify_claim(claim["text"])
        assert verdict == claim["expected_verdict"]
```

### Using Combined Fixtures

```python
def test_all_edge_cases(all_edge_cases):
    """Test across all edge case categories."""
    for category, data in all_edge_cases.items():
        claims = data["claims"]
        for claim in claims:
            # Test each claim
            result = process_claim(claim)
            assert result.verdict == claim["expected_verdict"]
```

### Using Factory Fixtures

```python
def test_specific_claim(get_edge_case_by_id):
    """Test a specific claim by ID."""
    claim, category = get_edge_case_by_id("edge_insuf_001")
    print(f"Testing {claim['text']} from {category}")
```

### Accessing Statistics

```python
def test_coverage(edge_case_statistics):
    """Verify edge case coverage."""
    stats = edge_case_statistics
    print(f"Total claims: {stats['total_claims']}")
    print(f"Categories: {stats['total_categories']}")

    for category, info in stats['categories'].items():
        print(f"{category}: {info['claim_count']} claims")
```

## Validation Tests

The `test_edge_cases.py` module contains comprehensive validation tests organized into test classes:

### TestEdgeCaseStructure
- JSON file existence and validity
- Python syntax validation
- File format compliance

### TestEdgeCaseContent
- Required field presence
- Category label consistency
- Claim and evidence completeness
- Reference validity
- Verdict validity
- Metadata presence

### TestEdgeCaseSpecifications
- Short claims word count verification
- Long claims word count verification
- Unicode special character verification
- Evidence pair requirements
- Category-specific requirements

### TestEdgeCaseUsage
- Fixture loadability
- Factory fixture functionality
- Statistics accuracy
- Unicode handling

### TestEdgeCaseDocumentation
- Description quality
- Behavior documentation
- Individual claim documentation

**Run Tests**:
```bash
pytest tests/fixtures/edge_cases/test_edge_cases.py -v
```

## Statistics

| Category | Claims | Evidence | Word Range | Purpose |
|----------|--------|----------|------------|---------|
| Insufficient Evidence | 5 | 0 | Varies | Verify INSUFFICIENT handling |
| Contradictory Evidence | 4 | 8 | Varies | Verify conflict resolution |
| Ambiguous Evidence | 5 | 10 | Varies | Verify weak relevance handling |
| Long Claims | 5 | 15 | 150-280 words | Verify complex claim processing |
| Short Claims | 5 | 4 | 1-5 words | Verify minimal context handling |
| Special Characters | 5 | 5 | Varies | Verify Unicode robustness |
| Adversarial Examples | 5 | 10 | Varies | Verify against misleading frames |
| **TOTAL** | **34** | **52** | — | — |

## Integration with Existing Tests

Edge cases integrate seamlessly with existing test infrastructure:

1. **Compatible Format**: Matches existing fixture format from Feature 1.1
2. **Pytest Native**: Uses standard pytest fixtures and parametrization
3. **Separate Namespace**: `edge_*` prefix prevents ID collisions
4. **Modular Loading**: Load individual categories or combined
5. **Reference Compatible**: Evidence references use `evidence_ids` like main fixtures

## Expected Behaviors Summary

| Category | Expected Verdict | Why |
|----------|------------------|-----|
| Insufficient Evidence | `INSUFFICIENT` | No evidence available |
| Contradictory | `CONFLICTING` or confidence-balanced | Multiple valid perspectives |
| Ambiguous | `INSUFFICIENT` or `AMBIGUOUS` | Evidence too weak/tangential |
| Long Claims | Variable per claim | Test decomposition and processing |
| Short Claims | Variable per claim | Test minimal context inference |
| Special Characters | Variable per claim | Ensure encoding robustness |
| Adversarial | Technically correct verdict despite misleading frame | Resist adversarial attacks |

## Key Testing Insights

### 1. Insufficient Evidence
- System must not speculate or confabulate when evidence is unavailable
- Should explicitly return INSUFFICIENT rather than guessing
- Should handle unknowable claims gracefully

### 2. Contradictory Evidence
- System should recognize legitimate disagreement in evidence
- Confidence scores should reflect conflicting information
- Should not arbitrarily pick one side without justification

### 3. Ambiguous Evidence
- Correlation should not imply causation
- Alternative explanations should be considered
- Evidence relevance strength matters, not just presence

### 4. Long Claims
- System should not truncate or lose information
- Multiple sub-claims should be properly integrated
- Complex logical structure should be maintained

### 5. Short Claims
- Minimal context requires baseline knowledge
- Grammar and punctuation may be non-standard
- Some claims may be non-propositional

### 6. Special Characters & Multilingual
- Unicode handling must be robust
- Right-to-left text (Arabic) requires special handling
- Emoji and special symbols should not crash system
- Mixed-language claims need proper tokenization

### 7. Adversarial Examples
- Technically true claims can be misleading
- Cherry-picked statistics need context awareness
- Causal framing requires verification
- Selection bias distorts statistical claims

## Maintenance and Extension

### Adding New Edge Cases

1. **Create JSON file**: Name following pattern `{category_name}.json`
2. **Use unique IDs**: Prefix with `edge_{category_}###`
3. **Document thoroughly**: Include reason, expected_behavior, metadata
4. **Update conftest**: Add fixture if new category
5. **Add tests**: Update test_edge_cases.py with new category tests
6. **Update this README**: Document new category

### Updating Existing Cases

- Maintain ID consistency (don't rename)
- Update evidence as new sources emerge
- Adjust expected verdicts if evidence changes
- Document changes in version history

## References

- **Feature 1.1**: Standard Test Fixtures - base format reference
- **Feature 1.2**: FEVER Integration - evidence structure reference
- **Feature 1.3**: Real-World Claims - realistic example reference

## See Also

- `/tests/fixtures/conftest.py` - Main fixture loading patterns
- `/tests/fixtures/test_claims.json` - Standard fixture format
- `/tests/fixtures/fever/` - FEVER dataset integration
- `/tests/accuracy/` - Accuracy testing with real-world examples

---

**Feature**: 1.4 Edge Case Corpus
**Status**: Complete
**Created**: 2025-10-29
**Coverage**: 7 categories, 34 claims, 52 evidence items
