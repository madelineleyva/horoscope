import { useEffect, useState } from 'react'
import { fetchHoroscope } from './api'
import Taskbar from "./Taskbar";
import Win98Window from "./Win98Window";

const SIGNS = [
  'aries',
  'taurus',
  'gemini',
  'cancer',
  'leo',
  'virgo',
  'libra',
  'scorpio',
  'sagittarius',
  'capricorn',
  'aquarius',
  'pisces',
]

const CHAOS_LABELS = {
  1: '1 - Gentle',
  2: '2 - Playful',
  3: '3 - Unhinged',
}

const START_MENU_ITEMS = [
  { label: "Classic Version", icon: "🖥️", href: "/classic" },
  { label: "API Docs", icon: "📄", href: "http://localhost:8000/docs", external: true },
];


function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

export default function Win98Horoscope() {
  const [sign, setSign] = useState(SIGNS[0])
  const [chaosLevel, setChaosLevel] = useState(1)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [windowState, setWindowState] = useState("open")

  // 98.css loads only when mounted
  useEffect(() => {
    const link = document.createElement('link')
    link.id = 'win98-css'
    link.rel = 'stylesheet'
    link.href = 'https://unpkg.com/98.css'
    document.head.appendChild(link)

    return () => {
      document.getElementById('win98-css')?.remove()
    }
  }, [])

   useEffect(() => {
    document.getElementById("favicon")?.setAttribute("href", "/favicon-win98.svg");
  }, []);

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      // LLM version so omit mood
      const data = await fetchHoroscope({ sign, chaos_level: chaosLevel })
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
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
        paddingBottom: "calc(2rem + 34px)", // leave room for the fixed taskbar
        fontFamily: '"Pixelated MS Sans Serif", Arial, sans-serif',
      }}
    >
      {windowState === "closed" && (
        <div
          role="button"
          tabIndex={0}
          onClick={() => setWindowState("open")}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setWindowState("open")}
          style={{
            position: "fixed",
            top: 24,
            left: 24,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 4,
            width: 72,
            cursor: "pointer",
            userSelect: "none",
          }}
        >
          <span style={{ fontSize: 40, lineHeight: 1 }}>🔮</span>
          <span
            style={{
              color: "white",
              fontSize: 12,
              textAlign: "center",
              textShadow: "1px 1px 1px black",
            }}
          >
            Horoscope 98
          </span>
        </div>
      )}
 
      <Win98Window
        title="Generate a Horoscope"
        hidden={windowState !== "open"}
        onMinimize={() => setWindowState("minimized")}
        onClose={() => setWindowState("closed")}
      >
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
      </Win98Window>
 
      <Taskbar
        menuItems={START_MENU_ITEMS}
        runningApp={
          windowState === "minimized"
            ? { label: "Horoscope 98", icon: "🔮", onRestore: () => setWindowState("open") }
            : null
        }
      />
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
        fill={color || '#D62828'}
        stroke="#000"
        strokeWidth="1"
      />
    </svg>
  )
}
