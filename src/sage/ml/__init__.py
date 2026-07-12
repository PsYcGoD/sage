"""Machine learning predictor for failure prevention.

Exports are loaded lazily so lightweight commands do not import sklearn, torch,
or faiss unless ML functionality is actually used.
"""

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

_LAZY_NAMES = {
    "FeatureExtractor": (".features", "FeatureExtractor"),
    "FailurePredictor": (".predictor", "FailurePredictor"),
    "HistoryImporter": (".history_importer", "HistoryImporter"),
    "ImportResult": (".history_importer", "ImportResult"),
    "SklearnFailureModel": (".model", "SklearnFailureModel"),
    "TrainingResult": (".model", "TrainingResult"),
    "command_fingerprint": (".validation", "command_fingerprint"),
    "label_run": (".validation", "label_run"),
    "validate_temporal": (".validation", "validate_temporal"),
    "write_validation_report": (".validation", "write_validation_report"),
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
    if name in _LAZY_NAMES:
        import importlib

        module_path, attr = _LAZY_NAMES[name]
        mod = importlib.import_module(module_path, __package__)
        value = getattr(mod, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'sage.ml' has no attribute {name!r}")
