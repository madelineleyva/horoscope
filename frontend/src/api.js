const API_BASE = "http://localhost:8000";

export async function fetchHoroscope({ sign, mood, chaos_level }) {
  const res = await fetch(`${API_BASE}/horoscope`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sign, mood, chaos_level }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed with ${res.status}`);
  }

  return res.json();
}
