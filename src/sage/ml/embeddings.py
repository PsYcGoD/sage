"""
Command Embedding Pipeline for SAGE ML V2.

Uses sentence-transformers (all-MiniLM-L6-v2) to convert commands
into 384-dimensional semantic vectors for similarity-based predictions.

Requires: pip install psycgod-sage[ml]
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    _HAS_ML_DEPS = True
except ImportError:
    _HAS_ML_DEPS = False

logger = logging.getLogger(__name__)


def _require_ml_deps():
    if not _HAS_ML_DEPS:
        raise ImportError(
            "ML V2 requires sentence-transformers, faiss-cpu, and numpy. "
            "Reinstall with: pip install --upgrade psycgod-sage"
        )


class CommandEmbedder:
    """
    Converts shell commands to semantic embeddings using all-MiniLM-L6-v2.

    Requires: sentence-transformers, torch (install via psycgod-sage[ml])
    """

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM = 384

    def __init__(self, cache_dir: Optional[Path] = None):
        _require_ml_deps()

        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "sage" / "models"

        cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Loading embedding model: {self.MODEL_NAME}")

        self.model = SentenceTransformer(
            self.MODEL_NAME,
            cache_folder=str(cache_dir),
            device="cpu",
        )

        self._cache: Dict[str, "np.ndarray"] = {}

        logger.info(f"Model loaded: {self.EMBEDDING_DIM}-dim embeddings")

    def embed(self, command: str) -> "np.ndarray":
        """Convert a command to a 384-dim embedding vector."""
        if command in self._cache:
            return self._cache[command]

        embedding = self.model.encode(
            command,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        self._cache[command] = embedding
        return embedding

    def embed_batch(self, commands: List[str], batch_size: int = 32) -> "np.ndarray":
        """Embed multiple commands efficiently."""
        uncached_indices = []
        uncached_commands = []

        for i, cmd in enumerate(commands):
            if cmd not in self._cache:
                uncached_indices.append(i)
                uncached_commands.append(cmd)

        if uncached_commands:
            logger.info(f"Encoding {len(uncached_commands)} commands...")

            new_embeddings = self.model.encode(
                uncached_commands,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=len(uncached_commands) > 100,
            )

            for i, cmd in enumerate(uncached_commands):
                self._cache[cmd] = new_embeddings[i]

        result = np.zeros((len(commands), self.EMBEDDING_DIM), dtype=np.float32)

        for i, cmd in enumerate(commands):
            result[i] = self._cache[cmd]

        return result

    def similarity(self, cmd1: str, cmd2: str) -> float:
        """Compute cosine similarity between two commands (0-1 scale)."""
        vec1 = self.embed(cmd1)
        vec2 = self.embed(cmd2)
        return float(np.dot(vec1, vec2))

    def clear_cache(self):
        """Clear the in-memory embedding cache."""
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        """Number of cached embeddings."""
        return len(self._cache)


class EmbeddingStore:
    """Persistent storage for command embeddings in SQLite."""

    def __init__(self, db_path: Path):
        _require_ml_deps()
        self.db_path = db_path
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    command TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_created
                ON embeddings(created_at)
            """)
            conn.commit()

    def store(self, command: str, embedding: "np.ndarray"):
        embedding_bytes = embedding.astype(np.float32).tobytes()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO embeddings (command, embedding) VALUES (?, ?)",
                (command, embedding_bytes),
            )
            conn.commit()

    def store_batch(self, commands: List[str], embeddings: "np.ndarray"):
        rows = [
            (cmd, emb.astype(np.float32).tobytes())
            for cmd, emb in zip(commands, embeddings)
        ]

        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO embeddings (command, embedding) VALUES (?, ?)",
                rows,
            )
            conn.commit()

        logger.info(f"Stored {len(commands)} embeddings in database")

    def load(self, command: str) -> Optional["np.ndarray"]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT embedding FROM embeddings WHERE command = ?",
                (command,),
            ).fetchone()

        if row is None:
            return None

        return np.frombuffer(row[0], dtype=np.float32).copy()

    def load_all(self) -> Tuple[List[str], "np.ndarray"]:
        """Load all stored embeddings. Returns (commands, embeddings_array)."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT command, embedding FROM embeddings ORDER BY created_at"
            ).fetchall()

        if not rows:
            return [], np.zeros((0, CommandEmbedder.EMBEDDING_DIM), dtype=np.float32)

        commands = [row[0] for row in rows]
        embeddings = np.array(
            [np.frombuffer(row[1], dtype=np.float32) for row in rows],
            dtype=np.float32,
        )

        logger.info(f"Loaded {len(commands)} embeddings from database")
        return commands, embeddings

    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]

    def delete_all(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM embeddings")
            conn.commit()


_global_embedder: Optional[CommandEmbedder] = None


def get_embedder() -> CommandEmbedder:
    """Get or create the global CommandEmbedder instance."""
    global _global_embedder

    if _global_embedder is None:
        _global_embedder = CommandEmbedder()

    return _global_embedder
