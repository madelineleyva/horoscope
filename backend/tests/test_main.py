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
