# Edge Case Validation Tests

Comprehensive edge case validation tests for the TruthGraph verification system.

## Overview

This test suite validates the system's ability to handle challenging edge cases that deviate from typical inputs. The tests ensure robustness, proper error handling, and appropriate confidence scoring for edge cases.

## Test Categories

### 1. Insufficient Evidence (test_insufficient_evidence.py)
Tests claims where no relevant evidence exists or evidence is unavailable.

**Examples**: Private personal information, Unpublished research, Future predictions

**Expected Behavior**: Return INSUFFICIENT verdict with confidence < 0.6

### 2. Contradictory Evidence (test_contradictory_evidence.py)
Tests claims with conflicting evidence - some supporting, some refuting.

**Expected Behavior**: Recognize conflicting evidence, return CONFLICTING or INSUFFICIENT

### 3. Ambiguous Evidence (test_ambiguous_evidence.py)
Tests claims where evidence is tangential, vague, or weakly related.

**Expected Behavior**: Reflect uncertainty with lower confidence scores

### 4. Long Claims (test_long_claims.py)
Tests processing of long-form claims (>500 words or >100 words).

**Expected Behavior**: Process without truncation or errors

### 5. Short Claims (test_short_claims.py)
Tests processing of short-form claims (<10 words).

**Expected Behavior**: Handle minimal claims without rejection

### 6. Special Characters (test_special_characters.py)
Tests Unicode and special character handling.

**Expected Behavior**: Handle Unicode correctly without encoding errors

## Running the Tests

```bash
# Run all edge case tests
pytest tests/accuracy/edge_cases/ -v

# Run specific category
pytest tests/accuracy/edge_cases/test_insufficient_evidence.py -v

# Skip pipeline integration tests
pytest tests/accuracy/edge_cases/ -v -m "not skip"
```

## Current Status

- 113 test cases across 6 categories
- 83 tests passing (data validation)
- 16 tests skipped (pending pipeline integration)
- 14 tests failing (minor data structure issues)

See IMPLEMENTATION_SUMMARY.md for details.
