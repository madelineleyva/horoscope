"""
FastAPI entry point. Roughly the equivalent of Program.cs +
a controller, combined into one file for now since the app is small.
Split routes into their own module once this grows.
"""

from datetime import date as date_cls

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import database
from horoscope_service import generate_horoscope, generate_horoscope_auto_mood
from models import MOOD_COLORS, HoroscopeRequest, HoroscopeResponse

app = FastAPI(title="Horoscope API")

# Allow the local React dev server to call this API.
# Tighten this list before deploying anywhere public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    database.init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/horoscope", response_model=HoroscopeResponse)
def get_horoscope(req: HoroscopeRequest):
    today = date_cls.today().isoformat()

    if req.mood is not None:
        # Original flow: mood is a user input, part of the cache key.
        cached = database.get_cached(req.sign, today, req.mood, req.chaos_level)
        if cached:
            new_count = database.increment_view_count(cached["id"])
            cached["view_count"] = new_count
            return HoroscopeResponse(**cached, from_cache=True)

        try:
            text = generate_horoscope(req.sign, req.mood, req.chaos_level, today)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"LLM generation failed: {exc}") from exc

        row = database.insert_horoscope(
            sign=req.sign,
            date=today,
            mood=req.mood,
            mood_color=MOOD_COLORS[req.mood],
            chaos_level=req.chaos_level,
            horoscope_text=text,
            mood_source="user",
        )
        return HoroscopeResponse(**row, from_cache=False)

    # Auto-mood flow: mood is chosen by the LLM, so it isn't known until
    # after generation and isn't part of the cache lookup key.
    cached = database.get_cached_auto(req.sign, today, req.chaos_level)
    if cached:
        new_count = database.increment_view_count(cached["id"])
        cached["view_count"] = new_count
        return HoroscopeResponse(**cached, from_cache=True)

    try:
        text, chosen_mood = generate_horoscope_auto_mood(req.sign, req.chaos_level, today)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {exc}") from exc

    row = database.insert_horoscope(
        sign=req.sign,
        date=today,
        mood=chosen_mood,
        mood_color=MOOD_COLORS[chosen_mood],
        chaos_level=req.chaos_level,
        horoscope_text=text,
        mood_source="llm",
    )
    return HoroscopeResponse(**row, from_cache=False)
