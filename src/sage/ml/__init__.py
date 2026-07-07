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
    "CommandEmbedder",
    "EmbeddingStore",
    "get_embedder",
    "CommandVectorStore",
    "CommandOutcome",
    "build_vector_store",
    "NeuralCommandCenter",
    "NeuralResult",
]

# V2 exports are lazy — importing torch/faiss at module level adds ~11s.
# Access these names via sage.ml.NeuralCommandCenter etc. and they load on demand.
_V2_NAMES = {
    "CommandEmbedder": (".embeddings", "CommandEmbedder"),
    "EmbeddingStore": (".embeddings", "EmbeddingStore"),
    "get_embedder": (".embeddings", "get_embedder"),
    "CommandVectorStore": (".vector_store", "CommandVectorStore"),
    "CommandOutcome": (".vector_store", "CommandOutcome"),
    "build_vector_store": (".vector_store", "build_vector_store"),
    "NeuralCommandCenter": (".neural_center", "NeuralCommandCenter"),
    "NeuralResult": (".neural_center", "NeuralResult"),
}


def __getattr__(name):
    if name in _V2_NAMES:
        module_path, attr = _V2_NAMES[name]
        import importlib
        mod = importlib.import_module(module_path, __package__)
        value = getattr(mod, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'sage.ml' has no attribute {name!r}")
