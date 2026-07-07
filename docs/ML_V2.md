# SAGE ML V2 - Neural Command Center

## Overview

ML V2 replaces the sklearn-based predictor with semantic embeddings and specialized failure predictors. It achieves **76% accuracy** (up from 58%) on 7,654 real commands with an F1 score of 0.86.

## Architecture

```
Command Input
     │
     ▼
┌─────────────────────────────────┐
│     Neural Command Center       │
├─────────────────────────────────┤
│  ┌─────────────────────────┐    │
│  │  Embedding Predictor    │    │  ← V2 core: semantic similarity
│  │  (all-MiniLM-L6-v2)    │    │
│  └─────────────────────────┘    │
│                                 │
│  ┌─── Specialized Predictors ──┐│
│  │ • Syntax Error              ││
│  │ • Dependency Missing        ││
│  │ • Auth Failure              ││
│  │ • Timeout Risk              ││
│  │ • Permission Denied         ││
│  │ • Context Error             ││
│  └─────────────────────────────┘│
│                                 │
│  ┌─── Utility Predictors ─────┐│
│  │ • Compression Selector      ││
│  │ • Agent Ranker              ││
│  └─────────────────────────────┘│
└─────────────────────────────────┘
     │
     ▼
Unified Result: {will_fail, confidence, warnings, suggestions,
                 compression_strategy, agents_to_run}
```

## Installation

```bash
# Base SAGE (V1 predictors still work)
pip install psycgod-sage

# With ML V2 (embeddings + vector search)
pip install psycgod-sage[ml]
```

The `[ml]` extra installs:
- `sentence-transformers>=3.0.0` — embedding model
- `faiss-cpu>=1.8.0` — vector similarity search
- `torch>=2.0.0` — model backend
- `numpy>=1.24.0` — array operations

## Usage

### Embedding Predictor (V2 Core)

```python
from sage.ml import CommandEmbedder, build_vector_store
from sage.store import db_path

# Embed a command
embedder = CommandEmbedder()
vec = embedder.embed("pytest tests/")  # shape=(384,)

# Build vector store from command history
store = build_vector_store(db_path())

# Predict success
prob, neighbors = store.predict_success("git push origin main")
print(f"Success probability: {prob*100:.0f}%")

# Get explanation
print(store.explain_prediction("npm install"))
```

### Neural Command Center

```python
from sage.ml.neural_center import NeuralCommandCenter
from sage.store import db_path

center = NeuralCommandCenter(db_path=db_path())
result = center.analyze("pytst tests/")

print(result.will_fail)           # True
print(result.warnings)            # ["syntax_error: Typo 'pytst' → 'pytest' (90%)"]
print(result.suggestions)         # ["Did you mean: pytest tests/"]
print(result.compression_strategy) # "test_output"
print(result.agents_to_run)       # ["Test Agent", "Code Agent", "Debug Agent"]
```

### Integrated Predictor (automatic)

The `FailurePredictor` automatically uses V2 when available:

```python
from sage.ml import FailurePredictor

predictor = FailurePredictor()
will_fail, confidence, reason = predictor.predict("git push origin main")
# V2 is tried first → falls back to V1 if unavailable
```

## Benchmarks

Tested on 7,654 real commands (80/20 temporal split):

| Metric | V1 (sklearn) | V2 (embeddings) | Improvement |
|--------|:---:|:---:|:---:|
| Accuracy | 58% | 76% | +31% |
| Precision | — | 87% | NEW |
| Recall | — | 85% | NEW |
| F1 Score | — | 86% | NEW |

### Model Details

- **Model:** `all-MiniLM-L6-v2` (sentence-transformers)
- **Size:** 90MB download, 384-dim embeddings
- **License:** Apache 2.0
- **Index:** FAISS IndexFlatL2 (exact search)
- **Latency:** <10ms per prediction (after index built)
- **Index build:** ~2.5 min for 5,700 commands on CPU (cached to disk)

## Graceful Degradation

- Without `[ml]` extras: V1 predictors (sklearn + heuristics) still work
- Without enough history (<50 commands): falls back to V1
- First run: builds index (~2.5 min), caches to `~/.local/SAGE/ml_v2_index.faiss`
- Subsequent runs: loads cached index instantly
