"""Slack notification — send weekly digest + janam patri via Incoming Webhook.

Uses httpx to POST the formatted digest to a Slack channel.
Gracefully skips when SLACK_WEBHOOK_URL is not set (local dev).
"""
from __future__ import annotations

import os
from pathlib import Path

import httpx

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_MEMBER_ID = os.getenv("SLACK_MEMBER_ID", "")


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
        "═══ Janam Patri — Birth chart shlokas ═══",
        f"Birth: {jp['birth_date']} {jp['birth_time']} ({jp.get('birth_place', '')})",
        f"Janma Nakshatra: {jp['janma_nakshatra']} · Rashi: {jp['rashi']}",
        "",
        "Recommended verses:",
    ]
    for v in jp.get("verses", [])[:3]:
        lines += [v["devanagari"], v["transliteration"], f"— {v['meaning']} [{v['source']}]", ""]
    return "\n".join(lines)


def send_digest(digest_text: str) -> dict:
    """POST digest to Slack Incoming Webhook. Returns response or skip message."""
    if not SLACK_WEBHOOK_URL:
        return {"status": "skipped", "reason": "SLACK_WEBHOOK_URL not set"}

    digest_text = digest_text + _janam_patri_block()
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
