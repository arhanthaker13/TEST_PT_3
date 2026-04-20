import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'
import NodeDetail from './NodeDetail'

const SEED_COLOR   = '#f59e0b'  // amber — seed paper
const NODE_COLOR   = '#6366f1'  // indigo — all others
const SEL_STROKE   = '#1d4ed8'  // dark blue — selected
const HOVER_STROKE = '#94a3b8'  // slate — hover
const LINK_COLOR   = '#cbd5e1'

export default function GraphView({ data, seedPaperId, onBack }) {
  const containerRef = useRef(null)
  const svgRef       = useRef(null)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    if (!data?.nodes?.length || !svgRef.current || !containerRef.current) return

    const { width, height } = containerRef.current.getBoundingClientRect()

    // D3 mutates nodes/links — work on copies so React data stays clean
    const nodes = data.nodes.map(d => ({ ...d }))
    const links = data.links.map(d => ({ ...d }))

    // Filter out any links whose endpoints aren't present (safety net)
    const nodeIdSet = new Set(nodes.map(n => n.id))
    const validLinks = links.filter(
      l => nodeIdSet.has(l.source) && nodeIdSet.has(l.target)
    )

    // ── Scales ──────────────────────────────────────────────────────────────
    const prMax = d3.max(nodes, d => d.pagerank) || 1e-10
    const radius = d3.scaleSqrt().domain([0, prMax]).range([5, 20])

    const labelNodes = new Set(
      [...nodes].sort((a, b) => (b.pagerank || 0) - (a.pagerank || 0))
        .slice(0, 15)
        .map(n => n.id)
    )

    // ── SVG ─────────────────────────────────────────────────────────────────
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()
    svg.attr('width', width).attr('height', height)

    const g = svg.append('g')

    svg.call(
      d3.zoom()
        .scaleExtent([0.05, 10])
        .on('zoom', e => g.attr('transform', e.transform))
    )

    // Click on background → deselect
    svg.on('click', () => {
      setSelected(null)
      nodeGroup.selectAll('circle')
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5)
    })

    // ── Links ────────────────────────────────────────────────────────────────
    const link = g.append('g')
      .selectAll('line')
      .data(validLinks)
      .join('line')
      .attr('stroke', LINK_COLOR)
      .attr('stroke-opacity', 0.45)
      .attr('stroke-width', 1)

    // ── Nodes ────────────────────────────────────────────────────────────────
    const nodeGroup = g.append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .style('cursor', 'pointer')

    nodeGroup.append('circle')
      .attr('r', d => radius(d.pagerank || 0))
      .attr('fill', d => d.paper_id === seedPaperId ? SEED_COLOR : NODE_COLOR)
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)

    // Labels — top-N nodes only, below the circle
    nodeGroup.filter(d => labelNodes.has(d.id))
      .append('text')
      .text(d => d.title ? d.title.slice(0, 24) + (d.title.length > 24 ? '…' : '') : '')
      .attr('dy', d => radius(d.pagerank || 0) + 11)
      .attr('text-anchor', 'middle')
      .attr('font-size', '8px')
      .attr('fill', '#475569')
      .style('pointer-events', 'none')
      .style('user-select', 'none')

    // ── Interaction ──────────────────────────────────────────────────────────
    // Closure variable so hover/click handlers share state without React re-renders
    let activeDatum = null

    nodeGroup
      .on('click', function (event, d) {
        event.stopPropagation()
        activeDatum = d
        setSelected(d)
        nodeGroup.selectAll('circle').attr('stroke', '#fff').attr('stroke-width', 1.5)
        d3.select(this).select('circle').attr('stroke', SEL_STROKE).attr('stroke-width', 2.5)
      })
      .on('mouseenter', function (event, d) {
        if (d !== activeDatum) {
          d3.select(this).select('circle').attr('stroke', HOVER_STROKE).attr('stroke-width', 2)
        }
      })
      .on('mouseleave', function (event, d) {
        if (d !== activeDatum) {
          d3.select(this).select('circle').attr('stroke', '#fff').attr('stroke-width', 1.5)
        }
      })

    // ── Force simulation ─────────────────────────────────────────────────────
    const simulation = d3.forceSimulation(nodes)
      .force('link',    d3.forceLink(validLinks).id(d => d.id).distance(70))
      .force('charge',  d3.forceManyBody().strength(-130))
      .force('center',  d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide(d => radius(d.pagerank || 0) + 3))

    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
      nodeGroup.attr('transform', d => `translate(${d.x ?? 0},${d.y ?? 0})`)
    })

    // ── Drag ─────────────────────────────────────────────────────────────────
    nodeGroup.call(
      d3.drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x; d.fy = d.y
        })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
        .on('end',  (event, d) => {
          if (!event.active) simulation.alphaTarget(0)
          d.fx = null; d.fy = null
        })
    )

    return () => simulation.stop()
  }, [data, seedPaperId])

  return (
    <div className="graph-wrapper">
      <div className="graph-toolbar">
        <button className="btn-back" onClick={onBack}>← Back to search</button>
        <span className="graph-stats">
          {data.nodes.length} papers · {data.links.length} citations
          {' · '}
          <span className="legend-seed">■</span> seed paper
          {' '}
          <span className="legend-node">■</span> cited paper
        </span>
      </div>

      <div className="graph-body">
        <div ref={containerRef} className="graph-container">
          <svg ref={svgRef} />
          {data.nodes.length === 0 && (
            <p className="graph-empty">No graph data yet. Run a crawl first.</p>
          )}
        </div>

        {selected && (
          <NodeDetail node={selected} onClose={() => setSelected(null)} />
        )}
      </div>
    </div>
  )
}
