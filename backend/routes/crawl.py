from flask import Blueprint, jsonify, request

from backend.services.crawler import CrawlerService
from backend.services.semantic_scholar import RateLimitError, SemanticScholarError, get_service

crawl_bp = Blueprint("crawl", __name__)
_crawler = CrawlerService(ss_service=get_service())


@crawl_bp.route("/crawl", methods=["POST"])
def trigger_crawl():
    """
    Start a BFS crawl from a seed paper.

    Body: {"paper_id": "<semantic_scholar_id>", "max_depth": 2, "max_papers": 500}
    """
    body = request.get_json(silent=True) or {}
    paper_id = (body.get("paper_id") or "").strip()

    if not paper_id:
        return jsonify({"error": "Missing required field: paper_id"}), 400

    max_depth = int(body.get("max_depth", 2))
    max_papers = min(int(body.get("max_papers", 500)), 500)

    if max_depth < 0 or max_depth > 3:
        return jsonify({"error": "max_depth must be between 0 and 3"}), 400

    try:
        result = _crawler.crawl(
            seed_paper_id=paper_id,
            max_depth=max_depth,
            max_papers=max_papers,
        )
        return jsonify(result), 200
    except RateLimitError:
        return jsonify({"error": "Upstream rate limit hit during crawl — partial results saved"}), 429
    except SemanticScholarError as e:
        return jsonify({"error": str(e)}), 502
    except Exception as e:
        return jsonify({"error": f"Crawl failed: {str(e)}"}), 500
