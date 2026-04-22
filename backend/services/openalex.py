import logging
import os
import time

import requests

from backend.services.semantic_scholar import PaperNotFoundError, RateLimitError, SemanticScholarError

logger = logging.getLogger(__name__)

OA_BASE = "https://api.openalex.org"

_WORK_FIELDS = "id,title,publication_year,cited_by_count,authorships,abstract_inverted_index,referenced_works,ids"
_EDGE_FIELDS = "id,title,publication_year,cited_by_count,authorships"


def _is_oa_id(paper_id: str) -> bool:
    return len(paper_id) > 1 and paper_id[0].upper() == "W" and paper_id[1:].isdigit()


def _short_id(url_or_id: str) -> str:
    """Extract W-number from a full OA URL or return the ID as-is."""
    return url_or_id.split("/")[-1]


def _reconstruct_abstract(inv_idx: dict | None) -> str | None:
    if not inv_idx:
        return None
    positions: dict[int, str] = {}
    for word, pos_list in inv_idx.items():
        for pos in pos_list:
            positions[pos] = word
    return " ".join(positions[i] for i in sorted(positions))


def _normalize_work(raw: dict) -> dict:
    return {
        "paper_id": _short_id(raw.get("id", "")),
        "title": raw.get("title"),
        "abstract": _reconstruct_abstract(raw.get("abstract_inverted_index")),
        "year": raw.get("publication_year"),
        "citation_count": raw.get("cited_by_count", 0),
        "authors": [
            a["author"]["display_name"]
            for a in raw.get("authorships", [])
            if a.get("author") and a["author"].get("display_name")
        ],
        "references": [],
        "citations": [],
    }


def _normalize_edge(raw: dict) -> dict:
    return {
        "paper_id": _short_id(raw.get("id", "")),
        "title": raw.get("title"),
        "year": raw.get("publication_year"),
        "citation_count": raw.get("cited_by_count", 0),
        "authors": [
            a["author"]["display_name"]
            for a in raw.get("authorships", [])
            if a.get("author") and a["author"].get("display_name")
        ],
    }


class OpenAlexService:
    def __init__(self) -> None:
        self.session = requests.Session()
        email = os.getenv("OPENALEX_EMAIL", "").strip()
        ua = "PaperTrail/1.0"
        if email:
            ua += f" (mailto:{email})"
        self.session.headers["User-Agent"] = ua

    def _get(self, url: str, params: dict) -> dict:
        time.sleep(0.15)
        resp = self.session.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (400, 404):
            raise PaperNotFoundError(f"OpenAlex: not found — {url} (HTTP {resp.status_code})")
        if resp.status_code == 429:
            raise RateLimitError("OpenAlex rate limit exceeded")
        raise SemanticScholarError(f"OpenAlex error: HTTP {resp.status_code}")

    def _fetch_raw_work(self, paper_id: str) -> dict:
        if _is_oa_id(paper_id):
            return self._get(f"{OA_BASE}/works/{paper_id}", {"select": _WORK_FIELDS})

        # Try to resolve a Semantic Scholar ID via OpenAlex's external ID filter
        data = self._get(
            f"{OA_BASE}/works",
            {"filter": f"ids.semantic_scholar:{paper_id}", "per-page": 1, "select": _WORK_FIELDS},
        )
        results = data.get("results", [])
        if not results:
            raise PaperNotFoundError(f"OpenAlex: no paper with Semantic Scholar ID {paper_id}")
        return results[0]

    def _fetch_stubs_batch(self, oa_ids: list[str]) -> list[dict]:
        if not oa_ids:
            return []
        results = []
        for i in range(0, len(oa_ids), 50):
            batch = oa_ids[i : i + 50]
            data = self._get(
                f"{OA_BASE}/works",
                {"filter": f"ids.openalex:{'|'.join(batch)}", "per-page": 50, "select": _EDGE_FIELDS},
            )
            results.extend(data.get("results", []))
        return results

    def _fetch_citations(self, oa_id: str, limit: int = 25) -> list[dict]:
        data = self._get(
            f"{OA_BASE}/works",
            {"filter": f"cites:{oa_id}", "per-page": limit, "select": _EDGE_FIELDS},
        )
        return data.get("results", [])

    def fetch_paper(self, paper_id: str) -> dict:
        raw = self._fetch_raw_work(paper_id)
        oa_id = _short_id(raw["id"])

        ref_ids = [_short_id(u) for u in raw.get("referenced_works", [])[:50]]
        ref_raws = self._fetch_stubs_batch(ref_ids)
        cit_raws = self._fetch_citations(oa_id)

        result = _normalize_work(raw)
        result["references"] = [_normalize_edge(r) for r in ref_raws]
        result["citations"] = [_normalize_edge(c) for c in cit_raws]
        return result

    def search_paper(self, query: str, limit: int = 5) -> list[dict]:
        data = self._get(
            f"{OA_BASE}/works",
            {"search": query, "per-page": limit, "select": _WORK_FIELDS},
        )
        return [_normalize_work(w) for w in data.get("results", [])]


class FallbackService:
    """Tries Semantic Scholar first; falls back to OpenAlex on rate-limit or any SS error."""

    def __init__(self, primary, fallback) -> None:
        self.primary = primary
        self.fallback = fallback

    def fetch_paper(self, paper_id: str) -> dict:
        try:
            return self.primary.fetch_paper(paper_id)
        except (RateLimitError, SemanticScholarError) as exc:
            logger.warning("SS unavailable (%s), falling back to OpenAlex for %s", exc, paper_id)
            return self.fallback.fetch_paper(paper_id)

    def search_paper(self, query: str, limit: int = 5) -> list[dict]:
        try:
            return self.primary.search_paper(query, limit)
        except (RateLimitError, SemanticScholarError) as exc:
            logger.warning("SS unavailable (%s), falling back to OpenAlex for query: %s", exc, query)
            return self.fallback.search_paper(query, limit)
