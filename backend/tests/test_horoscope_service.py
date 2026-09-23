"""Tests for horoscope_service.py - prompt construction and response
parsing. Deliberately does NOT call the real Claude API - these test the
pure logic around it (see test_main.py for the endpoint-level tests, which
mock the actual API call)."""

import pytest

from horoscope_service import build_auto_mood_prompt, build_prompt, parse_mood_response


def test_build_prompt_includes_key_details():
    prompt = build_prompt("leo", "happy", 2, "2026-09-22")
    assert "Leo" in prompt
    assert "happy" in prompt
    assert "2026-09-22" in prompt


def test_build_auto_mood_prompt_lists_all_mood_options():
    prompt = build_auto_mood_prompt("aries", 1, "2026-09-22")
    # Every preset mood should be offered as a choice for the LLM.
    for mood in [
        "stressed",
        "anxious",
        "calm",
        "neutral",
        "excited",
        "passionate",
        "happy",
        "romantic",
        "bored",
    ]:
        assert mood in prompt
    assert "JSON" in prompt


def test_parse_mood_response_valid_json():
    raw = '{"mood": "excited", "horoscope": "Big things are coming your way."}'
    text, mood = parse_mood_response(raw)
    assert mood == "excited"
    assert text == "Big things are coming your way."


def test_parse_mood_response_strips_code_fence():
    raw = '```json\n{"mood": "calm", "horoscope": "Breathe easy today."}\n```'
    text, mood = parse_mood_response(raw)
    assert mood == "calm"
    assert text == "Breathe easy today."


def test_parse_mood_response_unknown_mood_falls_back_to_neutral():
    raw = '{"mood": "supercalifragilistic", "horoscope": "Odd vibes today."}'
    text, mood = parse_mood_response(raw)
    assert mood == "neutral"
    assert text == "Odd vibes today."


def test_parse_mood_response_invalid_json_raises():
    with pytest.raises(ValueError):
        parse_mood_response("this is not json at all")


def test_parse_mood_response_missing_keys_raises():
    with pytest.raises(ValueError):
        parse_mood_response('{"mood": "happy"}')  # missing "horoscope"
