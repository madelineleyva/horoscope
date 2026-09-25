import { useEffect, useState } from "react";
import { fetchHoroscope } from "./api";
import { playThunderClap } from "./Sounds";
import "./App.css";

const SIGNS = [
  "aries", "taurus", "gemini", "cancer", "leo", "virgo",
  "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
];

const MOODS = [
  "stressed", "anxious", "calm", "neutral", "excited",
  "passionate", "happy", "romantic", "bored",
];

const CHAOS_LABELS = {
  1: "Gentle",
  2: "Playful",
  3: "Unhinged",
};

function formatDate(isoDate) {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function timesLabel(n) {
  return n === 1 ? "once" : `${n} times`;
}

export default function App() {
  const [sign, setSign] = useState(SIGNS[0]);
  const [mood, setMood] = useState(MOODS[0]);
  const [chaosLevel, setChaosLevel] = useState(2);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    document.getElementById("favicon")?.setAttribute("href", "/favicon-mansion.svg");
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    playThunderClap();
    try {
      const data = await fetchHoroscope({ sign, mood, chaos_level: chaosLevel });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <div className="masthead">
        <h1>The Parlour Oracle</h1>
        <p>Whisper your sign to the orb.</p>
        <a className="back-link" href="/main">
          ← Back to the Win98 wing
        </a>
      </div>

      <div className="orb-wrapper">
        <div className="orb">
          <form onSubmit={handleSubmit} className="orb-form">
            <label>
              Zodiac Sign
              <select value={sign} onChange={(e) => setSign(e.target.value)}>
                {SIGNS.map((s) => (
                  <option key={s} value={s}>
                    {s.charAt(0).toUpperCase() + s.slice(1)}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Current Mood
              <select value={mood} onChange={(e) => setMood(e.target.value)}>
                {MOODS.map((m) => (
                  <option key={m} value={m}>
                    {m.charAt(0).toUpperCase() + m.slice(1)}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Chaos Level: {CHAOS_LABELS[chaosLevel]}
              <input
                type="range"
                min="1"
                max="3"
                value={chaosLevel}
                onChange={(e) => setChaosLevel(Number(e.target.value))}
              />
            </label>

            <button type="submit" disabled={loading}>
              {loading ? "Consulting…" : "Consult the Orb"}
            </button>
          </form>
        </div>
        <div className="plinth" />
      </div>

      {error && <p className="error">The spirits could not be reached: {error}</p>}

      {result && (
        <div className="result">
          <div className="wax-seal" style={{ backgroundColor: result.mood_color }} />
          <p className="horoscope-text">{result.horoscope_text}</p>
          <p className="meta">
            For {result.sign}, {formatDate(result.date)}. Consulted{" "}
            {timesLabel(result.view_count)} —{" "}
            {result.from_cache ? "recalled from memory" : "freshly divined"}.
          </p>
        </div>
      )}
    </div>
  );
}