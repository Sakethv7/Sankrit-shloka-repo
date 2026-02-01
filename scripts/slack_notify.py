"""Slack notification — send weekly digest via Incoming Webhook.

Uses httpx to POST the formatted digest to a Slack channel.
Gracefully skips when SLACK_WEBHOOK_URL is not set (local dev).
"""
from __future__ import annotations

import os
import re

import httpx

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_MEMBER_ID = os.getenv("SLACK_MEMBER_ID", "")

_NO_OBS_RE = re.compile(r"No major observances this week\\.", re.IGNORECASE)


def _should_mention(digest_text: str) -> bool:
    """Mention only when at least one observance exists."""
    if not SLACK_MEMBER_ID:
        return False
    return "Observances This Week:" in digest_text and not _NO_OBS_RE.search(digest_text)


def send_digest(digest_text: str) -> dict:
    """POST digest to Slack Incoming Webhook. Returns response or skip message."""
    if not SLACK_WEBHOOK_URL:
        return {"status": "skipped", "reason": "SLACK_WEBHOOK_URL not set"}

    if _should_mention(digest_text):
        digest_text = f"<@{SLACK_MEMBER_ID}>\\n{digest_text}"

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
