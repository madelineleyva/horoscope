import { useState } from 'react'
import { fetchHoroscope } from './api'
import './App.css'

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

const MOODS = [
  'stressed',
  'anxious',
  'calm',
  'neutral',
  'excited',
  'passionate',
  'happy',
  'romantic',
  'bored',
]

const CHAOS_LABELS = {
  1: 'Gentle',
  2: 'Playful',
  3: 'Unhinged',
}

export default function App() {
  const [sign, setSign] = useState(SIGNS[0])
  const [mood, setMood] = useState(MOODS[0])
  const [chaosLevel, setChaosLevel] = useState(2)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const data = await fetchHoroscope({ sign, mood, chaos_level: chaosLevel })
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <h1>✨ Daily Horoscope</h1>
      <p style={{ fontSize: '0.8rem' }}>
        <a href="/main">← Back to Win98 version</a>
      </p>

      <form onSubmit={handleSubmit} className="form">
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
          {loading ? 'Consulting the stars…' : 'Get My Horoscope'}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="result" style={{ borderColor: result.mood_color }}>
          <div
            className="mood-ring"
            style={{ backgroundColor: result.mood_color }}
            title={`Mood: ${result.mood}`}
          />
          <p className="horoscope-text">{result.horoscope_text}</p>
          <p className="meta">
            {result.sign} · {result.date} · viewed {result.view_count}x
            {result.from_cache ? ' · from cache' : ' · freshly generated'}
          </p>
        </div>
      )}
    </div>
  )
}
