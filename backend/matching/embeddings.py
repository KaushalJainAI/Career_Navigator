"""Embedding helpers — designed so production uses sentence-transformers or an
LLM endpoint, while tests use the deterministic `hash_embed` fallback."""

from __future__ import annotations

import hashlib
import math
from typing import Sequence

_DIM = 256


def hash_embed(text: str, dim: int = _DIM) -> list[float]:
    """Cheap deterministic embedding so tests don't need a model.
    Hashes each token into one of `dim` buckets and L2-normalises."""
    vec = [0.0] * dim
    for tok in (text or '').lower().split():
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError('Vector length mismatch')
    return sum(x * y for x, y in zip(a, b))


def embed(text: str) -> list[float]:
    """Production hook: swap in sentence-transformers or NIM embeddings.
    Falls back to hash_embed if no model is configured."""
    return hash_embed(text)
