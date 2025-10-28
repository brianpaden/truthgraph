"""Unit tests for NLI service with mocked models.

This test suite uses mocked transformers models to test the NLI service logic
without downloading or loading actual models. Integration tests with real models
are in test_nli_integration.py.
"""

from unittest.mock import MagicMock, patch

import pytest
import torch

from truthgraph.services.ml import NLILabel, NLIResult, NLIService


class TestNLIServiceMocked:
    """Test NLI service with mocked models (unit tests)."""

    @pytest.fixture
    def mock_model(self):
        """Create a mock NLI model."""
        model = MagicMock()
        model.eval.return_value = None
        model.to.return_value = model
        return model

    @pytest.fixture
    def mock_tokenizer(self):
        """Create a mock tokenizer."""
        tokenizer = MagicMock()
        tokenizer.return_value = {
            "input_ids": torch.tensor([[1, 2, 3]]),
            "attention_mask": torch.tensor([[1, 1, 1]]),
        }
        return tokenizer

    @pytest.fixture
    def nli_service(self, mock_model, mock_tokenizer):
        """Create NLI service with mocked model and tokenizer."""
        # Reset singleton
        NLIService._instance = None

        with (
            patch(
                "truthgraph.services.ml.nli_service.AutoModelForSequenceClassification"
            ) as mock_model_class,
            patch("truthgraph.services.ml.nli_service.AutoTokenizer") as mock_tokenizer_class,
            patch("truthgraph.services.ml.nli_service.torch.cuda.is_available") as mock_cuda,
        ):
            mock_model_class.from_pretrained.return_value = mock_model
            mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
            mock_cuda.return_value = False  # Use CPU for tests

            service = NLIService.get_instance()
            yield service

        # Cleanup
        NLIService._instance = None

    def test_singleton_pattern(self):
        """Test that NLIService follows singleton pattern."""
        # Reset singleton
        NLIService._instance = None

        service1 = NLIService.get_instance()
        service2 = NLIService.get_instance()

        assert service1 is service2
        assert NLIService._instance is service1

        # Cleanup
        NLIService._instance = None

    def test_detect_device_cpu(self):
        """Test device detection returns CPU when no GPU available."""
        with (
            patch("truthgraph.services.ml.nli_service.torch.cuda.is_available") as mock_cuda,
            patch("truthgraph.services.ml.nli_service.torch.backends") as mock_backends,
        ):
            mock_cuda.return_value = False
            mock_backends.mps.is_available.return_value = False

            device = NLIService._detect_device()
            assert device == "cpu"

    def test_detect_device_cuda(self):
        """Test device detection returns CUDA when GPU available."""
        with patch("truthgraph.services.ml.nli_service.torch.cuda.is_available") as mock_cuda:
            mock_cuda.return_value = True

            device = NLIService._detect_device()
            assert device == "cuda"

    def test_detect_device_mps(self):
        """Test device detection returns MPS when available (Apple Silicon)."""
        with (
            patch("truthgraph.services.ml.nli_service.torch.cuda.is_available") as mock_cuda,
            patch("truthgraph.services.ml.nli_service.torch.backends") as mock_backends,
        ):
            mock_cuda.return_value = False
            mock_backends.mps.is_available.return_value = True

            device = NLIService._detect_device()
            assert device == "mps"

    def test_verify_single_entailment(self, nli_service, mock_model):
        """Test single verification with entailment result."""
        # Mock model output for entailment (index 1)
        mock_output = MagicMock()
        mock_output.logits = torch.tensor([[0.3, 2.5, 0.5]])  # High entailment score
        mock_model.return_value = mock_output

        result = nli_service.verify_single(
            premise="Paris is the capital of France",
            hypothesis="Paris is in France",
        )

        assert isinstance(result, NLIResult)
        assert result.label == NLILabel.ENTAILMENT
        assert result.confidence > 0.8
        assert "entailment" in result.scores
        assert "neutral" in result.scores
        assert "contradiction" in result.scores
        assert sum(result.scores.values()) == pytest.approx(1.0, abs=0.01)

    def test_verify_single_contradiction(self, nli_service, mock_model):
        """Test single verification with contradiction result."""
        # Mock model output for contradiction (index 0)
        mock_output = MagicMock()
        mock_output.logits = torch.tensor([[2.8, 0.5, 0.3]])  # High contradiction score
        mock_model.return_value = mock_output

        result = nli_service.verify_single(
            premise="The Earth orbits the Sun",
            hypothesis="The Sun orbits the Earth",
        )

        assert isinstance(result, NLIResult)
        assert result.label == NLILabel.CONTRADICTION
        assert result.confidence > 0.8
        assert sum(result.scores.values()) == pytest.approx(1.0, abs=0.01)

    def test_verify_single_neutral(self, nli_service, mock_model):
        """Test single verification with neutral result."""
        # Mock model output for neutral (index 2)
        mock_output = MagicMock()
        mock_output.logits = torch.tensor([[0.3, 0.4, 2.5]])  # High neutral score
        mock_model.return_value = mock_output

        result = nli_service.verify_single(
            premise="The sky is blue",
            hypothesis="Water is wet",
        )

        assert isinstance(result, NLIResult)
        assert result.label == NLILabel.NEUTRAL
        assert result.confidence > 0.8
        assert sum(result.scores.values()) == pytest.approx(1.0, abs=0.01)

    def test_verify_single_empty_premise(self, nli_service):
        """Test that empty premise raises ValueError."""
        with pytest.raises(ValueError, match="Premise cannot be empty"):
            nli_service.verify_single(premise="", hypothesis="Some claim")

    def test_verify_single_empty_hypothesis(self, nli_service):
        """Test that empty hypothesis raises ValueError."""
        with pytest.raises(ValueError, match="Hypothesis cannot be empty"):
            nli_service.verify_single(premise="Some evidence", hypothesis="")

    def test_verify_single_whitespace_only(self, nli_service):
        """Test that whitespace-only inputs raise ValueError."""
        with pytest.raises(ValueError, match="Premise cannot be empty"):
            nli_service.verify_single(premise="   ", hypothesis="Some claim")

        with pytest.raises(ValueError, match="Hypothesis cannot be empty"):
            nli_service.verify_single(premise="Some evidence", hypothesis="   ")

    def test_verify_batch_multiple_pairs(self, nli_service, mock_model):
        """Test batch verification with multiple pairs."""
        # Mock model output for a batch
        mock_output = MagicMock()
        mock_output.logits = torch.tensor(
            [
                [0.3, 2.5, 0.5],  # Entailment (index 1)
                [2.8, 0.5, 0.3],  # Contradiction (index 0)
                [0.3, 0.4, 2.5],  # Neutral (index 2)
            ]
        )
        mock_model.return_value = mock_output

        pairs = [
            ("Evidence 1", "Claim 1"),
            ("Evidence 2", "Claim 2"),
            ("Evidence 3", "Claim 3"),
        ]

        results = nli_service.verify_batch(pairs, batch_size=8)

        assert len(results) == 3
        assert all(isinstance(r, NLIResult) for r in results)
        assert results[0].label == NLILabel.ENTAILMENT
        assert results[1].label == NLILabel.CONTRADICTION
        assert results[2].label == NLILabel.NEUTRAL

    def test_verify_batch_batching(self, nli_service, mock_model):
        """Test that batch processing respects batch_size."""
        # Mock model output
        mock_output = MagicMock()
        mock_output.logits = torch.tensor([[0.3, 2.5, 0.5]] * 2)  # Batch of 2
        mock_model.return_value = mock_output

        # 5 pairs with batch_size=2 should process in 3 batches
        pairs = [(f"Evidence {i}", f"Claim {i}") for i in range(5)]

        results = nli_service.verify_batch(pairs, batch_size=2)

        assert len(results) == 5
        # Model should be called 3 times (2+2+1)
        assert mock_model.call_count >= 3

    def test_verify_batch_empty_pairs(self, nli_service):
        """Test that empty pairs list raises ValueError."""
        with pytest.raises(ValueError, match="Pairs list cannot be empty"):
            nli_service.verify_batch([])

    def test_verify_batch_invalid_pair(self, nli_service):
        """Test that invalid pairs raise ValueError."""
        pairs = [
            ("Valid evidence", "Valid claim"),
            ("", "Invalid - empty premise"),
        ]

        with pytest.raises(ValueError, match="Premise at index 1 cannot be empty"):
            nli_service.verify_batch(pairs)

        pairs = [
            ("Valid evidence", "Valid claim"),
            ("Invalid - empty hypothesis", ""),
        ]

        with pytest.raises(ValueError, match="Hypothesis at index 1 cannot be empty"):
            nli_service.verify_batch(pairs)

    def test_model_loads_once(self, nli_service, mock_model):
        """Test that model is loaded only once (lazy loading)."""
        # Model should not be loaded initially
        assert not nli_service._initialized

        # Mock model output
        mock_output = MagicMock()
        mock_output.logits = torch.tensor([[0.3, 2.5, 0.5]])
        mock_model.return_value = mock_output

        # First call should load model
        nli_service.verify_single("Evidence", "Claim")
        assert nli_service._initialized

        # Get call count
        initial_load_calls = mock_model.to.call_count

        # Second call should not reload
        nli_service.verify_single("Evidence 2", "Claim 2")
        assert mock_model.to.call_count == initial_load_calls  # No additional load

    def test_get_model_info(self, nli_service):
        """Test model info retrieval."""
        info = nli_service.get_model_info()

        assert "model_name" in info
        assert "device" in info
        assert "initialized" in info
        assert info["model_name"] == "cross-encoder/nli-deberta-v3-base"
        assert isinstance(info["initialized"], bool)

    def test_label_mapping(self):
        """Test that label mapping is correct for cross-encoder/nli-deberta-v3-base."""
        assert NLIService._label_mapping[0] == NLILabel.CONTRADICTION
        assert NLIService._label_mapping[1] == NLILabel.ENTAILMENT
        assert NLIService._label_mapping[2] == NLILabel.NEUTRAL

    def test_nli_result_dataclass(self):
        """Test NLIResult dataclass structure."""
        result = NLIResult(
            label=NLILabel.ENTAILMENT,
            confidence=0.95,
            scores={
                "entailment": 0.95,
                "neutral": 0.03,
                "contradiction": 0.02,
            },
        )

        assert result.label == NLILabel.ENTAILMENT
        assert result.confidence == 0.95
        assert len(result.scores) == 3
        assert sum(result.scores.values()) == 1.0

    def test_nli_label_enum(self):
        """Test NLILabel enum values."""
        assert NLILabel.ENTAILMENT.value == "entailment"
        assert NLILabel.CONTRADICTION.value == "contradiction"
        assert NLILabel.NEUTRAL.value == "neutral"

        # Test string comparison
        assert NLILabel.ENTAILMENT == "entailment"
        assert NLILabel.CONTRADICTION == "contradiction"
        assert NLILabel.NEUTRAL == "neutral"


class TestNLIServiceErrorHandling:
    """Test error handling in NLI service."""

    def test_model_load_failure(self):
        """Test handling of model loading failure."""
        # Reset singleton
        NLIService._instance = None

        with (
            patch(
                "truthgraph.services.ml.nli_service.AutoModelForSequenceClassification"
            ) as mock_model_class,
            patch("truthgraph.services.ml.nli_service.torch.cuda.is_available") as mock_cuda,
        ):
            mock_model_class.from_pretrained.side_effect = RuntimeError("Model download failed")
            mock_cuda.return_value = False

            service = NLIService.get_instance()

            with pytest.raises(RuntimeError, match="Failed to load NLI model"):
                service.verify_single("Evidence", "Claim")

        # Cleanup
        NLIService._instance = None

    def test_inference_failure(self):
        """Test handling of inference failure."""
        # Reset singleton
        NLIService._instance = None

        mock_model = MagicMock()
        mock_model.eval.return_value = None
        mock_model.to.return_value = mock_model
        mock_model.side_effect = RuntimeError("CUDA out of memory")

        with (
            patch(
                "truthgraph.services.ml.nli_service.AutoModelForSequenceClassification"
            ) as mock_model_class,
            patch("truthgraph.services.ml.nli_service.AutoTokenizer") as mock_tokenizer_class,
            patch("truthgraph.services.ml.nli_service.torch.cuda.is_available") as mock_cuda,
        ):
            mock_model_class.from_pretrained.return_value = mock_model
            mock_tokenizer = MagicMock()
            mock_tokenizer.return_value = {
                "input_ids": torch.tensor([[1, 2, 3]]),
                "attention_mask": torch.tensor([[1, 1, 1]]),
            }
            mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
            mock_cuda.return_value = False

            service = NLIService.get_instance()

            with pytest.raises(RuntimeError, match="NLI inference failed"):
                service.verify_single("Evidence", "Claim")

        # Cleanup
        NLIService._instance = None


def test_get_nli_service():
    """Test convenience function for getting NLI service."""
    from truthgraph.services.ml import get_nli_service

    # Reset singleton
    NLIService._instance = None

    service1 = get_nli_service()
    service2 = get_nli_service()

    assert service1 is service2
    assert isinstance(service1, NLIService)

    # Cleanup
    NLIService._instance = None
