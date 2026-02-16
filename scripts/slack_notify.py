"""Slack notification — send compact weekly digest + janam patri via webhook."""
from __future__ import annotations

import os
import re
from pathlib import Path

import httpx

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_MEMBER_ID = os.getenv("SLACK_MEMBER_ID", "")
SLACK_MENTION = os.getenv("SLACK_MENTION", "")


def _clean_meaning(text: str) -> str:
    """Normalize spacing and drop duplicated verse prefixes like '7.3 '."""
    clean = re.sub(r"^\s*\d+\.\d+\s*", "", text or "")
    return re.sub(r"\s+", " ", clean).strip()


def _compact_verse_line(v: dict | None) -> str:
    """Compact multi-line verse summary for Slack including Sanskrit."""
    if not v:
        return "No verse matched."
    devanagari = (v.get("devanagari") or "").strip()
    transliteration = (v.get("transliteration") or "").strip()
    source = v.get("source", "Verse")
    meaning = _clean_meaning(v.get("meaning", ""))
    parts = [p for p in [devanagari, transliteration, f"{meaning} [{source}]"] if p]
    return "\n".join(parts)


def _weekly_block() -> str:
    """Compact weekly block: panchang + verse of week."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from weekly_notification import build_digest

    digest, _ = build_digest()
    lines = [
        "Weekly Panchang",
        f"Week: {digest.week_start} -> {digest.week_end}",
    ]
    for p in digest.panchang_days:
        lines.append(f"- {p.date} ({p.vaara}) | {p.paksha} {p.tithi} | {p.nakshatra} | Sunrise {p.sunrise}")

    lines += [
        "",
        "Shloka of the Week",
        _compact_verse_line(digest.verse),
    ]
    if digest.lifestyle_recommendations:
        lines += ["", "Lifestyle Recommendations"]
        lines += [f"- {r}" for r in digest.lifestyle_recommendations]
    return "\n".join(lines)


def _janam_patri_block() -> str:
    """Format janam patri recommendations in compact Slack style."""
    root = Path(__file__).resolve().parent.parent
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from janam_patri import run_to_dict
    jp = run_to_dict(root / "config.yaml")
    if not jp:
        return ""

    verses = jp.get("verses", [])
    influenced = verses[0] if verses else None
    others = verses[1:4] if len(verses) > 1 else []

    lines = [
        "",
        "Janam Patri",
        f"Janma Nakshatra: {jp['janma_nakshatra']} | Rashi: {jp['rashi']}",
        "Janam-Patri Influenced Shloka of the Week",
        _compact_verse_line(influenced),
    ]
    if others:
        lines.append("Other Recommendations")
        for idx, v in enumerate(others, start=1):
            lines.append(f"{idx}.\n{_compact_verse_line(v)}")
    lifestyle = jp.get("lifestyle_recommendations", [])
    if lifestyle:
        lines.append("Janam-Patri Lifestyle Guidance")
        lines += [f"- {r}" for r in lifestyle]
    return "\n".join(lines).rstrip()


def send_digest(digest_text: str) -> dict:
    """POST digest to Slack Incoming Webhook. Returns response or skip message."""
    if not SLACK_WEBHOOK_URL:
        return {"status": "skipped", "reason": "SLACK_WEBHOOK_URL not set"}

    digest_text = digest_text + "\n" + _janam_patri_block()
    if SLACK_MEMBER_ID:
        digest_text = f"<@{SLACK_MEMBER_ID}>\n{digest_text}"
    elif SLACK_MENTION:
        digest_text = f"{SLACK_MENTION}\n{digest_text}"

    resp = httpx.post(SLACK_WEBHOOK_URL, json={"text": digest_text}, timeout=30)
    resp.raise_for_status()
    return {"status": "sent", "code": resp.status_code}


if __name__ == "__main__":
    digest = _weekly_block()
    print(digest + "\n" + _janam_patri_block())
    print("\n--- Sending to Slack ---")
    result = send_digest(digest)
    print(result)
