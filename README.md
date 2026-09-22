# Horoscope App

LLM-generated daily horoscopes with a mood-ring twist. Local dev project created in conjunction with Claude. Mostly meant to practice LLM intervention and the Anthropic SDK.

## Backend (FastAPI)

```bash
cd backend
python -m venv venv
venv\Scripts\Activate.ps1 # We're working with Windows but adjust as needed
pip install -r requirements.txt
cp .env.example .env          # then throw in your real ANTHROPIC_API_KEY
uvicorn main:app --reload
```

API docs available at http://localhost:8000/docs once running (FastAPI auto-generates this — like Swagger).

## Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

App runs at http://localhost:5173.

## How caching works

Each request is keyed on `(sign, date, mood, chaos_level)`. First request
for a given combo on a given day calls Claude and stores the result;
every subsequent identical request that day is served from SQLite and
bumps `view_count`. In the main instance, Claude generates mood itself from 
a predetermined list, in the other instance mood is selected by the user
but either way it is cached to be seen from both. 

## Next steps / ideas

- Add a `/stats` endpoint to surface view counts per sign
- Swap SQLite connection string for Postgres when deploying (SQLAlchemy
  makes this closer to a config change than a rewrite)
- Add a "share my horoscope" image export
- Rate-limit the generation path before this ever goes public lol
