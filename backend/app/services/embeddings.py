import hashlib
import math

import requests

from app.config import settings


def _hash_embedding(text: str) -> list[float]:
    dimensions = settings.embeddings_dimensions
    vector = [0.0] * dimensions
    words = [word for word in text.lower().split() if word]
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def build_embedding_text(property_item: dict) -> str:
    parts = [
        property_item.get("title"),
        property_item.get("description"),
        property_item.get("raw_text"),
        property_item.get("city"),
        property_item.get("zone"),
        property_item.get("neighborhood"),
        property_item.get("property_type"),
        property_item.get("operation"),
        " ".join(property_item.get("features") or []),
    ]
    return " ".join(str(part) for part in parts if part).strip()


def generate_embedding(text: str) -> list[float] | None:
    clean_text = " ".join((text or "").split())
    if not clean_text:
        return None

    if settings.embeddings_provider.lower() != "ollama":
        return _hash_embedding(clean_text)

    try:
        response = requests.post(
            f"{settings.ollama_url.rstrip('/')}/api/embeddings",
            json={"model": settings.embeddings_model, "prompt": clean_text},
            timeout=30,
        )
        response.raise_for_status()
        embedding = response.json().get("embedding")
        if isinstance(embedding, list) and len(embedding) == settings.embeddings_dimensions:
            return [float(value) for value in embedding]
    except Exception:
        return _hash_embedding(clean_text)

    return _hash_embedding(clean_text)


def to_pgvector_literal(embedding: list[float] | None) -> str | None:
    if not embedding:
        return None
    return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"
