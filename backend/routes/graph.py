from flask import Blueprint, jsonify

from backend.models.citation import Citation
from backend.models.paper import Paper
from backend.services.pagerank import compute_pagerank

graph_bp = Blueprint("graph", __name__)


@graph_bp.route("/graph", methods=["GET"])
def get_graph():
    papers = Paper.query.all()
    if not papers:
        return jsonify({"nodes": [], "links": []}), 200

    citations = Citation.query.all()
    scores = compute_pagerank(papers, citations)
    paper_ids = {p.id for p in papers}

    nodes = [
        {
            "id": p.id,
            "paper_id": p.semantic_scholar_id,
            "title": p.title,
            "year": p.year,
            "authors": p.authors or [],
            "abstract": p.abstract,
            "citation_count": p.citation_count,
            "pagerank": round(scores.get(p.id, 0.0), 8),
            "field": p.field,
        }
        for p in papers
    ]

    # Only emit links where both endpoints exist as nodes
    links = [
        {"source": c.citing_paper_id, "target": c.cited_paper_id}
        for c in citations
        if c.citing_paper_id in paper_ids and c.cited_paper_id in paper_ids
    ]

    return jsonify({"nodes": nodes, "links": links}), 200
