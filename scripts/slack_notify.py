"""Slack notification — send weekly digest + janam patri via Incoming Webhook.

Uses httpx to POST the formatted digest to a Slack channel.
Gracefully skips when SLACK_WEBHOOK_URL is not set (local dev).
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

import httpx

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_MEMBER_ID = os.getenv("SLACK_MEMBER_ID", "")


def _strip_diacritics(text: str) -> str:
    """Convert transliteration with diacritics to plain ASCII-style text."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_marks.replace("\n", " ")).strip()


def _clean_meaning(text: str) -> str:
    """Normalize spacing and drop duplicated verse prefixes like '7.3 '."""
    clean = re.sub(r"^\s*\d+\.\d+\s*", "", text or "")
    return re.sub(r"\s+", " ", clean).strip()


def _janam_patri_block() -> str:
    """Format janam patri as text block for Slack; empty if disabled."""
    root = Path(__file__).resolve().parent.parent
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from janam_patri import run_to_dict
    jp = run_to_dict(root / "config.yaml")
    if not jp:
        return ""

    lines = [
        "",
        "Janam Patri",
        f"Birth: {jp['birth_date']} {jp['birth_time']} ({jp.get('birth_place', '')})",
        f"Janma Nakshatra: {jp['janma_nakshatra']} | Rashi: {jp['rashi']}",
        "Recommended verses:",
    ]

    for idx, v in enumerate(jp.get("verses", [])[:3], start=1):
        lines += [
            f"{idx}. {v['source']}",
            f"   Transliteration: {_strip_diacritics(v.get('transliteration', ''))}",
            f"   Meaning: {_clean_meaning(v.get('meaning', ''))}",
            "",
        ]
    return "\n".join(lines).rstrip()


def send_digest(digest_text: str) -> dict:
    """POST digest to Slack Incoming Webhook. Returns response or skip message."""
    if not SLACK_WEBHOOK_URL:
        return {"status": "skipped", "reason": "SLACK_WEBHOOK_URL not set"}

    digest_text = digest_text + "\n" + _janam_patri_block()
    if SLACK_MEMBER_ID:
        digest_text = f"<@{SLACK_MEMBER_ID}>\n{digest_text}"

    resp = httpx.post(SLACK_WEBHOOK_URL, json={"text": digest_text}, timeout=30)
    resp.raise_for_status()
    return {"status": "sent", "code": resp.status_code}


if __name__ == "__main__":
    from weekly_notification import generate_weekly

    digest = generate_weekly()
    print(digest)
    print("\n--- Sending to Slack ---")
    result = send_digest(digest)
    print(result)
