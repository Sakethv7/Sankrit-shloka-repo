"""Telugu Panchangam engine — real astronomical calculations.

Uses pyswisseph (Swiss Ephemeris) to compute the five limbs of the
panchangam: Tithi, Nakshatra, Yoga, Karana, and Vaara.

Configured for New Jersey, USA (default) with Amanta month system per
Golconda Vyapari Niyogi Brahmin tradition.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import swisseph as swe

# ── Constants ────────────────────────────────────────────────────────

# New Jersey defaults (from config.yaml)
DEFAULT_LAT = 40.7128
DEFAULT_LON = -74.2060
DEFAULT_TZ = -5.0  # EST

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",
]

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

YOGA_NAMES = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shula", "Ganda",
    "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma",
    "Indra", "Vaidhriti",
]

KARANA_NAMES = [
    "Bava", "Balava", "Kaulava", "Taitila", "Garaja",
    "Vanija", "Vishti", "Shakuni", "Chatushpada", "Nagava", "Kimstughna",
]

VAARA_NAMES = ["Ravivara", "Somavara", "Mangalavara", "Budhavara", "Guruvara", "Shukravara", "Shanivara"]

PAKSHA_NAMES = ["Shukla", "Krishna"]

MASA_NAMES = [
    "Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana",
    "Bhadrapada", "Ashwina", "Kartika", "Margashira", "Pushya",
    "Magha", "Phalguna",
]


# ── Core Calculations ────────────────────────────────────────────────

def _jd(date: dt.date) -> float:
    """Convert a Gregorian date to Julian Day Number."""
    return swe.julday(date.year, date.month, date.day, 0.0)


def _sun_lon(jd: float) -> float:
    """Tropical longitude of the Sun in degrees."""
    return swe.calc_ut(jd, swe.SUN)[0][0]


def _moon_lon(jd: float) -> float:
    """Tropical longitude of the Moon in degrees."""
    return swe.calc_ut(jd, swe.MOON)[0][0]


def _sunrise_jd(jd: float, lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> float:
    """Julian day of sunrise for the given date and location."""
    result = swe.rise_trans(jd, swe.SUN, 1, (lon, lat, 0.0))
    return result[1][0]


def _tithi_at(jd: float) -> int:
    """Tithi number (0-29) at the given Julian day."""
    sun, moon = _sun_lon(jd), _moon_lon(jd)
    diff = (moon - sun) % 360
    return int(diff / 12)


def _nakshatra_at(jd: float) -> int:
    """Nakshatra number (0-26) at the given Julian day."""
    moon = _moon_lon(jd)
    # Ayanamsha correction (Lahiri)
    ayan = swe.get_ayanamsa_ut(jd)
    sidereal = (moon - ayan) % 360
    return int(sidereal / (360 / 27))


def _yoga_at(jd: float) -> int:
    """Yoga number (0-26) at the given Julian day."""
    sun, moon = _sun_lon(jd), _moon_lon(jd)
    ayan = swe.get_ayanamsa_ut(jd)
    sid_sun = (sun - ayan) % 360
    sid_moon = (moon - ayan) % 360
    total = (sid_sun + sid_moon) % 360
    return int(total / (360 / 27))


def _karana_at(jd: float) -> int:
    """Karana number (0-10) at the given Julian day."""
    sun, moon = _sun_lon(jd), _moon_lon(jd)
    diff = (moon - sun) % 360
    karana_num = int(diff / 6) % 60
    # Map 60 karanas to the 11 named ones
    if karana_num == 0:
        return 10  # Kimstughna
    if karana_num == 57:
        return 7   # Shakuni
    if karana_num == 58:
        return 8   # Chatushpada
    if karana_num == 59:
        return 9   # Nagava
    return (karana_num - 1) % 7


# ── Public API ───────────────────────────────────────────────────────

@dataclass
class DailyPanchang:
    date: dt.date
    vaara: str
    tithi: str
    tithi_num: int
    paksha: str
    nakshatra: str
    yoga: str
    karana: str
    sunrise: str  # HH:MM format in local time


def compute(date: dt.date, lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON, tz: float = DEFAULT_TZ) -> DailyPanchang:
    """Compute panchangam for a given date and location."""
    jd = _jd(date)
    sunrise_jd = _sunrise_jd(jd, lat, lon)

    tithi_num = _tithi_at(sunrise_jd)
    paksha = PAKSHA_NAMES[0] if tithi_num < 15 else PAKSHA_NAMES[1]
    nak_num = _nakshatra_at(sunrise_jd)
    yoga_num = _yoga_at(sunrise_jd)
    karana_num = _karana_at(sunrise_jd)
    vaara_num = int((jd + 1.5) % 7)

    # Sunrise time in local HH:MM — convert JD(UT) to local hours
    sunrise_ut_hours = (sunrise_jd % 1 - 0.5) * 24  # UT hours (0-24)
    sunrise_local = (sunrise_ut_hours + tz) % 24
    sunrise_h, sunrise_m = int(sunrise_local), int((sunrise_local % 1) * 60)

    return DailyPanchang(
        date=date,
        vaara=VAARA_NAMES[vaara_num],
        tithi=TITHI_NAMES[tithi_num],
        tithi_num=tithi_num,
        paksha=paksha,
        nakshatra=NAKSHATRA_NAMES[nak_num],
        yoga=YOGA_NAMES[yoga_num],
        karana=KARANA_NAMES[karana_num],
        sunrise=f"{sunrise_h:02d}:{sunrise_m:02d}",
    )


def is_ekadashi(p: DailyPanchang) -> bool:
    return p.tithi == "Ekadashi"


def is_pradosham(p: DailyPanchang) -> bool:
    return p.tithi == "Trayodashi"


def is_amavasya(p: DailyPanchang) -> bool:
    return p.tithi == "Amavasya"


def is_purnima(p: DailyPanchang) -> bool:
    return p.tithi == "Purnima"


def is_chaturthi(p: DailyPanchang) -> bool:
    return p.tithi == "Chaturthi" and p.paksha == "Krishna"  # Sankashti


if __name__ == "__main__":
    today = dt.date.today()
    for offset in range(7):
        day = today + dt.timedelta(days=offset)
        p = compute(day)
        print(f"{p.date} ({p.vaara}) | {p.paksha} {p.tithi} | {p.nakshatra} | {p.yoga} | Sunrise {p.sunrise}")
