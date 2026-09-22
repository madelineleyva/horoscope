"""
All LLM-facing logic lives here, isolated from the API routes and the
database. Keeping this separate means you can swap providers later
(or add a fallback provider) without touching main.py.
"""
import json
import os
from anthropic import Anthropic
from models import CHAOS_DESCRIPTIONS, MOOD_COLORS

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-6"
MOOD_OPTIONS = list(MOOD_COLORS.keys())

def build_prompt(sign: str, mood: str, chaos_level: int, date: str) -> str:
    chaos_desc = CHAOS_DESCRIPTIONS[chaos_level]
    return f"""Write a daily horoscope for {sign.capitalize()} for {date}.

The reader has told you their current mood is: {mood}.
The tone of the horoscope should be {chaos_desc}.

Requirements:
- 3-5 sentences.
- Speak directly to the reader ("you").
- Weave in their {mood} mood naturally, don't just repeat the word.
- Keep it fun and a little playful regardless of chaos level.
- Do not include a greeting, sign-off, or any text besides the horoscope itself.
"""


def generate_horoscope(sign: str, mood: str, chaos_level: int, date: str) -> str:
    """Calls Claude and returns just the horoscope text."""
    prompt = build_prompt(sign, mood, chaos_level, date)

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    # response.content is a list of blocks; we just want the text ones.
    text_parts = [block.text for block in response.content if block.type == "text"]
    return "".join(text_parts).strip()

def build_auto_mood_prompt(sign: str, chaos_level: int, date: str) -> str:
    chaos_desc = CHAOS_DESCRIPTIONS[chaos_level]
    mood_list = ", ".join(MOOD_OPTIONS)
    return f"""Write a daily horoscope for {sign.capitalize()} for {date}.
 
The tone of the horoscope should be {chaos_desc}.
 
You also get to decide the overall mood/vibe of this horoscope. Choose
exactly one mood from this fixed list, whichever best fits the horoscope
you write: {mood_list}.
 
Requirements for the horoscope text:
- 3-5 sentences.
- Speak directly to the reader ("you").
- Keep it fun and a little playful regardless of chaos level.
 
Respond with ONLY a raw JSON object (no markdown fences, no extra text)
in exactly this shape:
{{"mood": "<one of the listed moods>", "horoscope": "<the horoscope text>"}}
"""
 
def generate_horoscope_auto_mood(sign: str, chaos_level: int, date: str) -> tuple[str, str]:
    """Calls Claude, letting it choose the mood itself.
    Returns (horoscope_text, mood)."""
    prompt = build_auto_mood_prompt(sign, chaos_level, date)
 
    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
 
    text_parts = [block.text for block in response.content if block.type == "text"]
    raw = "".join(text_parts).strip()
 
    # Defensive cleanup in case the model wraps the JSON in a code fence
    # despite being asked not to.
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
 
    try:
        parsed = json.loads(raw)
        mood = parsed["mood"]
        horoscope_text = parsed["horoscope"].strip()
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"Could not parse mood/horoscope from model output: {raw!r}") from exc
 
    if mood not in MOOD_OPTIONS:
        # Model picked something outside the fixed list; fall back safely
        # rather than storing a mood we have no color mapping for.
        mood = "neutral"
 
    return horoscope_text, mood
