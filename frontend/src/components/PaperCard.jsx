export default function PaperCard({ paper, onExplore }) {
  const authors = paper.authors ?? []
  const displayAuthors =
    authors.length > 3
      ? authors.slice(0, 3).join(', ') + ' et al.'
      : authors.join(', ')

  const abstract = paper.abstract ?? ''
  const shortAbstract = abstract.length > 320 ? abstract.slice(0, 320) + '…' : abstract

  return (
    <article className="paper-card">
      <h2 className="paper-title">{paper.title}</h2>

      <div className="paper-meta">
        {displayAuthors && <span className="authors">{displayAuthors}</span>}
        {paper.year && <span className="year">{paper.year}</span>}
        {paper.citation_count != null && (
          <span className="citations">{paper.citation_count.toLocaleString()} citations</span>
        )}
      </div>

      {shortAbstract && <p className="abstract">{shortAbstract}</p>}

      <div className="paper-actions">
        {onExplore && (
          <button className="btn-explore" onClick={() => onExplore(paper)}>
            Explore Network
          </button>
        )}
        {paper.paper_id && (
          <a
            className="ss-link"
            href={`https://www.semanticscholar.org/paper/${paper.paper_id}`}
            target="_blank"
            rel="noreferrer"
          >
            View on Semantic Scholar →
          </a>
        )}
      </div>
    </article>
  )
}
