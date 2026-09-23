from typing import Literal

from pydantic import BaseModel

ZodiacSign = Literal[
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
]

Mood = Literal[
    "stressed",
    "anxious",
    "calm",
    "neutral",
    "excited",
    "passionate",
    "happy",
    "romantic",
    "bored",
]

ChaosLevel = Literal[1, 2, 3]

# Mood -> color mapping for the "mood ring" UI treatment.
MOOD_COLORS: dict[str, str] = {
    "stressed": "#D62828",
    "anxious": "#F77F00",
    "calm": "#457B9D",
    "neutral": "#ADB5BD",
    "excited": "#FFD60A",
    "passionate": "#7209B7",
    "happy": "#52B788",
    "romantic": "#F72585",
    "bored": "#6C757D",
}

CHAOS_DESCRIPTIONS: dict[int, str] = {
    1: "gentle, grounded, and reassuring",
    2: "playful, a little unpredictable, with a mild plot twist",
    3: "unhinged, dramatic, and delightfully chaotic",
}


class HoroscopeRequest(BaseModel):
    sign: ZodiacSign
    # Optional: when omitted, the LLM chooses the mood itself based on the
    # horoscope it generates (used by the Win98 /main page, which has no
    # mood dropdown). When provided, behaves exactly as before.
    mood: Mood | None = None
    chaos_level: ChaosLevel


class HoroscopeResponse(BaseModel):
    id: int
    sign: str
    date: str
    mood: str
    mood_color: str
    chaos_level: int
    horoscope_text: str
    view_count: int
    from_cache: bool
