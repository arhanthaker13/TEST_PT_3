from flask import Blueprint, jsonify, request

from backend.services.semantic_scholar import (
    PaperNotFoundError,
    RateLimitError,
    SemanticScholarError,
    get_service,
)

papers_bp = Blueprint("papers", __name__)
_service = get_service()


@papers_bp.route("/papers/<paper_id>", methods=["GET"])
def get_paper(paper_id: str):
    """Fetch a paper's metadata, references, and citations by Semantic Scholar ID."""
    try:
        paper = _service.fetch_paper(paper_id)
        return jsonify(paper), 200
    except PaperNotFoundError:
        return jsonify({"error": "Paper not found"}), 404
    except RateLimitError:
        return jsonify({"error": "Upstream rate limit reached, try again shortly"}), 429
    except SemanticScholarError as e:
        return jsonify({"error": str(e)}), 502


@papers_bp.route("/papers/search", methods=["GET"])
def search_papers():
    """Search for papers by title or keywords. Query param: ?q=<query>&limit=<n>"""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing query parameter 'q'"}), 400

    limit = min(int(request.args.get("limit", 5)), 20)

    try:
        results = _service.search_paper(query, limit=limit)
        return jsonify({"results": results, "count": len(results)}), 200
    except RateLimitError:
        return jsonify({"error": "Upstream rate limit reached, try again shortly"}), 429
    except SemanticScholarError as e:
        return jsonify({"error": str(e)}), 502
