"""Machine learning predictor for failure prevention."""

from .features import FeatureExtractor
from .history_importer import HistoryImporter, ImportResult
from .model import SklearnFailureModel, TrainingResult
from .predictor import FailurePredictor
from .validation import (
    command_fingerprint,
    label_run,
    validate_temporal,
    write_validation_report,
)

__all__ = [
    "FeatureExtractor",
    "FailurePredictor",
    "HistoryImporter",
    "ImportResult",
    "SklearnFailureModel",
    "TrainingResult",
    "command_fingerprint",
    "label_run",
    "validate_temporal",
    "write_validation_report",
]

# V2 exports (available only when [ml] extras installed)
try:
    from .embeddings import CommandEmbedder, EmbeddingStore, get_embedder
    from .vector_store import CommandVectorStore, CommandOutcome, build_vector_store

    __all__ += [
        "CommandEmbedder",
        "EmbeddingStore",
        "get_embedder",
        "CommandVectorStore",
        "CommandOutcome",
        "build_vector_store",
    ]
except ImportError:
    pass
