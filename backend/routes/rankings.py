from flask import Blueprint, jsonify, request

from backend.models.citation import Citation
from backend.models.paper import Paper
from backend.services.pagerank import ranked_papers

rankings_bp = Blueprint("rankings", __name__)


@rankings_bp.route("/rankings", methods=["GET"])
def get_rankings():
    """
    Return papers ranked by PageRank over the full citation graph.

    Query params:
      limit  — max results to return (default 50, max 500)
      alpha  — PageRank damping factor (default 0.85)
    """
    limit = min(int(request.args.get("limit", 50)), 500)
    alpha = float(request.args.get("alpha", 0.85))

    if not (0.0 < alpha < 1.0):
        return jsonify({"error": "alpha must be between 0 and 1 (exclusive)"}), 400

    papers = Paper.query.all()
    if not papers:
        return jsonify({"papers": [], "total_papers": 0, "total_citations": 0}), 200

    citations = Citation.query.all()
    results = ranked_papers(papers, citations, limit=limit, alpha=alpha)

    return jsonify({
        "papers": results,
        "total_papers": len(papers),
        "total_citations": len(citations),
    }), 200
