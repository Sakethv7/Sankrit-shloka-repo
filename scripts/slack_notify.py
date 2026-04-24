"""Slack notification — send compact weekly digest + janam patri via webhook."""
from __future__ import annotations

import os
import re
from pathlib import Path

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_MEMBER_ID = os.getenv("SLACK_MEMBER_ID", "")
SLACK_MENTION = os.getenv("SLACK_MENTION", "")

EN_DAY = {"Ravivara":"Sun","Somavara":"Mon","Mangalavara":"Tue","Budhavara":"Wed",
          "Guruvara":"Thu","Shukravara":"Fri","Shanivara":"Sat"}


def _dashboard_url() -> str:
    if os.getenv("DASHBOARD_URL"):
        return os.getenv("DASHBOARD_URL", "")
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if "/" not in repo:
        return ""
    owner, name = repo.split("/", 1)
    return f"https://{owner.lower()}.github.io/{name}/"


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


def _stars(n: int) -> str:
    return "★" * n + "☆" * (5 - n)


def _observance_lines(days: list) -> list[str]:
    obs = [f"- {d.date} — {d.observance} ({d.deity_of_day})" for d in days if d.observance]
    return obs or ["- None this week"]


def _day_line(day) -> str:
    p = day.panchang
    obs = f" | {day.observance}" if day.observance else ""
    vaara = EN_DAY.get(p.vaara, p.vaara)
    return (
        f"- {day.date} {vaara} | {_stars(day.day_score)} | "
        f"{p.paksha} {p.tithi} | {p.nakshatra} | Sunrise {day.sunrise}{obs}"
    )


def _practice_line(day) -> str:
    vaara = EN_DAY.get(day.panchang.vaara, day.panchang.vaara)
    return f"- {day.date} {vaara}: {day.practice}"


def _header_lines(digest: dict, chart, loc) -> list[str]:
    dashboard_url = _dashboard_url()
    lines = [
        "Vedic Wisdom Weekly",
        f"Week: {digest['week_start']} -> {digest['week_end']}",
        f"Practice location: {loc.city} ({loc.timezone})",
        f"Janma: {chart.janma_nakshatra} | Rashi: {chart.rashi}",
    ]
    return lines + ([f"Dashboard: {dashboard_url}"] if dashboard_url else [])


def _overview_lines(days: list) -> list[str]:
    best = [d for d in days if d.day_score == 5]
    caution = [d for d in days if d.day_score <= 2]
    return [
        "",
        "Week Overview",
        "Observances:",
        *_observance_lines(days),
        f"Best days: {', '.join(str(d.date) for d in best) or 'None'}",
        f"Caution days: {', '.join(str(d.date) for d in caution) or 'None'}",
    ]


def _weekly_block() -> str:
    """Compact weekly block from the canonical weekly guidance engine."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from weekly_guidance import build_week, week_to_dict
    import datetime as dt

    days, chart, loc = build_week(dt.date.today(), write_history=False)
    digest = week_to_dict(days, chart, loc)
    lines = _header_lines(digest, chart, loc) + _overview_lines(days)
    lines += ["", "Daily Panchang + Score", *[_day_line(day) for day in days]]
    lines += [
        "",
        "Shloka of the Week",
        _compact_verse_line(digest["verse_of_week"]),
    ]
    lines += [
        "",
        "Practice Guidance",
        *[_practice_line(day) for day in days],
    ]
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
        lines += [f"{idx}.\n{_compact_verse_line(v)}" for idx, v in enumerate(others, start=1)]
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

    import httpx
    resp = httpx.post(SLACK_WEBHOOK_URL, json={"text": digest_text}, timeout=30)
    resp.raise_for_status()
    return {"status": "sent", "code": resp.status_code}


if __name__ == "__main__":
    digest = _weekly_block()
    print(digest + "\n" + _janam_patri_block())
    print("\n--- Sending to Slack ---")
    result = send_digest(digest)
    print(result)
