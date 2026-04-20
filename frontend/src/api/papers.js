const BASE = '/api/v1'

export async function searchPapers(query, limit = 8) {
  const url = `${BASE}/papers/search?q=${encodeURIComponent(query)}&limit=${limit}`
  const res = await fetch(url)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || `HTTP ${res.status}`)
  }
  return res.json()
}
