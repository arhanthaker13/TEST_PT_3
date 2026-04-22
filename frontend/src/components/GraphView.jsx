import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'
import NodeDetail from './NodeDetail'
import PaperList from './PaperList'
import GraphFilters from './GraphFilters'

const SEED_COLOR    = '#f59e0b'
const SEL_STROKE    = '#1d4ed8'
const HOVER_STROKE  = '#94a3b8'
const LINK_COLOR    = '#cbd5e1'
const FADED_OPACITY = 0.08

const COLOR_POOL = [
  '#2563eb', '#dc2626', '#16a34a', '#7c3aed', '#ea580c',
  '#0891b2', '#db2777', '#ca8a04', '#0f766e', '#84cc16',
  '#92400e', '#0369a1', '#9333ea', '#c2410c', '#0e7490',
  '#15803d', '#b45309', '#6d28d9', '#1d9bf0', '#be185d',
]
const DEFAULT_COLOR = '#6366f1'

function fieldColor(field) {
  if (!field) return DEFAULT_COLOR
  let h = 5381
  for (let i = 0; i < field.length; i++) {
    h = ((h << 5) + h) ^ field.charCodeAt(i)
  }
  return COLOR_POOL[Math.abs(h) % COLOR_POOL.length]
}

const EMPTY_FILTERS = { yearMin: '', yearMax: '', minCitations: '', keyword: '' }

function isVisible(node, filters) {
  if (filters.keyword) {
    const kw = filters.keyword.toLowerCase()
    if (!node.title?.toLowerCase().includes(kw) && !node.abstract?.toLowerCase().includes(kw)) {
      return false
    }
  }
  if (filters.yearMin !== '' && node.year != null && node.year < Number(filters.yearMin)) return false
  if (filters.yearMax !== '' && node.year != null && node.year > Number(filters.yearMax)) return false
  if (filters.minCitations !== '' && (node.citation_count ?? 0) < Number(filters.minCitations)) return false
  return true
}

export default function GraphView({ data, seedPaperId, onBack }) {
  const containerRef   = useRef(null)
  const svgRef         = useRef(null)
  const highlightFnRef = useRef(null)
  const nodeGroupRef   = useRef(null)
  const linkRef        = useRef(null)
  const tooltipRef     = useRef(null)

  const [selected, setSelected] = useState(null)
  const [filters, setFilters]   = useState(EMPTY_FILTERS)

  // ── Main D3 effect ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!data?.nodes?.length || !svgRef.current || !containerRef.current) return

    const { width, height } = containerRef.current.getBoundingClientRect()

    const nodes = data.nodes.map(d => ({ ...d }))
    const links = data.links.map(d => ({ ...d }))

    const nodeIdSet = new Set(nodes.map(n => n.id))
    const validLinks = links.filter(
      l => nodeIdSet.has(l.source) && nodeIdSet.has(l.target)
    )

    // Build lookup structures for color propagation
    const nodeById = new Map(nodes.map(n => [n.id, n]))
    const adjMap = new Map()
    for (const l of validLinks) {
      if (!adjMap.has(l.source)) adjMap.set(l.source, new Set())
      if (!adjMap.has(l.target)) adjMap.set(l.target, new Set())
      adjMap.get(l.source).add(l.target)
      adjMap.get(l.target).add(l.source)
    }

    function resolveColor(node) {
      if (node.paper_id === seedPaperId) return SEED_COLOR
      if (node.field) return fieldColor(node.field)
      const neighborIds = adjMap.get(node.id) || new Set()
      let best = null
      for (const nId of neighborIds) {
        const nb = nodeById.get(nId)
        if (nb?.field && (!best || (nb.pagerank || 0) > (best.pagerank || 0))) best = nb
      }
      return best ? fieldColor(best.field) : DEFAULT_COLOR
    }

    const prMax = d3.max(nodes, d => d.pagerank) || 1e-10
    const radius = d3.scaleSqrt().domain([0, prMax]).range([5, 20])

    const labelNodes = new Set(
      [...nodes].sort((a, b) => (b.pagerank || 0) - (a.pagerank || 0))
        .slice(0, 15)
        .map(n => n.id)
    )

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()
    svg.attr('width', width).attr('height', height)

    const g = svg.append('g')

    svg.call(
      d3.zoom()
        .scaleExtent([0.05, 10])
        .on('zoom', e => g.attr('transform', e.transform))
    )

    svg.on('click', () => {
      activeDatum = null
      setSelected(null)
      nodeGroup.selectAll('circle').attr('stroke', '#fff').attr('stroke-width', 1.5)
    })

    const link = g.append('g')
      .selectAll('line')
      .data(validLinks)
      .join('line')
      .attr('stroke', LINK_COLOR)
      .attr('stroke-opacity', 0.45)
      .attr('stroke-width', 1)

    const nodeGroup = g.append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .style('cursor', 'pointer')

    nodeGroup.append('circle')
      .attr('r', d => radius(d.pagerank || 0))
      .attr('fill', d => resolveColor(d))
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)

    nodeGroup.filter(d => labelNodes.has(d.id))
      .append('text')
      .text(d => d.title ? d.title.slice(0, 24) + (d.title.length > 24 ? '…' : '') : '')
      .attr('dy', d => radius(d.pagerank || 0) + 11)
      .attr('text-anchor', 'middle')
      .attr('font-size', '8px')
      .attr('fill', '#475569')
      .style('pointer-events', 'none')
      .style('user-select', 'none')

    // Store selections so the filter effect can update them without re-simulating
    nodeGroupRef.current = nodeGroup
    linkRef.current = link

    let activeDatum = null

    function applyHighlight(d) {
      activeDatum = d
      setSelected(d)
      nodeGroup.selectAll('circle').attr('stroke', '#fff').attr('stroke-width', 1.5)
      nodeGroup.filter(n => n.id === d.id).select('circle')
        .attr('stroke', SEL_STROKE).attr('stroke-width', 2.5)
    }

    highlightFnRef.current = (nodeId) => {
      const d = nodes.find(n => n.id === nodeId)
      if (d) applyHighlight(d)
    }

    const tooltip = tooltipRef.current

    nodeGroup
      .on('click', function (event, d) {
        event.stopPropagation()
        applyHighlight(d)
      })
      .on('mouseenter', function (event, d) {
        if (d !== activeDatum) {
          d3.select(this).select('circle').attr('stroke', HOVER_STROKE).attr('stroke-width', 2)
        }
        if (tooltip && d.title) {
          tooltip.textContent = d.title
          tooltip.style.display = 'block'
          tooltip.style.left = (event.clientX + 14) + 'px'
          tooltip.style.top  = (event.clientY - 32) + 'px'
        }
      })
      .on('mousemove', function (event) {
        if (tooltip) {
          tooltip.style.left = (event.clientX + 14) + 'px'
          tooltip.style.top  = (event.clientY - 32) + 'px'
        }
      })
      .on('mouseleave', function (event, d) {
        if (d !== activeDatum) {
          d3.select(this).select('circle').attr('stroke', '#fff').attr('stroke-width', 1.5)
        }
        if (tooltip) tooltip.style.display = 'none'
      })

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

  // ── Filter effect — updates D3 opacity without restarting simulation ───────
  useEffect(() => {
    const nodeGroup = nodeGroupRef.current
    const link = linkRef.current
    if (!nodeGroup || !link) return

    const visibleIds = new Set(
      data.nodes.filter(n => isVisible(n, filters)).map(n => n.id)
    )

    nodeGroup
      .style('opacity', d => visibleIds.has(d.id) ? 1 : FADED_OPACITY)
      .style('pointer-events', d => visibleIds.has(d.id) ? null : 'none')

    link.style('opacity', d => {
      const srcId = typeof d.source === 'object' ? d.source.id : d.source
      const tgtId = typeof d.target === 'object' ? d.target.id : d.target
      return visibleIds.has(srcId) && visibleIds.has(tgtId) ? 0.45 : 0
    })
  }, [filters, data.nodes])

  const visibleNodes = data.nodes.filter(n => isVisible(n, filters))
  const isDirty = filters.yearMin || filters.yearMax || filters.minCitations || filters.keyword
  const hiddenCount = data.nodes.length - visibleNodes.length

  // Build legend from fields actually present in this graph
  const presentFields = [...new Set(data.nodes.map(n => n.field).filter(Boolean))]
    .map(field => ({ field, color: fieldColor(field) }))
    .sort((a, b) => a.field.localeCompare(b.field))

  return (
    <div className="graph-wrapper">
      <div className="graph-toolbar">
        <button className="btn-back" onClick={onBack}>← Back to search</button>
        <span className="graph-stats">
          {isDirty
            ? `${visibleNodes.length} of ${data.nodes.length} papers · ${data.links.length} citations`
            : `${data.nodes.length} papers · ${data.links.length} citations`
          }
          {isDirty && hiddenCount > 0 && (
            <span className="graph-hidden"> · {hiddenCount} hidden</span>
          )}
        </span>
        <div className="graph-legend">
          <span className="legend-item">
            <span className="legend-dot" style={{ background: SEED_COLOR }} />
            seed
          </span>
          {presentFields.map(({ field, color }) => (
            <span key={field} className="legend-item">
              <span className="legend-dot" style={{ background: color }} />
              {field}
            </span>
          ))}
        </div>
      </div>

      <GraphFilters nodes={data.nodes} filters={filters} onChange={setFilters} />

      <div className="graph-body">
        <PaperList
          nodes={visibleNodes}
          selectedId={selected?.id}
          onSelect={(node) => highlightFnRef.current?.(node.id)}
        />

        <div ref={tooltipRef} className="node-tooltip" />
        <div ref={containerRef} className="graph-container">
          <svg ref={svgRef} />
          {data.nodes.length === 0 && (
            <p className="graph-empty">No graph data yet. Run a crawl first.</p>
          )}
          {data.nodes.length > 0 && visibleNodes.length === 0 && (
            <p className="graph-empty">No papers match the current filters.</p>
          )}
        </div>

        {selected && (
          <NodeDetail node={selected} onClose={() => setSelected(null)} />
        )}
      </div>
    </div>
  )
}
