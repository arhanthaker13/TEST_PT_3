import { useState } from 'react'
import SearchBar from './components/SearchBar'
import PaperCard from './components/PaperCard'
import GraphView from './components/GraphView'
import { searchPapers } from './api/papers'
import { triggerCrawl, fetchGraph } from './api/graph'

// view: 'search' | 'crawling' | 'graph'

export default function App() {
  const [view, setView]         = useState('search')
  const [results, setResults]   = useState([])
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState(null)
  const [query, setQuery]       = useState('')
  const [searched, setSearched] = useState(false)

  const [crawlStatus, setCrawlStatus] = useState('')
  const [crawlError, setCrawlError]   = useState(null)
  const [graphData, setGraphData]     = useState(null)
  const [seedPaperId, setSeedPaperId] = useState(null)

  // ── Search ────────────────────────────────────────────────────────────────
  async function handleSearch(q) {
    setQuery(q)
    setSearching(true)
    setSearchError(null)
    setSearched(false)
    try {
      const data = await searchPapers(q)
      setResults(data.results ?? [])
    } catch (e) {
      setSearchError(e.message)
      setResults([])
    } finally {
      setSearching(false)
      setSearched(true)
    }
  }

  // ── Explore (crawl → graph) ───────────────────────────────────────────────
  async function handleExplore(paper) {
    setSeedPaperId(paper.paper_id)
    setCrawlError(null)
    setView('crawling')
    setCrawlStatus(`Crawling citation network for "${paper.title}"…`)

    try {
      const summary = await triggerCrawl(paper.paper_id)
      setCrawlStatus(`Crawl complete — ${summary.papers_crawled} papers found. Loading graph…`)
      const data = await fetchGraph()
      setGraphData(data)
      setView('graph')
    } catch (e) {
      setCrawlError(e.message)
      setView('search')
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────
  if (view === 'graph' && graphData) {
    return (
      <div className="app app--wide">
        <GraphView
          data={graphData}
          seedPaperId={seedPaperId}
          onBack={() => setView('search')}
        />
      </div>
    )
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="logo">PaperTrail</h1>
        <p className="tagline">Explore the citation network of any research paper</p>
      </header>

      <main className="app-main">
        <SearchBar onSearch={handleSearch} loading={searching || view === 'crawling'} />

        {/* Crawl status */}
        {view === 'crawling' && (
          <div className="crawl-status">
            <div className="spinner" />
            <p>{crawlStatus}</p>
            <p className="crawl-note">This may take a minute while we fetch the citation network.</p>
          </div>
        )}

        {crawlError && <p className="status error">Crawl error: {crawlError}</p>}
        {searchError && <p className="status error">Error: {searchError}</p>}

        {!searching && searched && !searchError && results.length === 0 && view !== 'crawling' && (
          <p className="status empty">No papers found for "{query}"</p>
        )}

        {searching && <p className="status loading">Searching…</p>}

        {results.length > 0 && view === 'search' && (
          <section className="results">
            <p className="result-count">
              {results.length} result{results.length !== 1 ? 's' : ''} for "{query}"
            </p>
            {results.map(paper => (
              <PaperCard
                key={paper.paper_id}
                paper={paper}
                onExplore={handleExplore}
              />
            ))}
          </section>
        )}
      </main>
    </div>
  )
}
