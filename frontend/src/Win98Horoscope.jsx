import { useEffect, useState } from "react";
import { fetchHoroscope } from "./api";

const SIGNS = [
  "aries", "taurus", "gemini", "cancer", "leo", "virgo",
  "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
];

const CHAOS_LABELS = {
  1: "1 - Gentle",
  2: "2 - Playful",
  3: "3 - Unhinged",
};

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export default function Win98Horoscope() {
  const [sign, setSign] = useState(SIGNS[0]);
  const [chaosLevel, setChaosLevel] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 98.css loads only when mounted
  useEffect(() => {
    const link = document.createElement("link");
    link.id = "win98-css";
    link.rel = "stylesheet";
    link.href = "https://unpkg.com/98.css";
    document.head.appendChild(link);

    return () => {
      document.getElementById("win98-css")?.remove();
    };
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      // LLM version so omit mood
      const data = await fetchHoroscope({ sign, chaos_level: chaosLevel });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#008080",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
        fontFamily: '"Pixelated MS Sans Serif", Arial, sans-serif',
      }}
    >
      <div className="window" style={{ width: 520 }}>
        <div className="title-bar">
          <div className="title-bar-text">Generate a Horoscope</div>
          <div className="title-bar-controls">
            <button aria-label="Minimize"></button>
            <button aria-label="Maximize"></button>
            <button aria-label="Close"></button>
          </div>
        </div>

        <div className="window-body">
          <form onSubmit={handleSubmit}>
            <div className="field-row" style={{ marginBottom: 8 }}>
              <label htmlFor="sign-select" style={{ width: 90 }}>
                Zodiac Sign
              </label>
              <select
                id="sign-select"
                value={sign}
                onChange={(e) => setSign(e.target.value)}
              >
                {SIGNS.map((s) => (
                  <option key={s} value={s}>
                    {capitalize(s)}
                  </option>
                ))}
              </select>
            </div>

            <div className="field-row" style={{ marginBottom: 12 }}>
              <label htmlFor="chaos-select" style={{ width: 90 }}>
                Chaos Level
              </label>
              <select
                id="chaos-select"
                value={chaosLevel}
                onChange={(e) => setChaosLevel(Number(e.target.value))}
              >
                {[1, 2, 3].map((c) => (
                  <option key={c} value={c}>
                    {CHAOS_LABELS[c]}
                  </option>
                ))}
              </select>
            </div>

            <section className="field-row" style={{ justifyContent: "flex-end" }}>
              <button type="submit" disabled={loading}>
                {loading ? "Generating..." : "Generate"}
              </button>
            </section>
          </form>

          {error && (
            <div className="field-row" style={{ marginTop: 12, color: "#aa0000" }}>
              Error: {error}
            </div>
          )}

          {result && (
            <fieldset style={{ marginTop: 16 }}>
              <legend>Your Horoscope</legend>
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <p style={{ flex: 1, margin: 0, lineHeight: 1.4 }}>
                  {result.horoscope_text}
                </p>
                <Heart color={result.mood_color} />
              </div>
              <p
                style={{
                  marginTop: 12,
                  marginBottom: 0,
                  textAlign: "center",
                  textTransform: "capitalize",
                }}
              >
                Mood: {result.mood}
              </p>
            </fieldset>
          )}
        </div>

        <div className="status-bar">
          <p className="status-bar-field">{sign && capitalize(sign)}</p>
          <p className="status-bar-field">
            {result ? `Viewed ${result.view_count}x` : "Ready"}
          </p>
          <p className="status-bar-field">
            <a href="/classic">Classic version</a>
          </p>
        </div>
      </div>
    </div>
  );
}

function Heart({ color }) {
  return (
    <svg
      width="72"
      height="64"
      viewBox="0 0 32 29"
      xmlns="http://www.w3.org/2000/svg"
      style={{ flexShrink: 0 }}
      aria-label="Mood heart"
    >
      <path
        d="M16 29
           C 16 29, 0 18, 0 8.5
           C 0 3, 4 0, 8 0
           C 11.5 0, 14.5 2, 16 5.5
           C 17.5 2, 20.5 0, 24 0
           C 28 0, 32 3, 32 8.5
           C 32 18, 16 29, 16 29 Z"
        fill={color || "#D62828"}
        stroke="#000"
        strokeWidth="1"
      />
    </svg>
  );
}