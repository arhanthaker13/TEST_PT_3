export default function PaperList({ nodes, selectedId, onSelect }) {
  const sorted = [...nodes].sort((a, b) => (b.pagerank || 0) - (a.pagerank || 0))

  return (
    <aside className="paper-list">
      <div className="paper-list-header">Papers by Importance</div>
      <ol className="paper-list-items">
        {sorted.map((node, i) => (
          <li
            key={node.id}
            className={`paper-list-item${node.id === selectedId ? ' paper-list-item--active' : ''}`}
            onClick={() => onSelect(node)}
          >
            <span className="paper-list-rank">{i + 1}</span>
            <span className="paper-list-title">
              {node.title || node.id}
            </span>
          </li>
        ))}
      </ol>
    </aside>
  )
}
