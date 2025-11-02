"""Comprehensive tests for ML API endpoints.

Tests cover:
- /api/v1/embed - Embedding generation
- /api/v1/search - Vector/hybrid search
- /api/v1/nli - NLI inference
- /api/v1/verify - Full verification pipeline
- /api/v1/verdict - Verdict retrieval

Includes unit tests, integration tests, and error handling tests.
"""

from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from truthgraph.api.middleware import ErrorHandlingMiddleware, RequestIDMiddleware
from truthgraph.api.ml_routes import router as ml_router
from truthgraph.api.routes import router
from truthgraph.db import Base, SessionLocal, engine
from truthgraph.schemas import Claim, Embedding, Evidence, VerificationResult
from truthgraph.services.ml.embedding_service import get_embedding_service


@asynccontextmanager
async def test_lifespan(app: FastAPI):
    """Test application lifespan - no ML model preloading."""
    # Create database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup happens per-test


@pytest.fixture(scope="function")
def client():
    """Create test client with high rate limits.

    Function scope ensures proper test isolation.
    Rate limits are set very high to avoid 429 errors during testing.
    """
    # Import RateLimitMiddleware
    from truthgraph.api.middleware import RateLimitMiddleware

    # Create test app with very high rate limits
    test_app = FastAPI(
        title="TruthGraph Test API",
        version="2.0.0",
        lifespan=test_lifespan,
    )

    # Add middleware with very high limits (essentially unlimited for tests)
    test_app.add_middleware(ErrorHandlingMiddleware)
    test_app.add_middleware(RequestIDMiddleware)
    test_app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=10000,  # Very high limit for tests
        ml_requests_per_minute=10000,  # Very high limit for tests
    )

    # Include API routes
    test_app.include_router(router, prefix="/api/v1", tags=["Claims"])
    test_app.include_router(ml_router, tags=["ML Services"])

    # Add health endpoint
    @test_app.get("/health")
    async def health_check():
        return {"status": "healthy", "services": {}}

    # Add root endpoint
    @test_app.get("/")
    def root():
        return {
            "service": "TruthGraph Test API",
            "version": "2.0.0",
            "endpoints": {
                "verify": "/api/v1/verify",
                "embed": "/api/v1/embed",
                "search": "/api/v1/search",
                "nli": "/api/v1/nli",
            },
        }

    return TestClient(test_app)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh database session for each test.

    Uses transaction rollback for fast cleanup instead of drop_all().
    """
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    # Create a connection and begin a transaction
    connection = engine.connect()
    transaction = connection.begin()

    # Create session bound to this connection
    session = SessionLocal(bind=connection)

    yield session

    # Cleanup: rollback transaction and close connection
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def sample_evidence(db_session):
    """Create sample evidence with embeddings for testing."""
    embedding_service = get_embedding_service()

    # Create evidence items
    evidence_texts = [
        "The Earth orbits around the Sun in an elliptical orbit taking approximately 365.25 days.",
        "Water freezes at 0 degrees Celsius or 32 degrees Fahrenheit at standard atmospheric pressure.",
        "The speed of light in vacuum is approximately 299,792,458 meters per second.",
        "Photosynthesis is the process by which plants convert sunlight into chemical energy.",
        "The human heart pumps blood throughout the body via the circulatory system.",
    ]

    evidence_items = []
    for text in evidence_texts:
        # Create evidence
        evidence = Evidence(
            content=text, source_url="https://example.com/science", source_type="scientific"
        )
        db_session.add(evidence)
        db_session.flush()

        # Generate and store embedding
        embedding_vector = embedding_service.embed_text(text)
        embedding = Embedding(
            entity_type="evidence",
            entity_id=evidence.id,
            embedding=embedding_vector,
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            tenant_id="default",
        )
        db_session.add(embedding)

        evidence_items.append(evidence)

    db_session.commit()

    return evidence_items


# ===== Embedding Endpoint Tests =====


class TestEmbedEndpoint:
    """Tests for /api/v1/embed endpoint."""

    def test_embed_single_text(self, client):
        """Test embedding generation for single text."""
        response = client.post("/api/v1/embed", json={"texts": ["Hello world"]})

        assert response.status_code == 200
        data = response.json()

        assert data["count"] == 1
        assert data["dimension"] == 384
        assert len(data["embeddings"]) == 1
        assert len(data["embeddings"][0]) == 384
        assert "processing_time_ms" in data

    def test_embed_multiple_texts(self, client):
        """Test embedding generation for multiple texts."""
        texts = [
            "The Earth orbits the Sun",
            "Water freezes at zero degrees",
            "Light travels at 3e8 m/s",
        ]

        response = client.post("/api/v1/embed", json={"texts": texts, "batch_size": 32})

        assert response.status_code == 200
        data = response.json()

        assert data["count"] == 3
        assert data["dimension"] == 384
        assert len(data["embeddings"]) == 3
        assert all(len(emb) == 384 for emb in data["embeddings"])

    def test_embed_empty_text_error(self, client):
        """Test error handling for empty text."""
        response = client.post("/api/v1/embed", json={"texts": [""]})

        assert response.status_code == 422  # Pydantic validation error

    def test_embed_too_many_texts_error(self, client):
        """Test error handling for too many texts."""
        response = client.post(
            "/api/v1/embed",
            json={"texts": ["text"] * 101},  # Max is 100
        )

        assert response.status_code == 422  # Validation error

    def test_embed_invalid_batch_size(self, client):
        """Test error handling for invalid batch size."""
        response = client.post(
            "/api/v1/embed",
            json={"texts": ["test"], "batch_size": 200},  # Max is 128
        )

        assert response.status_code == 422


# ===== Search Endpoint Tests =====


class TestSearchEndpoint:
    """Tests for /api/v1/search endpoint."""

    def test_search_vector_mode(self, client, db_session, sample_evidence):
        """Test vector search mode."""
        response = client.post(
            "/api/v1/search",
            json={"query": "Earth orbits Sun", "limit": 5, "mode": "vector", "min_similarity": 0.5},
        )

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert data["count"] >= 0
        assert data["mode"] == "vector"
        assert data["query"] == "Earth orbits Sun"
        assert "query_time_ms" in data

        # Check result structure
        if data["count"] > 0:
            result = data["results"][0]
            assert "evidence_id" in result
            assert "content" in result
            assert "similarity" in result
            assert "rank" in result
            assert 0.0 <= result["similarity"] <= 1.0

    def test_search_with_similarity_threshold(self, client, db_session, sample_evidence):
        """Test search with minimum similarity threshold."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "completely unrelated quantum mechanics",
                "limit": 10,
                "mode": "vector",
                "min_similarity": 0.9,  # Very high threshold
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should have fewer or no results due to high threshold
        assert data["count"] >= 0

    def test_search_with_limit(self, client, db_session, sample_evidence):
        """Test search result limiting."""
        response = client.post(
            "/api/v1/search", json={"query": "science", "limit": 2, "mode": "vector"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["count"] <= 2

    def test_search_keyword_mode_not_implemented(self, client):
        """Test that keyword mode returns not implemented."""
        response = client.post("/api/v1/search", json={"query": "test", "mode": "keyword"})

        assert response.status_code == 501

    def test_search_empty_query_error(self, client):
        """Test error handling for empty query."""
        response = client.post("/api/v1/search", json={"query": ""})

        assert response.status_code == 422

    def test_search_invalid_limit(self, client):
        """Test error handling for invalid limit."""
        response = client.post(
            "/api/v1/search",
            json={"query": "test", "limit": 200},  # Max is 100
        )

        assert response.status_code == 422


# ===== NLI Endpoint Tests =====


class TestNLIEndpoint:
    """Tests for /api/v1/nli endpoint."""

    def test_nli_entailment(self, client):
        """Test NLI for entailment relationship."""
        response = client.post(
            "/api/v1/nli",
            json={
                "premise": "The Earth revolves around the Sun",
                "hypothesis": "The Earth orbits the Sun",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["label"] in ["entailment", "contradiction", "neutral"]
        assert 0.0 <= data["confidence"] <= 1.0
        assert "scores" in data
        assert "entailment" in data["scores"]
        assert "contradiction" in data["scores"]
        assert "neutral" in data["scores"]
        assert "processing_time_ms" in data

        # Scores should sum to approximately 1.0
        total_score = sum(data["scores"].values())
        assert 0.99 <= total_score <= 1.01

    def test_nli_contradiction(self, client):
        """Test NLI for contradiction relationship."""
        response = client.post(
            "/api/v1/nli", json={"premise": "The Earth is round", "hypothesis": "The Earth is flat"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["label"] in ["entailment", "contradiction", "neutral"]
        assert 0.0 <= data["confidence"] <= 1.0

    def test_nli_empty_premise_error(self, client):
        """Test error handling for empty premise."""
        response = client.post("/api/v1/nli", json={"premise": "", "hypothesis": "test"})

        assert response.status_code == 422

    def test_nli_empty_hypothesis_error(self, client):
        """Test error handling for empty hypothesis."""
        response = client.post("/api/v1/nli", json={"premise": "test", "hypothesis": ""})

        assert response.status_code == 422


class TestNLIBatchEndpoint:
    """Tests for /api/v1/nli/batch endpoint."""

    def test_nli_batch_processing(self, client):
        """Test batch NLI processing."""
        pairs = [
            ["The sky is blue", "The sky has a blue color"],
            ["Water is wet", "Water is dry"],
            ["Cats are mammals", "Cats are reptiles"],
        ]

        response = client.post("/api/v1/nli/batch", json={"pairs": pairs, "batch_size": 8})

        assert response.status_code == 200
        data = response.json()

        assert data["count"] == 3
        assert len(data["results"]) == 3
        assert "total_processing_time_ms" in data

        # Check each result
        for result in data["results"]:
            assert result["label"] in ["entailment", "contradiction", "neutral"]
            assert 0.0 <= result["confidence"] <= 1.0
            assert "scores" in result

    def test_nli_batch_too_many_pairs_error(self, client):
        """Test error handling for too many pairs."""
        pairs = [["premise", "hypothesis"]] * 51  # Max is 50

        response = client.post("/api/v1/nli/batch", json={"pairs": pairs})

        assert response.status_code == 422


# ===== Verify Endpoint Tests =====


class TestVerifyEndpoint:
    """Tests for /api/v1/verify endpoint (full pipeline)."""

    def test_verify_claim_with_evidence(self, client, db_session, sample_evidence):
        """Test full verification pipeline with available evidence."""
        response = client.post(
            "/api/v1/verify",
            json={
                "claim": "The Earth orbits the Sun",
                "max_evidence": 5,
                "confidence_threshold": 0.5,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["verdict"] in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]
        assert 0.0 <= data["confidence"] <= 1.0
        assert "evidence" in data
        assert "explanation" in data
        assert "claim_id" in data
        assert "verification_id" in data
        assert "processing_time_ms" in data

        # Check evidence structure
        for evidence_item in data["evidence"]:
            assert "evidence_id" in evidence_item
            assert "content" in evidence_item
            assert "nli_label" in evidence_item
            assert "nli_confidence" in evidence_item
            assert "similarity" in evidence_item

    def test_verify_claim_no_evidence(self, client, db_session):
        """Test verification when no evidence is available."""
        response = client.post(
            "/api/v1/verify",
            json={"claim": "This is a completely novel claim with no evidence", "max_evidence": 10},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["verdict"] == "INSUFFICIENT"
        assert data["confidence"] == 0.0
        assert len(data["evidence"]) == 0
        assert "no relevant evidence" in data["explanation"].lower()

    def test_verify_with_custom_threshold(self, client, db_session, sample_evidence):
        """Test verification with custom confidence threshold."""
        response = client.post(
            "/api/v1/verify",
            json={
                "claim": "Water freezes at 0 degrees Celsius",
                "confidence_threshold": 0.8,
                "max_evidence": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["verdict"] in ["SUPPORTED", "REFUTED", "INSUFFICIENT"]

    def test_verify_empty_claim_error(self, client):
        """Test error handling for empty claim."""
        response = client.post("/api/v1/verify", json={"claim": ""})

        assert response.status_code == 422

    def test_verify_invalid_max_evidence(self, client):
        """Test error handling for invalid max_evidence."""
        response = client.post(
            "/api/v1/verify",
            json={"claim": "test", "max_evidence": 100},  # Max is 50
        )

        assert response.status_code == 422


# ===== Verdict Endpoint Tests =====


class TestVerdictEndpoint:
    """Tests for /api/v1/verdict endpoint."""

    def test_get_verdict_existing(self, client, db_session):
        """Test retrieving verdict for existing claim."""
        # Create claim and verification result
        claim = Claim(text="Test claim")
        db_session.add(claim)
        db_session.commit()
        db_session.refresh(claim)

        verification = VerificationResult(
            claim_id=claim.id,
            verdict="SUPPORTED",
            confidence=0.85,
            support_score=0.85,
            refute_score=0.10,
            neutral_score=0.05,
            evidence_count=5,
            supporting_evidence_count=4,
            refuting_evidence_count=0,
            neutral_evidence_count=1,
            reasoning="Strong supporting evidence found",
            retrieval_method="vector",
        )
        db_session.add(verification)
        db_session.commit()

        # Retrieve verdict
        response = client.get(f"/api/v1/verdict/{claim.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["claim_id"] == str(claim.id)
        assert data["claim_text"] == "Test claim"
        assert data["verdict"] == "SUPPORTED"
        assert data["confidence"] == 0.85
        assert data["evidence_count"] == 5
        assert data["supporting_evidence_count"] == 4
        assert data["refuting_evidence_count"] == 0

    def test_get_verdict_claim_not_found(self, client, db_session):
        """Test error when claim doesn't exist."""
        fake_uuid = uuid4()
        response = client.get(f"/api/v1/verdict/{fake_uuid}")

        assert response.status_code == 404

    def test_get_verdict_no_verification(self, client, db_session):
        """Test error when claim exists but has no verification."""
        claim = Claim(text="Unverified claim")
        db_session.add(claim)
        db_session.commit()

        response = client.get(f"/api/v1/verdict/{claim.id}")

        assert response.status_code == 404


# ===== Health Check Tests =====


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
        assert "version" in data

        # Check service statuses
        assert "database" in data["services"]
        assert "embedding_service" in data["services"]
        assert "nli_service" in data["services"]


# ===== Root Endpoint Tests =====


class TestRootEndpoint:
    """Tests for root / endpoint."""

    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "TruthGraph Phase 2"
        assert data["version"] == "2.0.0"
        assert "endpoints" in data


# ===== Middleware Tests =====


class TestMiddleware:
    """Tests for middleware functionality."""

    def test_request_id_header(self, client):
        """Test that request ID is added to responses."""
        response = client.get("/health")

        assert "X-Request-ID" in response.headers

    def test_process_time_header(self, client):
        """Test that processing time is added to responses."""
        response = client.get("/health")

        assert "X-Process-Time" in response.headers
        assert response.headers["X-Process-Time"].endswith("ms")

    def test_rate_limit_headers(self, client):
        """Test that rate limit headers are added."""
        response = client.get("/health")

        # Health endpoint should not have rate limit headers
        # Test with ML endpoint
        response = client.post("/api/v1/embed", json={"texts": ["test"]})

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
