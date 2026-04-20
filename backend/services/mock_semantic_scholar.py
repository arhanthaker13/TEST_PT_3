import json
from pathlib import Path

MOCK_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "mock_papers.json"


def _load():
    with open(MOCK_DATA_PATH) as f:
        return json.load(f)


def _to_edge(paper: dict) -> dict:
    return {
        "paper_id": paper["id"],
        "title": paper["title"],
        "year": paper.get("year"),
        "authors": paper.get("authors", []),
        "citation_count": paper.get("citation_count", 0),
    }


def _normalize(paper: dict, references: list, citations: list) -> dict:
    return {
        "paper_id": paper["id"],
        "title": paper["title"],
        "abstract": paper.get("abstract"),
        "year": paper.get("year"),
        "publication_date": paper.get("publication_date"),
        "authors": paper.get("authors", []),
        "citation_count": paper.get("citation_count", 0),
        "reference_count": len(references),
        "external_ids": {},
        "references": [_to_edge(r) for r in references],
        "citations": [_to_edge(c) for c in citations],
    }


class MockSemanticScholarService:
    def __init__(self) -> None:
        data = _load()
        self._papers: dict[str, dict] = {p["id"]: p for p in data["papers"]}
        self._citation_edges: list[dict] = data["citations"]

    def fetch_paper(self, paper_id: str) -> dict:
        paper = self._papers.get(paper_id)
        if paper is None:
            # Fall back to first mock paper so crawl always works regardless of seed ID
            paper = next(iter(self._papers.values()))

        references = [
            self._papers[e["cited_id"]]
            for e in self._citation_edges
            if e["citing_id"] == paper["id"] and e["cited_id"] in self._papers
        ]
        citations = [
            self._papers[e["citing_id"]]
            for e in self._citation_edges
            if e["cited_id"] == paper["id"] and e["citing_id"] in self._papers
        ]
        return _normalize(paper, references, citations)

    def search_paper(self, query: str, limit: int = 5) -> list[dict]:
        q = query.lower()
        matches = [
            p for p in self._papers.values()
            if q in p["title"].lower() or q in p.get("abstract", "").lower()
        ]
        return [_normalize(p, [], []) for p in matches[:limit]]
