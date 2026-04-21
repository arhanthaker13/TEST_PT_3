import os
import time
import requests
from typing import Optional


PAPER_FIELDS = "paperId,title,abstract,year,authors,citationCount,referenceCount,externalIds,publicationDate"
EDGE_FIELDS = "paperId,title,year,authors,citationCount"

BASE_URL = "https://api.semanticscholar.org/graph/v1"


class SemanticScholarError(Exception):
    pass


class PaperNotFoundError(SemanticScholarError):
    pass


class RateLimitError(SemanticScholarError):
    pass


class SemanticScholarService:
    def __init__(self) -> None:
        self.session = requests.Session()
        api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
        # Ignore placeholder values copied from .env.example
        if api_key and api_key != "your_api_key_here":
            self.session.headers["x-api-key"] = api_key

    def _get(self, url: str, params: dict, max_retries: int = 1) -> dict:
        for attempt in range(max_retries):
            try:
                resp = self.session.get(url, params=params, timeout=5)
            except requests.exceptions.RequestException as exc:
                raise SemanticScholarError(f"Semantic Scholar connection error: {exc}") from exc

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 404:
                raise PaperNotFoundError(f"Paper not found: {url}")

            if resp.status_code == 429:
                raise RateLimitError("Semantic Scholar rate limit exceeded")

            if resp.status_code in (401, 403):
                raise SemanticScholarError(
                    "Semantic Scholar rejected the API key — "
                    "remove or correct SEMANTIC_SCHOLAR_API_KEY in .env"
                )

            raise SemanticScholarError(f"Semantic Scholar error: HTTP {resp.status_code}")

        raise RateLimitError("Exhausted retries due to rate limiting")

    def fetch_paper(self, paper_id: str) -> dict:
        """Fetch metadata, references, and citations for a paper by its Semantic Scholar ID."""
        data = self._get(
            f"{BASE_URL}/paper/{paper_id}",
            params={"fields": f"{PAPER_FIELDS},references.{EDGE_FIELDS},citations.{EDGE_FIELDS}"},
        )
        return _normalize_paper(data)

    def search_paper(self, query: str, limit: int = 5) -> list[dict]:
        """Search for papers by title/keywords. Returns top matches."""
        data = self._get(
            f"{BASE_URL}/paper/search",
            params={"query": query, "fields": PAPER_FIELDS, "limit": limit},
        )
        return [_normalize_paper(p) for p in data.get("data", [])]


def _normalize_paper(raw: dict) -> dict:
    return {
        "paper_id": raw.get("paperId"),
        "title": raw.get("title"),
        "abstract": raw.get("abstract"),
        "year": raw.get("year"),
        "publication_date": raw.get("publicationDate"),
        "authors": [a.get("name") for a in raw.get("authors", [])],
        "citation_count": raw.get("citationCount"),
        "reference_count": raw.get("referenceCount"),
        "external_ids": raw.get("externalIds", {}),
        "references": [_normalize_edge(r) for r in raw.get("references", [])],
        "citations": [_normalize_edge(c) for c in raw.get("citations", [])],
    }


def _normalize_edge(raw: dict) -> dict:
    return {
        "paper_id": raw.get("paperId"),
        "title": raw.get("title"),
        "year": raw.get("year"),
        "authors": [a.get("name") for a in raw.get("authors", [])],
        "citation_count": raw.get("citationCount"),
    }


def get_service():
    """Return a FallbackService that tries Semantic Scholar then OpenAlex."""
    from backend.services.openalex import FallbackService, OpenAlexService
    return FallbackService(SemanticScholarService(), OpenAlexService())
