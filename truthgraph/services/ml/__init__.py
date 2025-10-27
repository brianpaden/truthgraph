"""Machine learning services for TruthGraph."""

from .embedding_service import EmbeddingService, get_embedding_service
from .nli_service import NLILabel, NLIResult, NLIService, get_nli_service
from .verdict_aggregation_service import (
    AggregationStrategy,
    VerdictAggregationService,
    VerdictLabel,
    VerdictResult,
    get_verdict_aggregation_service,
)

__all__ = [
    "EmbeddingService",
    "get_embedding_service",
    "NLILabel",
    "NLIResult",
    "NLIService",
    "get_nli_service",
    "AggregationStrategy",
    "VerdictAggregationService",
    "VerdictLabel",
    "VerdictResult",
    "get_verdict_aggregation_service",
]
