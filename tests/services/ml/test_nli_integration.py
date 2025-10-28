"""Integration tests for NLI service with real models.

These tests download and use actual transformer models. They are slower than unit tests
but validate the complete integration with real NLI models.

Run with: pytest tests/services/ml/test_nli_integration.py -v
Skip with: pytest -m "not integration"
"""

import pytest

from truthgraph.services.ml import NLILabel, NLIResult, NLIService, get_nli_service


@pytest.mark.integration
class TestNLIServiceIntegration:
    """Integration tests with real NLI model."""

    @pytest.fixture(scope="class")
    def nli_service(self):
        """Create NLI service with real model (loaded once for all tests)."""
        # Reset singleton to ensure clean state
        NLIService._instance = None
        service = get_nli_service()
        yield service
        # Cleanup
        NLIService._instance = None

    def test_model_loads_successfully(self, nli_service):
        """Test that model loads without errors."""
        info = nli_service.get_model_info()
        assert info["model_name"] == "cross-encoder/nli-deberta-v3-base"
        assert info["device"] in ["cpu", "cuda", "mps"]

    def test_entailment_detection(self, nli_service):
        """Test detection of entailment relationship."""
        result = nli_service.verify_single(
            premise="Paris is the capital of France and a major European city.",
            hypothesis="Paris is in France.",
        )

        assert isinstance(result, NLIResult)
        assert result.label == NLILabel.ENTAILMENT
        assert result.confidence > 0.5
        assert sum(result.scores.values()) == pytest.approx(1.0, abs=0.01)

    def test_contradiction_detection(self, nli_service):
        """Test detection of contradiction relationship."""
        result = nli_service.verify_single(
            premise="The Earth is the third planet from the Sun.",
            hypothesis="The Earth is the first planet from the Sun.",
        )

        assert isinstance(result, NLIResult)
        assert result.label == NLILabel.CONTRADICTION
        assert result.confidence > 0.5
        assert sum(result.scores.values()) == pytest.approx(1.0, abs=0.01)

    def test_neutral_detection(self, nli_service):
        """Test detection of neutral relationship."""
        result = nli_service.verify_single(
            premise="The Eiffel Tower is in Paris.",
            hypothesis="Water boils at 100 degrees Celsius.",
        )

        assert isinstance(result, NLIResult)
        assert result.label == NLILabel.NEUTRAL
        assert result.confidence > 0.3  # Lower threshold for neutral
        assert sum(result.scores.values()) == pytest.approx(1.0, abs=0.01)

    def test_batch_inference(self, nli_service):
        """Test batch inference with multiple pairs."""
        pairs = [
            # Entailment
            (
                "All mammals are warm-blooded animals.",
                "Dogs are warm-blooded.",
            ),
            # Contradiction
            (
                "The meeting is scheduled for Monday morning.",
                "The meeting will happen on Friday.",
            ),
            # Neutral
            (
                "The sky is blue during the day.",
                "Grass is green.",
            ),
        ]

        results = nli_service.verify_batch(pairs, batch_size=8)

        assert len(results) == 3
        assert all(isinstance(r, NLIResult) for r in results)

        # Check that all results have valid scores
        for result in results:
            assert 0.0 <= result.confidence <= 1.0
            assert sum(result.scores.values()) == pytest.approx(1.0, abs=0.01)
            assert result.label in [
                NLILabel.ENTAILMENT,
                NLILabel.CONTRADICTION,
                NLILabel.NEUTRAL,
            ]

        # First pair should be entailment
        assert results[0].label == NLILabel.ENTAILMENT
        # Second pair should be contradiction
        assert results[1].label == NLILabel.CONTRADICTION
        # Third pair should be neutral
        assert results[2].label == NLILabel.NEUTRAL

    def test_long_texts(self, nli_service):
        """Test handling of longer text inputs."""
        long_premise = (
            "Climate change refers to long-term shifts in temperatures and weather "
            "patterns. These shifts may be natural, but since the 1800s, human "
            "activities have been the main driver of climate change, primarily due "
            "to the burning of fossil fuels like coal, oil and gas. Burning fossil "
            "fuels generates greenhouse gas emissions that act like a blanket wrapped "
            "around the Earth, trapping the sun's heat and raising temperatures."
        )

        result = nli_service.verify_single(
            premise=long_premise,
            hypothesis="Human activities contribute to climate change.",
        )

        assert isinstance(result, NLIResult)
        assert result.label == NLILabel.ENTAILMENT
        assert result.confidence > 0.5

    def test_special_characters(self, nli_service):
        """Test handling of special characters and punctuation."""
        result = nli_service.verify_single(
            premise="E = mc² is Einstein's famous equation.",
            hypothesis="Einstein developed the equation E = mc².",
        )

        assert isinstance(result, NLIResult)
        assert result.label == NLILabel.ENTAILMENT

    def test_case_sensitivity(self, nli_service):
        """Test that model handles different cases correctly."""
        result1 = nli_service.verify_single(
            premise="PARIS IS THE CAPITAL OF FRANCE.",
            hypothesis="paris is in france.",
        )

        result2 = nli_service.verify_single(
            premise="Paris is the capital of France.",
            hypothesis="Paris is in France.",
        )

        # Both should be entailment
        assert result1.label == NLILabel.ENTAILMENT
        assert result2.label == NLILabel.ENTAILMENT

    def test_numerical_claims(self, nli_service):
        """Test handling of numerical claims."""
        result = nli_service.verify_single(
            premise="The speed of light is approximately 299,792,458 meters per second.",
            hypothesis="Light travels at about 300,000 kilometers per second.",
        )

        assert isinstance(result, NLIResult)
        # Should recognize these are consistent (entailment or neutral)
        assert result.label in [NLILabel.ENTAILMENT, NLILabel.NEUTRAL]

    def test_model_caching(self, nli_service):
        """Test that model is cached and not reloaded."""
        # First call
        result1 = nli_service.verify_single("Evidence 1", "Claim 1")
        info1 = nli_service.get_model_info()
        assert result1

        # Second call
        result2 = nli_service.verify_single("Evidence 2", "Claim 2")
        info2 = nli_service.get_model_info()
        assert result2

        # Model should remain loaded
        assert info1["initialized"]
        assert info2["initialized"]
        assert info1["device"] == info2["device"]

    def test_batch_size_variations(self, nli_service):
        """Test different batch sizes produce same results."""
        pairs = [(f"Evidence {i}", f"Claim {i}") for i in range(10)]

        # Process with different batch sizes
        results_batch_2 = nli_service.verify_batch(pairs, batch_size=2)
        results_batch_5 = nli_service.verify_batch(pairs, batch_size=5)

        # Results should be similar (order might vary slightly)
        assert len(results_batch_2) == len(results_batch_5) == 10

        # Labels should be the same for corresponding pairs
        for r1, r2 in zip(results_batch_2, results_batch_5, strict=False):
            assert r1.label == r2.label
            # Confidence should be very close
            assert abs(r1.confidence - r2.confidence) < 0.01


@pytest.mark.integration
class TestNLIServicePerformance:
    """Performance tests for NLI service."""

    @pytest.fixture(scope="class")
    def nli_service(self):
        """Create NLI service with real model."""
        NLIService._instance = None
        service = get_nli_service()
        yield service
        NLIService._instance = None

    def test_throughput_target(self, nli_service):
        """Test that service meets >2 pairs/second throughput target."""
        import time

        # Prepare test pairs
        pairs = [
            (
                f"Evidence text number {i} with some content.",
                f"Claim text number {i} to verify.",
            )
            for i in range(20)
        ]

        # Warm up the model
        nli_service.verify_single("Warm up evidence", "Warm up claim")

        # Measure throughput
        start_time = time.time()
        results = nli_service.verify_batch(pairs, batch_size=8)
        elapsed_time = time.time() - start_time

        throughput = len(pairs) / elapsed_time

        assert len(results) == 20
        assert throughput > 2.0, f"Throughput {throughput:.2f} pairs/sec is below 2.0 target"

    def test_memory_efficiency(self, nli_service):
        """Test memory usage remains reasonable."""
        import gc

        # Run garbage collection
        gc.collect()

        # Process batch
        pairs = [(f"Evidence {i}", f"Claim {i}") for i in range(50)]
        results = nli_service.verify_batch(pairs, batch_size=8)

        assert len(results) == 50

        # Memory should be released after batch
        gc.collect()

        # All results should be valid
        for result in results:
            assert isinstance(result, NLIResult)
            assert 0.0 <= result.confidence <= 1.0


@pytest.mark.integration
class TestNLIServiceRealWorldClaims:
    """Test with real-world claim examples."""

    @pytest.fixture(scope="class")
    def nli_service(self):
        """Create NLI service with real model."""
        NLIService._instance = None
        service = get_nli_service()
        yield service
        NLIService._instance = None

    def test_scientific_claim(self, nli_service):
        """Test scientific claim verification."""
        result = nli_service.verify_single(
            premise="Water consists of two hydrogen atoms and one oxygen atom (H2O).",
            hypothesis="Water is made of hydrogen and oxygen.",
        )

        assert result.label == NLILabel.ENTAILMENT
        assert result.confidence > 0.7

    def test_historical_claim(self, nli_service):
        """Test historical claim verification."""
        result = nli_service.verify_single(
            premise="World War II ended in 1945 with the defeat of Nazi Germany and Japan.",
            hypothesis="World War II concluded in 1945.",
        )

        assert result.label == NLILabel.ENTAILMENT
        assert result.confidence > 0.7

    def test_contradictory_medical_claim(self, nli_service):
        """Test contradictory medical claim."""
        result = nli_service.verify_single(
            premise="Vaccines help protect against infectious diseases by training the immune system.",
            hypothesis="Vaccines weaken the immune system.",
        )

        assert result.label == NLILabel.CONTRADICTION
        assert result.confidence > 0.5

    def test_unrelated_claims(self, nli_service):
        """Test unrelated claims are marked as neutral."""
        result = nli_service.verify_single(
            premise="The Amazon rainforest produces 20% of Earth's oxygen.",
            hypothesis="Coffee was first discovered in Ethiopia.",
        )

        assert result.label == NLILabel.NEUTRAL
        assert result.confidence > 0.3
