export default function GraphFilters({ nodes, filters, onChange }) {
  const years = nodes.map(n => n.year).filter(Boolean)
  const dataYearMin = years.length ? Math.min(...years) : 2000
  const dataYearMax = years.length ? Math.max(...years) : new Date().getFullYear()

  function set(key, value) {
    onChange({ ...filters, [key]: value })
  }

  function reset() {
    onChange({ yearMin: '', yearMax: '', minCitations: '', keyword: '' })
  }

  const isDirty = filters.yearMin || filters.yearMax || filters.minCitations || filters.keyword

  return (
    <div className="graph-filters">
      <div className="filter-group">
        <label className="filter-label">Year</label>
        <input
          className="filter-input filter-input--year"
          type="number"
          placeholder={String(dataYearMin)}
          value={filters.yearMin}
          min={dataYearMin}
          max={dataYearMax}
          onChange={e => set('yearMin', e.target.value)}
        />
        <span className="filter-sep">–</span>
        <input
          className="filter-input filter-input--year"
          type="number"
          placeholder={String(dataYearMax)}
          value={filters.yearMax}
          min={dataYearMin}
          max={dataYearMax}
          onChange={e => set('yearMax', e.target.value)}
        />
      </div>

      <div className="filter-group">
        <label className="filter-label">Min citations</label>
        <input
          className="filter-input filter-input--citations"
          type="number"
          placeholder="0"
          value={filters.minCitations}
          min={0}
          onChange={e => set('minCitations', e.target.value)}
        />
      </div>

      <div className="filter-group filter-group--keyword">
        <label className="filter-label">Keyword</label>
        <input
          className="filter-input filter-input--keyword"
          type="text"
          placeholder="Search title or abstract…"
          value={filters.keyword}
          onChange={e => set('keyword', e.target.value)}
        />
      </div>

      {isDirty && (
        <button className="filter-reset" onClick={reset}>Reset</button>
      )}
    </div>
  )
}
