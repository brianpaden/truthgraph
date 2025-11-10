# API Test Suite - Issues Quick Reference

**For:** Debugger Agent
**File:** `tests/test_api_ml_endpoints.py`
**Total Tests:** 29

---

## Critical Issues (Blocking)

### 1. Database Cleanup Performance (Line 43)
**Problem:**
```python
Base.metadata.drop_all(bind=engine)  # SLOW! Drops ALL tables after every test
```

**Why It's Bad:**
- Drops all database tables, not just test data
- Rebuilds indexes on every test
- With 29 tests, this is ~29 full database resets
- Causes timeouts in CI/CD environments

**Expected Behavior When Running:**
- Tests will be SLOW (30-60+ seconds for full suite)
- May timeout if set to less than 60 seconds

**Fix Needed:**
Replace with transaction rollback approach

---

### 2. Fixture Scope Issue (Line 25)
**Problem:**
```python
@pytest.fixture(scope="module")  # WRONG: Should be function
def client():
    return TestClient(app)
```

**Why It's Bad:**
- Reuses same client across ALL 29 tests
- State from test #1 can affect test #2
- Not proper test isolation

**Expected Behavior:**
- Tests may fail/pass inconsistently based on order
- Hard to debug because issues are order-dependent

**Fix Needed:**
Change scope to `function`

---

### 3. Database Fixture Inconsistency
**Problem:**
- Lines 155-171: Tests call fixtures but setup differs
- First 3 search tests: `(self, client, db_session, sample_evidence)`
- Last 3 search tests: `(self, client)` - NO db_session parameter!

**Example Issue:**
```python
# Line 155 - HAS sample_evidence (populates DB)
def test_search_vector_mode(self, client, db_session, sample_evidence):

# Line 209 - NO sample_evidence (empty DB)
def test_search_keyword_mode_not_implemented(self, client):
```

**Expected Behavior:**
- Tests 1-3: Find results (database populated)
- Tests 4-6: Find NO results (database empty) OR fail (fixture unavailable)

**Why This Matters:**
- Test 4-6 pass because they don't care about results
- Tests are not truly validating functionality

---

## High Priority Issues

### 4. No Mocking of ML Services
**Location:** All tests use real services
**Impact:**
- Tests are SLOW (loading sentence-transformers and deberta models)
- Tests are FRAGILE (depend on model downloads, GPU availability)
- Not unit tests, they are integration tests

**Expected Behavior:**
- Each embedding test loads the embedding model (slow)
- Each NLI test loads the NLI model (slow)
- Tests may fail if models aren't cached

---

### 5. Weak Assertions
**Examples:**

```python
# Line 166 - Too weak!
assert data["count"] >= 0  # This passes even if count is 0!

# Should be:
assert data["count"] > 0  # Validate actual results returned
```

```python
# Line 196 - Doesn't validate threshold worked
def test_search_with_similarity_threshold(self, client, db_session, sample_evidence):
    # ... runs search with min_similarity=0.9
    assert data["count"] >= 0  # Doesn't check if threshold actually applied!
```

---

### 6. Manual Database Creation (Line 411-434)
**Problem:**
```python
def test_get_verdict_existing(self, client, db_session):
    # MANUALLY creates objects instead of calling API
    claim = Claim(text="Test claim")
    db_session.add(claim)

    verification = VerificationResult(...)
    db_session.add(verification)  # Creates verdict manually!
```

**Why This Is Bad:**
- Doesn't test actual `/verify` endpoint
- Verdict is created by test, not by API
- Breaks contract: verdict should come from verify pipeline
- Doesn't validate verification result computation

**Better Approach:**
```python
# Call /verify endpoint
response = client.post("/api/v1/verify", json={"claim": "..."})
claim_id = response.json()["claim_id"]

# Then retrieve verdict
response = client.get(f"/api/v1/verdict/{claim_id}")
assert response.status_code == 200
```

---

## Tests Requiring Fixture Fixes

### Search Endpoint Tests (Lines 155-207)

| Test | Fixture | Issue |
|------|---------|-------|
| `test_search_vector_mode` | ✓ sample_evidence | Works IF fixture runs |
| `test_search_with_similarity_threshold` | ✓ sample_evidence | Works IF fixture runs |
| `test_search_with_limit` | ✓ sample_evidence | Works IF fixture runs |
| `test_search_keyword_mode_not_implemented` | ✗ MISSING | No setup |
| `test_search_empty_query_error` | ✗ MISSING | No setup |
| `test_search_invalid_limit` | ✗ MISSING | No setup |

**Issue:** Inconsistent fixture usage means some tests have data, others don't

---

### Verify Endpoint Tests (Lines 325-403)

| Test | Issue |
|------|-------|
| `test_verify_claim_with_evidence` | Depends on `sample_evidence` fixture - database must be populated |
| `test_verify_claim_no_evidence` | Works - tests no evidence scenario |
| `test_verify_with_custom_threshold` | Has `sample_evidence` but doesn't validate threshold actually worked |
| `test_verify_empty_claim_error` | Works - validation test |
| `test_verify_invalid_max_evidence` | Works - validation test |

**Issue:** Threshold test doesn't assert the threshold was applied

---

## Assertions That Need Strengthening

### Current (Weak)
```python
assert response.status_code == 200
assert "count" in data
assert data["count"] >= 0  # Passes even if 0!
```

### Better (Strong)
```python
assert response.status_code == 200
assert "count" in data
assert data["count"] == expected_count  # Specific value
assert len(data["results"]) == data["count"]  # Consistency
assert all(result["similarity"] >= min_similarity for result in data["results"])
```

---

## Test Execution Timing

**Expected Duration:**
- With proper cleanup: 30-60 seconds
- With drop_all() (current): 45-90 seconds
- With mocking: 5-10 seconds

**Current Status:**
- Very slow due to drop_all() and no mocking
- May timeout in CI/CD if limit < 60 seconds

---

## What Tests Actually Do

### TestEmbedEndpoint (Lines 90-147)
- **Purpose:** Test `/api/v1/embed` endpoint
- **Setup:** None (no fixtures needed)
- **Behavior:** All 5 tests pass (well-structured)
- **Issue:** Loads real embedding model (SLOW)

### TestSearchEndpoint (Lines 152-229)
- **Purpose:** Test `/api/v1/search` endpoint
- **Setup:** Inconsistent (some use sample_evidence, some don't)
- **Behavior:** Weak assertions don't validate functionality
- **Issue:** Tests pass but don't prove search works correctly

### TestNLIEndpoint (Lines 234-285)
- **Purpose:** Test `/api/v1/nli` endpoint
- **Setup:** None needed
- **Behavior:** All 4 tests pass
- **Issue:** Loads real NLI model (SLOW), missing neutral test case

### TestVerifyEndpoint (Lines 325-403)
- **Purpose:** Test `/api/v1/verify` endpoint
- **Setup:** Some tests use sample_evidence
- **Behavior:** Tests for different scenarios (with evidence, no evidence, threshold)
- **Issue:** Manual DB creation, fixture inconsistency

### TestVerdictEndpoint (Lines 408-466)
- **Purpose:** Test `/api/v1/verdict` endpoint
- **Setup:** Manual DB creation (should use /verify)
- **Behavior:** 3 test cases
- **Issue:** Doesn't test actual verification flow

### TestHealthEndpoint (Lines 471-490)
- **Purpose:** Test `/health` endpoint
- **Setup:** None
- **Behavior:** Single test validates response structure
- **Issue:** None identified

### TestRootEndpoint (Lines 495-508)
- **Purpose:** Test `/` root endpoint
- **Setup:** None
- **Behavior:** Single test validates response structure
- **Issue:** None identified

### TestMiddleware (Lines 513-539)
- **Purpose:** Test middleware functionality
- **Setup:** None
- **Behavior:** Validates headers are present
- **Issue:** Doesn't actually test rate limiting behavior

---

## Debugging Steps

When test fails:

1. **Check database state**
   - Verify `sample_evidence` fixture is being called
   - Verify `db_session` has clean state
   - Check if other tests polluted the database

2. **Check assertion context**
   - Look for weak assertions (`>= 0`)
   - Check if test validates actual functionality or just structure

3. **Check fixture parameters**
   - Verify all required fixtures are in function signature
   - Verify fixture order doesn't matter (it shouldn't)

4. **Check model loading**
   - Embedding tests load ~500MB model
   - NLI tests load ~1GB model
   - If timeout, models may not be loading

---

## Files to Review When Fixing

| File | Purpose | Related Tests |
|------|---------|---------------|
| `truthgraph/api/ml_routes.py` | API endpoint implementations | All tests |
| `truthgraph/api/models.py` | Request/response schemas | All tests |
| `truthgraph/schemas.py` | Database models | Tests using fixtures |
| `truthgraph/services/ml/embedding_service.py` | Embedding service | TestEmbedEndpoint |
| `truthgraph/services/ml/nli_service.py` | NLI service | TestNLIEndpoint |
| `truthgraph/db.py` | Database session setup | All tests with DB access |

---

## Summary Table

| Category | Status | Count | Notes |
|----------|--------|-------|-------|
| **Total Tests** | - | 29 | All execute but need fixes |
| **Passing Tests** | ✓ | 19 | Basic validation tests |
| **Tests Needing Fixture Fix** | ⚠️ | 5 | Search and verify tests |
| **Tests Needing Assertion Fix** | ⚠️ | 3 | Threshold and rate limit tests |
| **Tests Needing Logic Fix** | ⚠️ | 2 | Verdict tests using manual DB |
| **Critical Infrastructure Issues** | ✗ | 2 | Fixture scope + DB cleanup |

**Overall:** Tests are structurally sound but have critical infrastructure issues that must be fixed.
