"""ML V2 validation: measure accuracy on real command history with train/test split."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import List, Tuple

from .embeddings import CommandEmbedder, _require_ml_deps

try:
    import numpy as np
    import faiss
except ImportError:
    pass

logger = logging.getLogger(__name__)


def validate_v2(db_path: Path, test_ratio: float = 0.2) -> dict:
    """
    Run 80/20 temporal split validation on V2 embeddings.

    Returns dict with accuracy, precision, recall, and comparison data.
    """
    _require_ml_deps()

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("""
            SELECT command, exit_code, created_at
            FROM runs
            WHERE command IS NOT NULL
              AND command != ''
              AND exit_code IS NOT NULL
            ORDER BY created_at ASC
        """).fetchall()

    if len(rows) < 50:
        return {"error": f"Not enough data: {len(rows)} rows (need 50+)"}

    commands = [r[0] for r in rows]
    labels = [1 if r[1] == 0 else 0 for r in rows]  # 1=success, 0=failure

    split_idx = int(len(rows) * (1 - test_ratio))
    train_cmds, test_cmds = commands[:split_idx], commands[split_idx:]
    train_labels, test_labels = labels[:split_idx], labels[split_idx:]

    logger.info(f"Train: {len(train_cmds)}, Test: {len(test_cmds)}")

    embedder = CommandEmbedder()

    train_embeddings = embedder.embed_batch(train_cmds, batch_size=64)
    test_embeddings = embedder.embed_batch(test_cmds, batch_size=64)

    index = faiss.IndexFlatL2(embedder.EMBEDDING_DIM)
    index.add(train_embeddings.astype(np.float32))

    k = 10
    distances, indices = index.search(test_embeddings.astype(np.float32), k)

    correct = 0
    true_positives = 0
    false_positives = 0
    false_negatives = 0

    for i in range(len(test_cmds)):
        neighbors_idx = indices[i]
        neighbor_dists = distances[i]

        weights = [1.0 / (1.0 + d) for d in neighbor_dists if d >= 0]
        total_weight = sum(weights)

        if total_weight == 0:
            predicted_success_prob = 0.5
        else:
            weighted_success = sum(
                w * train_labels[idx]
                for w, idx in zip(weights, neighbors_idx)
                if idx >= 0
            )
            predicted_success_prob = weighted_success / total_weight

        predicted_success = predicted_success_prob >= 0.5
        actual_success = test_labels[i] == 1

        if predicted_success == actual_success:
            correct += 1
        if predicted_success and actual_success:
            true_positives += 1
        if predicted_success and not actual_success:
            false_positives += 1
        if not predicted_success and actual_success:
            false_negatives += 1

    accuracy = correct / len(test_cmds)
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    results = {
        "total_commands": len(rows),
        "train_size": len(train_cmds),
        "test_size": len(test_cmds),
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "correct": correct,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }

    return results
