"""Tests for horoscope_service.py - prompt construction and structured-output
handling. Deliberately does NOT call the real Claude API: these test the pure
logic around it (see test_main.py for the endpoint-level tests, which mock
the API call itself)."""

from types import SimpleNamespace
from typing import get_args

import pytest

import horoscope_service
from horoscope_service import (
    MOOD_TOOL,
    MOOD_TOOL_NAME,
    HoroscopeGenerationError,
    build_auto_mood_prompt,
    build_prompt,
    extract_mood_reading,
)
from models import MOOD_COLORS, Mood


def fake_response(*blocks, stop_reason="tool_use"):
    return SimpleNamespace(content=list(blocks), stop_reason=stop_reason)


def tool_call(input_, name=MOOD_TOOL_NAME):
    return SimpleNamespace(type="tool_use", name=name, input=input_)


def test_build_prompt_includes_key_details():
    prompt = build_prompt("leo", "happy", 2, "2026-09-22")
    assert "Leo" in prompt
    assert "happy" in prompt
    assert "2026-09-22" in prompt


def test_build_auto_mood_prompt_lists_all_mood_options_and_names_the_tool():
    prompt = build_auto_mood_prompt("aries", 1, "2026-09-22")
    for mood in get_args(Mood):
        assert mood in prompt
    assert MOOD_TOOL_NAME in prompt


def test_every_mood_has_a_color():
    """Mood (the type) and MOOD_COLORS (the lookup) are defined separately.
    If they drift, a valid mood would KeyError after a paid LLM call."""
    assert set(get_args(Mood)) == set(MOOD_COLORS)


def test_tool_schema_restricts_mood_to_the_fixed_list():
    props = MOOD_TOOL["input_schema"]["properties"]
    assert set(props["mood"]["enum"]) == set(MOOD_COLORS)
    assert set(MOOD_TOOL["input_schema"]["required"]) == {"mood", "horoscope"}


def test_extract_valid_reading():
    response = fake_response(tool_call({"mood": "excited", "horoscope": "  Big things.  "}))
    reading = extract_mood_reading(response)
    assert reading.mood == "excited"
    assert reading.horoscope == "Big things."


def test_extract_ignores_non_tool_blocks():
    chatter = SimpleNamespace(type="text", text="Sure! Here you go.")
    response = fake_response(chatter, tool_call({"mood": "calm", "horoscope": "Breathe."}))
    assert extract_mood_reading(response).mood == "calm"


def test_unknown_mood_is_rejected_not_silently_replaced():
    response = fake_response(tool_call({"mood": "supercalifragilistic", "horoscope": "Odd."}))
    with pytest.raises(HoroscopeGenerationError):
        extract_mood_reading(response)


def test_missing_field_is_rejected():
    with pytest.raises(HoroscopeGenerationError):
        extract_mood_reading(fake_response(tool_call({"mood": "happy"})))


def test_empty_horoscope_is_rejected():
    with pytest.raises(HoroscopeGenerationError):
        extract_mood_reading(fake_response(tool_call({"mood": "happy", "horoscope": ""})))


def test_no_tool_call_is_rejected():
    with pytest.raises(HoroscopeGenerationError):
        extract_mood_reading(fake_response(SimpleNamespace(type="text", text="hi")))


def test_truncated_response_is_rejected():
    response = fake_response(
        tool_call({"mood": "happy", "horoscope": "Cut off mid-sen"}), stop_reason="max_tokens"
    )
    with pytest.raises(HoroscopeGenerationError):
        extract_mood_reading(response)


def test_generate_auto_mood_forces_the_tool_call(monkeypatch):
    """Checks the request we send, which is where structured output is won or lost."""
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return fake_response(tool_call({"mood": "romantic", "horoscope": "Love is in the air."}))

    monkeypatch.setattr(horoscope_service.client.messages, "create", fake_create)

    text, mood = horoscope_service.generate_horoscope_auto_mood("libra", 2, "2026-09-22")

    assert (text, mood) == ("Love is in the air.", "romantic")
    assert captured["tools"] == [MOOD_TOOL]
    assert captured["tool_choice"] == {"type": "tool", "name": MOOD_TOOL_NAME}
