"""
Vedic Wisdom — modern dashboard over SQLite metadata.
Run from repo root: streamlit run dashboard/streamlit_app.py
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().parent / "data" / "vedic_wisdom.db"


def _query(sql: str, params: tuple = ()) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as c:
        return pd.read_sql(sql, c, params=params if params else None)


def _strip_diacritics(text: str) -> str:
    if text is None or pd.isna(text):
        return ""
    normalized = unicodedata.normalize("NFKD", str(text))
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_marks).strip()


def _clean_meaning(text: str) -> str:
    if text is None or pd.isna(text):
        return ""
    clean = re.sub(r"^\s*\d+\.\d+\s*", "", str(text or ""))
    return re.sub(r"\s+", " ", clean).strip()


st.set_page_config(page_title="Vedic Wisdom", page_icon="📿", layout="wide")
st.title("📿 Vedic Wisdom")
st.caption("Panchang, janam patri, and recommendation history from your metadata")

if not DB_PATH.exists():
    st.warning("No database yet. Run: `python scripts/export_to_sqlite.py`")
    st.stop()

page = st.sidebar.radio("Go to", ["This week", "Janam patri", "History", "Insights"], label_visibility="collapsed")

if page == "This week":
    st.header("This week's panchang (EST)")
    weeks = _query("SELECT week_start, week_end FROM weeks ORDER BY week_start DESC LIMIT 1")
    if weeks.empty:
        st.info("No week data. Run `python scripts/export_to_sqlite.py`.")
    else:
        w = weeks.iloc[0]
        st.subheader(f"{w['week_start']} → {w['week_end']}")
        days = _query("SELECT date, vaara, tithi, paksha, nakshatra, sunrise FROM panchang_days WHERE week_start = ?", (w["week_start"],))
        if not days.empty:
            st.dataframe(days, use_container_width=True, hide_index=True)
        obs = _query("SELECT date, name, deity, description FROM observances WHERE week_start = ?", (w["week_start"],))
        if not obs.empty:
            st.subheader("Observances")
            st.dataframe(obs, use_container_width=True, hide_index=True)
        st.subheader("Shloka by tithi")
        verses = _query("SELECT date, tithi, paksha, devanagari, transliteration, meaning, source FROM daily_verses WHERE week_start = ? ORDER BY date", (w["week_start"],))
        for _, row in verses.iterrows():
            with st.expander(f"{row['date']} — {row['paksha']} {row['tithi']}"):
                if pd.notna(row["transliteration"]) or pd.notna(row["meaning"]):
                    st.write(f"Transliteration: {_strip_diacritics(row['transliteration'])}")
                    st.caption(f"Meaning: {_clean_meaning(row['meaning'])}")
                    st.caption(f"Source: {row['source'] or ''}")
        vo = _query("SELECT devanagari, transliteration, meaning, source FROM verse_of_week WHERE week_start = ?", (w["week_start"],))
        if not vo.empty:
            st.subheader("Verse of the week")
            r = vo.iloc[0]
            st.write(f"Transliteration: {_strip_diacritics(r['transliteration'])}")
            st.caption(f"Meaning: {_clean_meaning(r['meaning'])}")
            st.caption(f"Source: {r['source'] or ''}")

elif page == "Janam patri":
    st.header("Janam patri")
    jp = _query("SELECT * FROM janam_patri LIMIT 1")
    if jp.empty:
        st.info("Janam patri not in DB. Enable in config and run `python scripts/export_to_sqlite.py`.")
    else:
        r = jp.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Janma Nakshatra", r["janma_nakshatra"])
        c2.metric("Rashi", r["rashi"])
        c3.metric("Birth", f"{r['birth_date']} {r['birth_time']}")
        st.caption(f"Place: {r['birth_place']}")
        verses = _query("SELECT devanagari, transliteration, meaning, source FROM janam_patri_verses ORDER BY sort_order")
        if not verses.empty:
            st.subheader("Recommended verses")
            for idx, v in verses.iterrows():
                st.markdown(f"**{idx + 1}. {v['source'] or 'Verse'}**")
                st.write(f"Transliteration: {_strip_diacritics(v['transliteration'])}")
                st.caption(f"Meaning: {_clean_meaning(v['meaning'])}")

elif page == "History":
    st.header("Recommendation history")
    runs = _query("SELECT week_start AS week, verse_source, observances, observance_count, search_latency_ms, start_time FROM runs ORDER BY start_time DESC")
    if runs.empty:
        st.info("No runs yet.")
    else:
        st.dataframe(runs, use_container_width=True, hide_index=True)

else:
    st.header("Insights")
    runs = _query("SELECT week_start, verse_source, observance_count, observances FROM runs")
    if runs.empty:
        st.info("No runs yet. Generate weekly digests and export to SQLite.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Weeks tracked", len(runs))
        col2.metric("Total observances", int(runs["observance_count"].sum()))
        top = runs["verse_source"].value_counts()
        if not top.empty:
            col3.metric("Most recommended", top.index[0])
        st.subheader("Observance count by week")
        st.bar_chart(runs.set_index("week_start")[["observance_count"]])
