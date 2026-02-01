"""Sanskrit verse search — RAG over Gita & Vishnu Sahasranama.

Searches a local JSON corpus with Qdrant semantic search (preferred)
or keyword fallback. Returns verses in Devanagari + transliteration + meaning format.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
VERSES_PATH = DATA_DIR / "verses.json"
QDRANT_PATH = DATA_DIR / "qdrant_store"
COLLECTION_NAME = "vedic_verses"
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


@dataclass
class Verse:
    id: str
    devanagari: str
    transliteration: str
    meaning: str
    source: str
    tags: list[str]


def load_verses() -> list[Verse]:
    """Load the verse corpus from JSON."""
    if not VERSES_PATH.exists():
        return []
    raw = json.loads(VERSES_PATH.read_text())
    return [Verse(**v) for v in raw]


def _get_qdrant_client() -> "QdrantClient | None":
    """Connect to on-disk Qdrant store; returns None if path missing."""
    if not QDRANT_PATH.exists():
        return None
    from qdrant_client import QdrantClient
    return QdrantClient(path=str(QDRANT_PATH))


@lru_cache(maxsize=1)
def _get_embedder() -> "SentenceTransformer":
    """Lazy-load the multilingual sentence transformer (cached at module level)."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL)


def semantic_search(query: str, top_k: int = 3) -> list[Verse]:
    """Encode query and search Qdrant; returns Verse objects from payloads."""
    client = _get_qdrant_client()
    if client is None:
        return []
    embedding = _get_embedder().encode(query).tolist()
    result = client.query_points(collection_name=COLLECTION_NAME, query=embedding, limit=top_k)
    return [Verse(**pt.payload) for pt in result.points]


def keyword_search(query: str, top_k: int = 3) -> list[Verse]:
    """Keyword search over verses. Returns top_k matches."""
    query_lower = query.lower()
    verses = load_verses()
    scored = [
        (v, sum(t in query_lower for t in v.tags) + (query_lower in v.meaning.lower()))
        for v in verses
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [v for v, s in scored[:top_k] if s > 0]


def search(query: str, top_k: int = 3) -> list[Verse]:
    """Semantic search with keyword fallback when Qdrant store is unavailable."""
    return semantic_search(query, top_k) or keyword_search(query, top_k)


def format_verse(v: Verse) -> str:
    """Format a verse with all three representations."""
    return f"{v.devanagari}\n{v.transliteration}\n— {v.meaning}\n[{v.source}]"


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "karma yoga"
    results = search(query)
    if not results:
        print(f"No verses found for: {query}")
    for v in results:
        print(format_verse(v))
        print()
