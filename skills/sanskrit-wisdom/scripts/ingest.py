"""Verse ingestion pipeline — fetch, normalize, embed, upsert to Qdrant.

Downloads Bhagavad Gita (700 verses) from vedicscriptures/bhagavad-gita
GitHub repo, merges with local stotras, embeds using sentence-transformers,
and stores in on-disk Qdrant collection.
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import httpx

# Paths
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GITA_DIR = DATA_DIR / "gita"
STOTRAS_PATH = DATA_DIR / "verses.json"
QDRANT_PATH = DATA_DIR / "qdrant_store"
GITA_NORMALIZED_PATH = DATA_DIR / "gita_normalized.json"

# Source
GITHUB_API = "https://api.github.com/repos/vedicscriptures/bhagavad-gita/contents/slok"
GITHUB_RAW = "https://raw.githubusercontent.com/vedicscriptures/bhagavad-gita/main/slok"

COLLECTION = "vedic_verses"
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# ── Gita chapter themes for tagging ──────────────────────────────────

CHAPTER_THEMES: dict[int, list[str]] = {
    1: ["arjuna", "grief", "confusion", "battlefield", "dharma"],
    2: ["sankhya", "yoga", "soul", "duty", "karma", "detachment", "equanimity"],
    3: ["karma", "yoga", "action", "duty", "selfless", "sacrifice"],
    4: ["jnana", "knowledge", "avatar", "dharma", "wisdom", "divine"],
    5: ["renunciation", "sannyasa", "karma", "yoga", "liberation"],
    6: ["meditation", "dhyana", "yoga", "mind", "discipline", "self"],
    7: ["knowledge", "divine", "maya", "devotion", "vishnu", "creation"],
    8: ["brahman", "death", "rebirth", "meditation", "om", "liberation"],
    9: ["devotion", "bhakti", "surrender", "divine", "vishnu", "grace"],
    10: ["vibhuti", "glory", "divine", "manifestation", "vishnu", "power"],
    11: ["vishvarupa", "cosmic", "form", "divine", "awe", "vishnu"],
    12: ["bhakti", "devotion", "surrender", "love", "worship", "vishnu"],
    13: ["kshetra", "field", "body", "soul", "knowledge", "prakriti"],
    14: ["gunas", "sattva", "rajas", "tamas", "nature", "liberation"],
    15: ["purushottama", "supreme", "tree", "soul", "divine", "vishnu"],
    16: ["divine", "demoniac", "qualities", "virtue", "vice", "dharma"],
    17: ["shraddha", "faith", "sattva", "food", "sacrifice", "austerity"],
    18: ["moksha", "liberation", "renunciation", "duty", "karma", "surrender"],
}


# ── Fetch ────────────────────────────────────────────────────────────

def fetch_verse_list() -> list[str]:
    """Get all verse filenames from the GitHub API."""
    resp = httpx.get(GITHUB_API, timeout=30)
    resp.raise_for_status()
    return sorted(item["name"] for item in resp.json())


def fetch_verse(filename: str) -> dict:
    """Download a single verse JSON from GitHub."""
    resp = httpx.get(f"{GITHUB_RAW}/{filename}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def _fetch_or_cache(fname: str, batch_pause: float) -> dict:
    """Fetch a single verse from GitHub or read from local cache."""
    cache_path = GITA_DIR / fname
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    raw = fetch_verse(fname)
    cache_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2))
    time.sleep(batch_pause)
    return raw


def fetch_all_gita(batch_pause: float = 0.05) -> list[dict]:
    """Fetch all Gita verses. Saves raw JSONs to gita/ dir."""
    GITA_DIR.mkdir(parents=True, exist_ok=True)
    filenames = fetch_verse_list()
    verses = [_fetch_or_cache(f, batch_pause) for f in filenames]
    print(f"  Total: {len(verses)} Gita verses")
    return verses


# ── Normalize ────────────────────────────────────────────────────────

def _best_english(raw: dict) -> str:
    """Extract the best English translation from available commentators."""
    for key in ("siva", "rpihtam", "chinmay", "purohit"):
        if key in raw and raw[key].get("et"):
            return raw[key]["et"]
    # Fallback: find any 'et' field
    for key, val in raw.items():
        if isinstance(val, dict) and val.get("et"):
            return val["et"]
    return ""


def normalize_gita(raw: dict) -> dict:
    """Convert a raw GitHub verse JSON into our standard schema."""
    ch = raw.get("chapter", 0)
    verse = raw.get("verse", 0)
    meaning = _best_english(raw)
    tags = CHAPTER_THEMES.get(ch, ["gita"]) + ["vishnu", "gita"]
    return {
        "id": f"bg-{ch}.{verse}",
        "devanagari": raw.get("slok", ""),
        "transliteration": raw.get("transliteration", ""),
        "meaning": meaning,
        "source": f"Bhagavad Gita {ch}.{verse}",
        "tags": list(set(tags)),
    }


def load_stotras() -> list[dict]:
    """Load the existing stotra corpus."""
    if not STOTRAS_PATH.exists():
        return []
    return json.loads(STOTRAS_PATH.read_text())


def normalize_all(gita_raw: list[dict]) -> list[dict]:
    """Normalize Gita + stotras into a unified corpus."""
    gita = [normalize_gita(r) for r in gita_raw]
    stotras = load_stotras()
    # Dedupe by id
    seen = {v["id"] for v in gita}
    stotras = [s for s in stotras if s["id"] not in seen]
    corpus = gita + stotras
    print(f"  Corpus: {len(gita)} Gita + {len(stotras)} stotras = {len(corpus)} total")
    return corpus


# ── Embed & Upsert ──────────────────────────────────────────────────

def _embed_corpus(corpus: list[dict]) -> tuple:
    """Load model and embed all verses. Returns (embeddings, dim)."""
    from sentence_transformers import SentenceTransformer

    print(f"  Loading embedding model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)
    texts = [f"{v['meaning']} {' '.join(v['tags'])}" for v in corpus]
    print(f"  Embedding {len(texts)} verses ({model.get_sentence_embedding_dimension()}d)...")
    return model.encode(texts, show_progress_bar=True, batch_size=64), model.get_sentence_embedding_dimension()


def _upsert_to_qdrant(corpus: list[dict], embeddings, dim: int) -> int:
    """Create/recreate Qdrant collection and upsert all vectors."""
    from qdrant_client import QdrantClient, models

    QDRANT_PATH.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(QDRANT_PATH))
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(COLLECTION, vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE))
    points = [models.PointStruct(id=i, vector=embeddings[i].tolist(), payload=corpus[i]) for i in range(len(corpus))]
    client.upsert(COLLECTION, points=points, wait=True)
    print(f"  Upserted {len(points)} vectors to Qdrant at {QDRANT_PATH}")
    return len(points)


def embed_and_upsert(corpus: list[dict]) -> int:
    """Embed verse text and upsert into on-disk Qdrant collection."""
    embeddings, dim = _embed_corpus(corpus)
    return _upsert_to_qdrant(corpus, embeddings, dim)


# ── Main ─────────────────────────────────────────────────────────────

def main():
    """Full pipeline: fetch → normalize → embed → upsert."""
    print("1. Fetching Bhagavad Gita from GitHub...")
    gita_raw = fetch_all_gita()

    print("2. Normalizing corpus...")
    corpus = normalize_all(gita_raw)

    # Save normalized for inspection
    GITA_NORMALIZED_PATH.write_text(json.dumps(corpus, ensure_ascii=False, indent=2))
    print(f"   Saved normalized corpus to {GITA_NORMALIZED_PATH}")

    print("3. Embedding & upserting to Qdrant...")
    count = embed_and_upsert(corpus)

    print(f"\nDone. {count} verses indexed in Qdrant.")


if __name__ == "__main__":
    main()
