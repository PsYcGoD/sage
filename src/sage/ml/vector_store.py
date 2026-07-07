"""
Vector Similarity Search using FAISS for SAGE ML V2.

Finds similar historical commands based on semantic embeddings
to predict success/failure outcomes.

Requires: pip install psycgod-sage[ml]
"""

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import faiss
    import numpy as np

    _HAS_ML_DEPS = True
except ImportError:
    _HAS_ML_DEPS = False

from sage.ml.embeddings import CommandEmbedder, _require_ml_deps

logger = logging.getLogger(__name__)


@dataclass
class CommandOutcome:
    """Historical command outcome for prediction."""

    command: str
    success: bool
    exit_code: int
    distance: float
    similarity: float


class CommandVectorStore:
    """
    FAISS-based vector store for finding similar historical commands.

    Uses L2 distance on normalized embeddings (equivalent to cosine similarity).
    """

    def __init__(
        self,
        embedder: CommandEmbedder,
        db_path: Path,
        index_type: str = "flat",
    ):
        _require_ml_deps()

        self.embedder = embedder
        self.db_path = db_path
        self.index_type = index_type

        self.index: Optional["faiss.IndexFlatL2"] = None
        self.commands: List[Tuple[str, bool, int]] = []
        self._num_indexed = 0

    def build_index(self, min_commands: int = 10):
        """
        Build FAISS index from historical command data.

        Args:
            min_commands: Minimum commands required to build index (default 10)

        Raises:
            ValueError: If not enough commands in database
        """
        logger.info("Building vector index from command history...")

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT DISTINCT command, exit_code
                FROM runs
                WHERE command IS NOT NULL
                  AND command != ''
                  AND exit_code IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 10000
            """).fetchall()

        if len(rows) < min_commands:
            raise ValueError(
                f"Not enough commands in database: {len(rows)} < {min_commands}. "
                f"Run more commands through SAGE to build history."
            )

        logger.info(f"Found {len(rows)} historical commands")

        commands = [row[0] for row in rows]
        exit_codes = [row[1] for row in rows]
        successes = [code == 0 for code in exit_codes]

        logger.info("Embedding commands...")
        embeddings = self.embedder.embed_batch(commands, batch_size=64)

        if self.index_type == "flat":
            self.index = faiss.IndexFlatL2(self.embedder.EMBEDDING_DIM)
        else:
            raise NotImplementedError(f"Index type '{self.index_type}' not yet supported")

        self.index.add(embeddings.astype(np.float32))

        self.commands = list(zip(commands, successes, exit_codes))
        self._num_indexed = len(commands)

        logger.info(f"Index built: {self._num_indexed} commands indexed")

    def search(
        self,
        query_command: str,
        k: int = 10,
        max_distance: float = 2.0,
    ) -> List[CommandOutcome]:
        """Find K most similar historical commands."""
        if self.index is None:
            raise RuntimeError("Index not built. Call build_index() first.")

        query_vec = self.embedder.embed(query_command).astype(np.float32)
        query_vec = query_vec.reshape(1, -1)

        distances, indices = self.index.search(query_vec, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or dist > max_distance:
                continue

            command, success, exit_code = self.commands[idx]

            # For normalized vectors: cos_sim = 1 - (L2_dist^2 / 2)
            similarity = max(0.0, 1.0 - (dist / 2.0))

            results.append(CommandOutcome(
                command=command,
                success=success,
                exit_code=exit_code,
                distance=float(dist),
                similarity=float(similarity),
            ))

        return results

    def predict_success(
        self,
        query_command: str,
        k: int = 10,
        weight_by_distance: bool = True,
    ) -> Tuple[float, List[CommandOutcome]]:
        """
        Predict success probability for a command based on similar neighbors.

        Returns:
            (success_probability, neighbors) tuple
        """
        neighbors = self.search(query_command, k=k)

        if not neighbors:
            return 0.5, []

        if not weight_by_distance:
            success_rate = sum(n.success for n in neighbors) / len(neighbors)
            return success_rate, neighbors

        weights = [1.0 / (1.0 + n.distance) for n in neighbors]
        total_weight = sum(weights)

        weighted_successes = sum(
            w * n.success for w, n in zip(weights, neighbors)
        )

        success_prob = weighted_successes / total_weight
        return success_prob, neighbors

    def explain_prediction(self, query_command: str, k: int = 5) -> str:
        """Generate human-readable explanation of prediction."""
        prob, neighbors = self.predict_success(query_command, k=k)

        lines = [f"Based on {len(neighbors)} similar commands:"]

        for n in neighbors[:k]:
            status = "✅" if n.success else "❌"
            exit_info = f" [exit: {n.exit_code}]" if not n.success else ""
            lines.append(
                f"  {status} {n.command} (similarity: {n.similarity:.2f}){exit_info}"
            )

        lines.append(f"\nSuccess probability: {prob * 100:.0f}%")
        return "\n".join(lines)

    @property
    def size(self) -> int:
        """Number of commands in the index."""
        return self._num_indexed

    def save(self, path: Path):
        """Save FAISS index to disk."""
        if self.index is None:
            raise RuntimeError("No index to save")
        faiss.write_index(self.index, str(path))
        logger.info(f"Index saved to {path}")

    def load(self, path: Path):
        """Load FAISS index from disk."""
        self.index = faiss.read_index(str(path))
        self._num_indexed = self.index.ntotal
        logger.info(f"Index loaded from {path}: {self._num_indexed} commands")


def _index_cache_path(db_path: Path) -> Path:
    """Path to cached FAISS index file next to the database."""
    return db_path.parent / "ml_v2_index.faiss"


def _metadata_cache_path(db_path: Path) -> Path:
    """Path to cached command metadata file."""
    return db_path.parent / "ml_v2_commands.npy"


def build_vector_store(db_path: Path, use_cache: bool = True) -> CommandVectorStore:
    """Build a ready-to-use vector store from SAGE's database.

    Caches the FAISS index to disk so subsequent loads are instant.
    """
    _require_ml_deps()
    embedder = CommandEmbedder()
    store = CommandVectorStore(embedder, db_path)

    index_path = _index_cache_path(db_path)
    meta_path = _metadata_cache_path(db_path)

    if use_cache and index_path.exists() and meta_path.exists():
        try:
            import json
            store.load(index_path)
            meta = np.load(str(meta_path), allow_pickle=True).item()
            store.commands = meta["commands"]
            store._num_indexed = len(store.commands)
            logger.info(f"Loaded cached index: {store.size} commands")
            return store
        except Exception as e:
            logger.warning(f"Cache load failed, rebuilding: {e}")

    store.build_index()

    if use_cache:
        try:
            store.save(index_path)
            meta = {"commands": store.commands}
            np.save(str(meta_path), meta, allow_pickle=True)
            logger.info(f"Cached index to {index_path}")
        except Exception as e:
            logger.warning(f"Failed to cache index: {e}")

    return store
