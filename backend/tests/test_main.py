"""Tests for the FastAPI endpoints in main.py. The real Claude API call is
mocked out in every test here - these verify our own logic (routing,
caching, response shape), not the LLM's output."""

from fastapi.testclient import TestClient

import main


def make_client(monkeypatch, tmp_path):
    """Builds a TestClient pointed at an isolated test database, with the
    Claude API calls replaced by deterministic fakes."""
    monkeypatch.setattr(main.database, "DB_PATH", tmp_path / "test_main.db")

    monkeypatch.setattr(
        main,
        "generate_horoscope",
        lambda sign, mood, chaos_level, date: f"Fake horoscope for {sign} feeling {mood}.",
    )
    monkeypatch.setattr(
        main,
        "generate_horoscope_auto_mood",
        lambda sign, chaos_level, date: (f"Fake auto horoscope for {sign}.", "excited"),
    )

    return TestClient(main.app)


def test_health_check():
    client = TestClient(main.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_horoscope_with_mood_generates_then_caches(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    payload = {"sign": "leo", "mood": "happy", "chaos_level": 2}

    with client:
        first = client.post("/horoscope", json=payload)
        assert first.status_code == 200
        body = first.json()
        assert body["from_cache"] is False
        assert body["view_count"] == 1
        assert body["mood"] == "happy"
        assert "leo" in body["horoscope_text"]

        # Same request again should hit the cache, not regenerate.
        second = client.post("/horoscope", json=payload)
        assert second.status_code == 200
        second_body = second.json()
        assert second_body["from_cache"] is True
        assert second_body["view_count"] == 2
        assert second_body["horoscope_text"] == body["horoscope_text"]


def test_horoscope_without_mood_uses_auto_flow(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    payload = {"sign": "aries", "chaos_level": 3}  # no mood key at all

    with client:
        first = client.post("/horoscope", json=payload)
        assert first.status_code == 200
        body = first.json()
        assert body["from_cache"] is False
        assert body["mood"] == "excited"  # from our fake generate_horoscope_auto_mood

        second = client.post("/horoscope", json=payload)
        second_body = second.json()
        assert second_body["from_cache"] is True
        assert second_body["view_count"] == 2


def test_different_moods_are_separate_cache_entries(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    with client:
        happy_payload = {"sign": "libra", "mood": "happy", "chaos_level": 1}
        stressed_payload = {"sign": "libra", "mood": "stressed", "chaos_level": 1}
        happy = client.post("/horoscope", json=happy_payload)
        stressed = client.post("/horoscope", json=stressed_payload)

        assert happy.json()["from_cache"] is False
        assert stressed.json()["from_cache"] is False
        assert happy.json()["view_count"] == 1
        assert stressed.json()["view_count"] == 1


def test_llm_failure_returns_502(monkeypatch, tmp_path):
    monkeypatch.setattr(main.database, "DB_PATH", tmp_path / "test_main_fail.db")

    def boom(*args, **kwargs):
        raise RuntimeError("simulated API failure")

    monkeypatch.setattr(main, "generate_horoscope", boom)

    with TestClient(main.app) as client:
        response = client.post(
            "/horoscope", json={"sign": "scorpio", "mood": "bored", "chaos_level": 1}
        )
        assert response.status_code == 502
        assert "LLM generation failed" in response.json()["detail"]


def test_user_and_auto_requests_can_both_land_on_the_same_mood(monkeypatch, tmp_path):
    """Regression test for the cache-key collision. A user picks 'excited' on
    the classic page; the Win98 page then asks Claude to choose, and the fake
    Claude picks 'excited' too. This used to be a 500 after the LLM call."""
    client = make_client(monkeypatch, tmp_path)

    with client:
        classic = client.post(
            "/horoscope", json={"sign": "aries", "mood": "excited", "chaos_level": 3}
        )
        win98 = client.post("/horoscope", json={"sign": "aries", "chaos_level": 3})

        assert classic.status_code == 200
        assert win98.status_code == 200
        assert win98.json()["mood"] == "excited"
        assert win98.json()["from_cache"] is False
        assert win98.json()["horoscope_text"] != classic.json()["horoscope_text"]

        # And each flow still hits its own cache entry afterwards.
        assert client.post("/horoscope", json={"sign": "aries", "chaos_level": 3}).json()[
            "from_cache"
        ]


def test_losing_a_cache_race_serves_the_winner_instead_of_failing(monkeypatch, tmp_path):
    """Two identical requests can both miss the cache. Simulate the other
    request finishing first, while this one is still inside the LLM call."""
    client = make_client(monkeypatch, tmp_path)
    today = main.date_cls.today().isoformat()

    def generate_while_a_rival_wins(sign, mood, chaos_level, date):
        main.database.insert_horoscope(
            sign=sign,
            date=today,
            chaos_level=chaos_level,
            requested_mood=mood,
            mood=mood,
            mood_color=main.MOOD_COLORS[mood],
            horoscope_text="the rival's horoscope",
        )
        return "my horoscope"

    monkeypatch.setattr(main, "generate_horoscope", generate_while_a_rival_wins)

    with client:
        response = client.post("/horoscope", json={"sign": "leo", "mood": "calm", "chaos_level": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["horoscope_text"] == "the rival's horoscope"
    assert body["from_cache"] is True
    assert body["view_count"] == 2
