const BASE = '/api/v1'

export async function triggerCrawl(paperId, { maxDepth = 1, maxPapers = 15 } = {}) {
  const res = await fetch(`${BASE}/crawl`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paper_id: paperId, max_depth: maxDepth, max_papers: maxPapers }),
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body.error || `Crawl failed: HTTP ${res.status}`)
  return body
}

export async function fetchGraph() {
  const res = await fetch(`${BASE}/graph`)
  if (!res.ok) throw new Error(`Failed to load graph: HTTP ${res.status}`)
  return res.json()
}
