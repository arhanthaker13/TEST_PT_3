import networkx as nx

from backend.models.citation import Citation
from backend.models.paper import Paper


def build_citation_graph(papers: list[Paper], citations: list[Citation]) -> nx.DiGraph:
    G = nx.DiGraph()
    G.add_nodes_from(p.id for p in papers)
    G.add_edges_from((c.citing_paper_id, c.cited_paper_id) for c in citations)
    return G


def compute_pagerank(
    papers: list[Paper],
    citations: list[Citation],
    alpha: float = 0.85,
) -> dict[int, float]:
    """Return {paper_db_id: pagerank_score} for every paper in the graph."""
    G = build_citation_graph(papers, citations)
    if G.number_of_nodes() == 0:
        return {}
    return nx.pagerank(G, alpha=alpha)


def ranked_papers(
    papers: list[Paper],
    citations: list[Citation],
    limit: int = 50,
    alpha: float = 0.85,
) -> list[dict]:
    """
    Return up to *limit* papers sorted by descending PageRank score.
    Each entry is the paper's to_dict() plus a 'pagerank_score' field.
    """
    scores = compute_pagerank(papers, citations, alpha=alpha)
    results = []
    for paper in papers:
        entry = paper.to_dict()
        entry["pagerank_score"] = round(scores.get(paper.id, 0.0), 8)
        results.append(entry)
    results.sort(key=lambda p: p["pagerank_score"], reverse=True)
    return results[:limit]
