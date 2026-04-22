function importanceScore(pagerank, maxPagerank) {
  if (!pagerank || !maxPagerank) return null
  return Math.max(1, Math.round(Math.sqrt(pagerank / maxPagerank) * 10))
}

export default function NodeDetail({ node, maxPagerank, onClose }) {
  const authors = node.authors ?? []

  return (
    <aside className="node-detail">
      <button className="node-detail-close" onClick={onClose} aria-label="Close">×</button>

      <h2 className="node-detail-title">{node.title}</h2>

      <dl className="node-detail-meta">
        {authors.length > 0 && (
          <div><dt>Authors</dt><dd>{authors.join(', ')}</dd></div>
        )}
        {node.year && (
          <div><dt>Year</dt><dd>{node.year}</dd></div>
        )}
        {node.citation_count != null && (
          <div><dt>Citations</dt><dd>{node.citation_count.toLocaleString()}</dd></div>
        )}
        {node.pagerank != null && (
          <div><dt>Importance</dt><dd>{importanceScore(node.pagerank, maxPagerank)}/10</dd></div>
        )}
      </dl>

      {node.abstract && (
        <p className="node-detail-abstract">{node.abstract}</p>
      )}

      {node.paper_id && (
        <a
          className="node-detail-link"
          href={`https://www.semanticscholar.org/paper/${node.paper_id}`}
          target="_blank"
          rel="noreferrer"
        >
          View on Semantic Scholar →
        </a>
      )}
    </aside>
  )
}
