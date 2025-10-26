"""Natural Language Inference (NLI) service for claim verification.

This module provides NLI verification using DeBERTa-v3-base models fine-tuned on MNLI.
It supports single and batch inference with GPU/CPU/MPS device detection.

Example:
    >>> service = get_nli_service()
    >>> result = service.verify_single(
    ...     premise="The Earth orbits the Sun",
    ...     hypothesis="The Sun orbits the Earth"
    ... )
    >>> print(result.label)  # NLILabel.CONTRADICTION
    >>> print(result.confidence)  # 0.95
"""

import gc
from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar

import structlog
import torch
from transformers import (  # type: ignore[import-untyped]
    AutoModelForSequenceClassification,
    AutoTokenizer,
)

logger = structlog.get_logger(__name__)


class NLILabel(str, Enum):
    """NLI label categories for claim-evidence relationships."""

    ENTAILMENT = "entailment"
    CONTRADICTION = "contradiction"
    NEUTRAL = "neutral"


@dataclass
class NLIResult:
    """Result of NLI verification for a single claim-evidence pair.

    Attributes:
        label: The predicted NLI label (entailment, contradiction, or neutral)
        confidence: Confidence score for the predicted label (0.0-1.0)
        scores: Dictionary mapping each label to its probability score
    """

    label: NLILabel
    confidence: float
    scores: dict[str, float]


class NLIService:
    """Singleton service for Natural Language Inference verification.

    This service uses microsoft/deberta-v3-base fine-tuned on MNLI for NLI tasks.
    Models are loaded lazily on first use and cached for subsequent calls.

    Performance targets:
        - >2 pairs/second on CPU
        - <2GB memory usage (shared with embedding service)
        - Model loads once (singleton pattern)

    Thread safety: This class is NOT thread-safe. Use one instance per process.
    """

    _instance: ClassVar["NLIService | None"] = None
    # Using cross-encoder/nli-deberta-v3-base - specifically fine-tuned for NLI
    _model_name: ClassVar[str] = "cross-encoder/nli-deberta-v3-base"

    # Label mapping for cross-encoder/nli-deberta-v3-base
    # Index mapping: 0=CONTRADICTION, 1=ENTAILMENT, 2=NEUTRAL
    _label_mapping: ClassVar[dict[int, NLILabel]] = {
        0: NLILabel.CONTRADICTION,
        1: NLILabel.ENTAILMENT,
        2: NLILabel.NEUTRAL,
    }

    def __init__(self) -> None:
        """Initialize NLI service (private - use get_nli_service() instead)."""
        self.model: Any = None  # AutoModelForSequenceClassification
        self.tokenizer: Any = None  # AutoTokenizer
        self.device: str | None = None
        self._initialized: bool = False

    @classmethod
    def get_instance(cls) -> "NLIService":
        """Get singleton instance of NLI service.

        Returns:
            The singleton NLIService instance
        """
        if cls._instance is None:
            cls._instance = cls()
            logger.info("nli_service_created")
        return cls._instance

    @staticmethod
    def _detect_device() -> str:
        """Detect available compute device (GPU/CPU/MPS).

        Returns:
            Device string: "cuda", "mps", or "cpu"
        """
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"

    def _load_model(self) -> None:
        """Load NLI model and tokenizer (lazy loading).

        Raises:
            RuntimeError: If model loading fails
        """
        if self._initialized:
            return

        try:
            self.device = self._detect_device()
            logger.info(
                "loading_nli_model",
                model=self._model_name,
                device=self.device,
            )

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(  # type: ignore[no-untyped-call]
                self._model_name,
                model_max_length=512,
            )

            # Load model
            self.model = AutoModelForSequenceClassification.from_pretrained(  # type: ignore[no-untyped-call]
                self._model_name
            )
            self.model.to(self.device)  # type: ignore[union-attr]
            self.model.eval()  # type: ignore[union-attr]  # Set to evaluation mode

            self._initialized = True
            logger.info(
                "nli_model_loaded",
                model=self._model_name,
                device=self.device,
                memory_allocated_mb=torch.cuda.memory_allocated() / 1024 / 1024
                if self.device == "cuda"
                else 0,
            )

        except Exception as e:
            logger.error("nli_model_load_failed", error=str(e), exc_info=True)
            raise RuntimeError(f"Failed to load NLI model: {e}") from e

    def verify_single(self, premise: str, hypothesis: str) -> NLIResult:
        """Verify single premise-hypothesis pair using NLI.

        The premise is typically the evidence text, and the hypothesis is the claim.
        This method determines if the evidence supports (entailment), contradicts
        (contradiction), or is unrelated (neutral) to the claim.

        Args:
            premise: The evidence or premise text
            hypothesis: The claim or hypothesis text to verify

        Returns:
            NLIResult containing label, confidence, and all scores

        Raises:
            ValueError: If premise or hypothesis is empty
            RuntimeError: If model inference fails

        Example:
            >>> service = get_nli_service()
            >>> result = service.verify_single(
            ...     premise="Paris is the capital of France",
            ...     hypothesis="Paris is in France"
            ... )
            >>> print(result.label)  # NLILabel.ENTAILMENT
        """
        if not premise or not premise.strip():
            raise ValueError("Premise cannot be empty")
        if not hypothesis or not hypothesis.strip():
            raise ValueError("Hypothesis cannot be empty")

        # Ensure model is loaded
        self._load_model()

        try:
            # Tokenize input
            assert self.tokenizer is not None
            inputs = self.tokenizer(  # type: ignore[operator]
                premise,
                hypothesis,
                truncation=True,
                padding=True,
                max_length=512,
                return_tensors="pt",
            )

            # Move inputs to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Run inference
            assert self.model is not None
            with torch.no_grad():
                outputs = self.model(**inputs)  # type: ignore[operator]
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)

            # Extract results
            probs = probabilities[0].cpu().numpy()
            predicted_idx = int(probs.argmax())
            predicted_label = self._label_mapping[predicted_idx]
            confidence = float(probs[predicted_idx])

            # Build scores dictionary
            scores = {
                NLILabel.ENTAILMENT.value: float(probs[0]),
                NLILabel.NEUTRAL.value: float(probs[1]),
                NLILabel.CONTRADICTION.value: float(probs[2]),
            }

            logger.debug(
                "nli_inference_complete",
                label=predicted_label.value,
                confidence=confidence,
                premise_length=len(premise),
                hypothesis_length=len(hypothesis),
            )

            return NLIResult(
                label=predicted_label,
                confidence=confidence,
                scores=scores,
            )

        except Exception as e:
            logger.error("nli_inference_failed", error=str(e), exc_info=True)
            raise RuntimeError(f"NLI inference failed: {e}") from e

    def verify_batch(
        self,
        pairs: list[tuple[str, str]],
        batch_size: int = 8,
    ) -> list[NLIResult]:
        """Verify multiple premise-hypothesis pairs in batches.

        This method processes multiple pairs efficiently using batched inference.
        Batch size 8 is optimal for CPU; increase for GPU.

        Args:
            pairs: List of (premise, hypothesis) tuples to verify
            batch_size: Number of pairs to process in each batch (default: 8)

        Returns:
            List of NLIResult objects in the same order as input pairs

        Raises:
            ValueError: If pairs list is empty or contains invalid pairs
            RuntimeError: If batch inference fails

        Example:
            >>> service = get_nli_service()
            >>> pairs = [
            ...     ("Evidence 1", "Claim 1"),
            ...     ("Evidence 2", "Claim 2"),
            ... ]
            >>> results = service.verify_batch(pairs, batch_size=8)
            >>> for result in results:
            ...     print(f"{result.label}: {result.confidence:.2f}")
        """
        if not pairs:
            raise ValueError("Pairs list cannot be empty")

        # Validate all pairs
        for i, (premise, hypothesis) in enumerate(pairs):
            if not premise or not premise.strip():
                raise ValueError(f"Premise at index {i} cannot be empty")
            if not hypothesis or not hypothesis.strip():
                raise ValueError(f"Hypothesis at index {i} cannot be empty")

        # Ensure model is loaded
        self._load_model()

        results: list[NLIResult] = []

        try:
            total_pairs = len(pairs)
            logger.info(
                "nli_batch_inference_start",
                total_pairs=total_pairs,
                batch_size=batch_size,
            )

            # Process in batches
            for i in range(0, total_pairs, batch_size):
                batch_pairs = pairs[i : i + batch_size]
                premises = [pair[0] for pair in batch_pairs]
                hypotheses = [pair[1] for pair in batch_pairs]

                # Tokenize batch
                assert self.tokenizer is not None
                inputs = self.tokenizer(  # type: ignore[operator]
                    premises,
                    hypotheses,
                    truncation=True,
                    padding=True,
                    max_length=512,
                    return_tensors="pt",
                )

                # Move to device
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

                # Run inference
                assert self.model is not None
                with torch.no_grad():
                    outputs = self.model(**inputs)  # type: ignore[operator]
                    logits = outputs.logits
                    probabilities = torch.softmax(logits, dim=-1)

                # Extract results for each item in batch
                probs_numpy = probabilities.cpu().numpy()
                for j in range(len(batch_pairs)):
                    probs = probs_numpy[j]
                    predicted_idx = int(probs.argmax())
                    predicted_label = self._label_mapping[predicted_idx]
                    confidence = float(probs[predicted_idx])

                    scores = {
                        NLILabel.ENTAILMENT.value: float(probs[0]),
                        NLILabel.NEUTRAL.value: float(probs[1]),
                        NLILabel.CONTRADICTION.value: float(probs[2]),
                    }

                    results.append(
                        NLIResult(
                            label=predicted_label,
                            confidence=confidence,
                            scores=scores,
                        )
                    )

                # Memory management for large batches
                if self.device == "cuda":
                    torch.cuda.empty_cache()

            logger.info(
                "nli_batch_inference_complete",
                total_pairs=total_pairs,
                batches_processed=(total_pairs + batch_size - 1) // batch_size,
            )

            # Cleanup
            gc.collect()

            return results

        except Exception as e:
            logger.error("nli_batch_inference_failed", error=str(e), exc_info=True)
            raise RuntimeError(f"Batch NLI inference failed: {e}") from e

    def get_model_info(self) -> dict[str, str | bool]:
        """Get information about the loaded model.

        Returns:
            Dictionary with model name, device, and initialization status
        """
        return {
            "model_name": self._model_name,
            "device": self.device or "not_loaded",
            "initialized": self._initialized,
        }


def get_nli_service() -> NLIService:
    """Get the singleton NLI service instance.

    This is a convenience function for accessing the NLI service.
    The model is loaded lazily on first inference call.

    Returns:
        The singleton NLIService instance

    Example:
        >>> service = get_nli_service()
        >>> result = service.verify_single("Evidence", "Claim")
    """
    return NLIService.get_instance()
