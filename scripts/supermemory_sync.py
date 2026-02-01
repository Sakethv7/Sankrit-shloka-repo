"""Supermemory sync — push weekly digests to long-term memory.

Uses the Supermemory API to store past notifications so Claude Desktop
can recall them via MCP context.
"""
from __future__ import annotations

import os
import json
import datetime as dt

import httpx

SUPERMEMORY_URL = "https://api.supermemory.com/v1/memories"
API_KEY = os.getenv("SUPERMEMORY_API_KEY", "")


def sync_digest(digest_text: str, metadata: dict | None = None) -> dict:
    """Push a weekly digest to Supermemory.

    Returns the API response or an error dict if the key is missing.
    """
    if not API_KEY:
        return {"error": "SUPERMEMORY_API_KEY not set — skipping sync"}

    payload = {
        "content": digest_text,
        "metadata": metadata or {"source": "vedic-wisdom-weekly", "date": dt.date.today().isoformat()},
    }
    resp = httpx.post(SUPERMEMORY_URL, json=payload, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def list_memories(limit: int = 10) -> list[dict]:
    """Fetch recent memories from Supermemory."""
    if not API_KEY:
        return []

    resp = httpx.get(
        SUPERMEMORY_URL,
        params={"limit": limit},
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("memories", [])


if __name__ == "__main__":
    from weekly_notification import generate_weekly

    digest = generate_weekly()
    result = sync_digest(digest)
    print(json.dumps(result, indent=2))
