"""
All LLM-facing logic lives here, isolated from the API routes and the
database. Keeping this separate means you can swap providers later
(or add a fallback provider) without touching main.py.
"""

import os

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from models import CHAOS_DESCRIPTIONS, MOOD_COLORS, MoodReading

# Loaded here rather than in main.py: this module builds the Anthropic
# client as soon as it's imported, so the API key needs to already be in
# the environment by that point. Keeping the load_dotenv() call next to
# the thing that actually needs it also means main.py's imports can stay
# a clean, uninterrupted block at the top of the file (ruff's E402 rule).
load_dotenv()

# Explicit timeout + retries: the SDK defaults are generous (10 minutes), which
# would leave a user staring at a spinner if the API stalls.
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"), timeout=30.0, max_retries=2)

MODEL = "claude-sonnet-4-6"
MOOD_OPTIONS = list(MOOD_COLORS.keys())

# Forcing this tool call makes the API return arguments that conform to the
# schema, instead of us asking for JSON in prose and parsing whatever comes back.
MOOD_TOOL_NAME = "record_horoscope"
MOOD_TOOL = {
    "name": MOOD_TOOL_NAME,
    "description": "Record the horoscope you wrote and the single mood that best fits it.",
    "input_schema": MoodReading.model_json_schema(),
}


class HoroscopeGenerationError(Exception):
    """The model responded, but not with a usable horoscope."""


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

Submit your answer by calling the {MOOD_TOOL_NAME} tool.
"""


def extract_mood_reading(response) -> MoodReading:
    """Pulls the validated MoodReading out of an API response. Split out
    from the API call so it can be unit tested with fake responses."""
    if response.stop_reason == "max_tokens":
        raise HoroscopeGenerationError("Response was cut off before the horoscope was finished.")

    tool_call = next(
        (b for b in response.content if b.type == "tool_use" and b.name == MOOD_TOOL_NAME),
        None,
    )
    if tool_call is None:
        raise HoroscopeGenerationError(f"Model did not call {MOOD_TOOL_NAME}.")

    try:
        reading = MoodReading.model_validate(tool_call.input)
    except ValidationError as exc:
        raise HoroscopeGenerationError(f"Model output failed validation: {exc}") from exc

    return reading.model_copy(update={"horoscope": reading.horoscope.strip()})


def generate_horoscope_auto_mood(sign: str, chaos_level: int, date: str) -> tuple[str, str]:
    """Calls Claude, letting it choose the mood itself.
    Returns (horoscope_text, mood)."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        tools=[MOOD_TOOL],
        tool_choice={"type": "tool", "name": MOOD_TOOL_NAME},
        messages=[{"role": "user", "content": build_auto_mood_prompt(sign, chaos_level, date)}],
    )

    reading = extract_mood_reading(response)
    return reading.horoscope, reading.mood
