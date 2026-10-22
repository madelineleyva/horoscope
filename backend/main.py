"""
FastAPI entry point. Roughly the equivalent of Program.cs +
a controller, combined into one file for now since the app is small.
Split routes into their own module once this grows.
"""

from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import date as date_cls

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import database
from horoscope_service import generate_horoscope, generate_horoscope_auto_mood
from models import MOOD_COLORS, HoroscopeRequest, HoroscopeResponse


@asynccontextmanager
async def lifespan(_app: FastAPI):
    database.init_db()
    yield


app = FastAPI(title="Horoscope API", lifespan=lifespan)

# Allow the local React dev server to call this API.
# Tighten this list before deploying anywhere public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


def _serve_cached(row: dict) -> HoroscopeResponse:
    row["view_count"] = database.increment_view_count(row["id"])
    return HoroscopeResponse(**row, from_cache=True)


def _get_or_create(
    req: HoroscopeRequest,
    today: str,
    generate: Callable[[], tuple[str, str]],
) -> HoroscopeResponse:
    """Shared cache-aside flow for both mood modes. `generate` returns
    (horoscope_text, mood) and is only called on a cache miss."""
    cached = database.get_cached(req.sign, today, req.chaos_level, req.mood)
    if cached:
        return _serve_cached(cached)
    try:
        text, mood = generate()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {exc}") from exc
    row, created = database.insert_horoscope(
        sign=req.sign,
        date=today,
        chaos_level=req.chaos_level,
        requested_mood=req.mood,
        mood=mood,
        mood_color=MOOD_COLORS[mood],
        horoscope_text=text,
    )
    if not created:
        # A concurrent request cached this same key while we were waiting on
        # the LLM. Serve theirs rather than failing or overwriting it.
        return _serve_cached(row)
    return HoroscopeResponse(**row, from_cache=False)


@app.post("/horoscope", response_model=HoroscopeResponse)
def get_horoscope(req: HoroscopeRequest):
    today = date_cls.today().isoformat()

    if req.mood is not None:
        # Mood is a user input and part of the cache key.
        def generate():
            return generate_horoscope(req.sign, req.mood, req.chaos_level, today), req.mood
    else:
        # Claude picks the mood, so it isn't known until after generation.
        def generate():
            return generate_horoscope_auto_mood(req.sign, req.chaos_level, today)

    return _get_or_create(req, today, generate)
