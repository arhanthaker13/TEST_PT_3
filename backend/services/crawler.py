import logging
from collections import deque

import numpy as np

from backend.db import db
from backend.models.citation import Citation
from backend.models.paper import Paper
from backend.services.embeddings import EmbeddingService, paper_text
from backend.services.semantic_scholar import (
    PaperNotFoundError,
    RateLimitError,
)

logger = logging.getLogger(__name__)

DEFAULT_SIMILARITY_THRESHOLD = 0.6


class CrawlerService:
    def __init__(
        self,
        ss_service=None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        from backend.services.semantic_scholar import get_service
        self.ss = ss_service or get_service()
        self.emb = embedding_service or EmbeddingService()

    def crawl(
        self,
        seed_paper_id: str,
        max_depth: int = 2,
        max_papers: int = 500,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> dict:
        """
        BFS from seed_paper_id.

        Before following any branch, the candidate paper's title is embedded
        with SciBERT and compared to the seed's title+abstract embedding.
        Branches below *similarity_threshold* are stored as stubs (edge
        preserved in graph) but not recursed into.

        If SciBERT is unavailable the crawl proceeds without filtering.
        """
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(seed_paper_id, 0)])
        papers_crawled = 0
        papers_skipped = 0
        papers_filtered = 0

        # Fetch and embed the seed paper first so we have a reference vector.
        seed_data = self.ss.fetch_paper(seed_paper_id)
        seed_record = _upsert_paper_full(seed_data)
        db.session.commit()

        seed_embedding: np.ndarray | None = self.emb.embed(
            paper_text(seed_data.get("title"), seed_data.get("abstract"))
        )
        embedding_cache: dict[str, np.ndarray] = {}
        if seed_embedding is not None:
            embedding_cache[seed_paper_id] = seed_embedding

        visited.add(seed_paper_id)
        papers_crawled += 1

        # Enqueue seed's neighbors at depth 1.
        for ref in seed_data.get("references", []):
            if ref.get("paper_id") and ref["paper_id"] not in visited:
                queue.append((ref["paper_id"], 1))
        for cit in seed_data.get("citations", []):
            if cit.get("paper_id") and cit["paper_id"] not in visited:
                queue.append((cit["paper_id"], 1))

        # Store seed's edges immediately (stubs for neighbors).
        for ref in seed_data.get("references", []):
            if ref.get("paper_id"):
                ref_record = _upsert_paper_stub(ref)
                _upsert_citation(citing=seed_record, cited=ref_record)
        for cit in seed_data.get("citations", []):
            if cit.get("paper_id"):
                cit_record = _upsert_paper_stub(cit)
                _upsert_citation(citing=cit_record, cited=seed_record)
        db.session.commit()

        # BFS main loop (depth >= 1).
        while queue and papers_crawled < max_papers:
            paper_id, depth = queue.popleft()

            if paper_id in visited:
                continue
            visited.add(paper_id)

            try:
                data = self.ss.fetch_paper(paper_id)
            except PaperNotFoundError:
                papers_skipped += 1
                continue
            except RateLimitError:
                raise

            paper_record = _upsert_paper_full(data)
            papers_crawled += 1

            if depth < max_depth:
                for neighbor in (*data.get("references", []), *data.get("citations", [])):
                    nb_id = neighbor.get("paper_id")
                    if not nb_id or nb_id in visited:
                        continue

                    if _should_follow(
                        neighbor,
                        seed_embedding,
                        embedding_cache,
                        similarity_threshold,
                        self.emb,
                    ):
                        queue.append((nb_id, depth + 1))
                    else:
                        papers_filtered += 1
                        logger.debug("Filtered paper %s (below threshold)", nb_id)

            for ref in data.get("references", []):
                if ref.get("paper_id"):
                    ref_record = _upsert_paper_stub(ref)
                    _upsert_citation(citing=paper_record, cited=ref_record)
            for cit in data.get("citations", []):
                if cit.get("paper_id"):
                    cit_record = _upsert_paper_stub(cit)
                    _upsert_citation(citing=cit_record, cited=paper_record)

            db.session.commit()

        return {
            "seed_paper_id": seed_paper_id,
            "papers_crawled": papers_crawled,
            "papers_skipped": papers_skipped,
            "papers_filtered": papers_filtered,
            "similarity_filtering": seed_embedding is not None,
            "max_depth": max_depth,
            "similarity_threshold": similarity_threshold,
        }


# ---------------------------------------------------------------------------
# Similarity gating
# ---------------------------------------------------------------------------

def _should_follow(
    neighbor: dict,
    seed_embedding: np.ndarray | None,
    cache: dict[str, np.ndarray],
    threshold: float,
    emb_service: EmbeddingService,
) -> bool:
    """
    Return True if *neighbor* is similar enough to the seed to be worth crawling.
    Falls back to True when SciBERT is unavailable (seed_embedding is None).
    """
    if seed_embedding is None:
        return True

    nb_id = neighbor["paper_id"]
    if nb_id not in cache:
        vec = emb_service.embed(paper_text(neighbor.get("title")))
        if vec is None:
            return True  # fail-open
        cache[nb_id] = vec

    similarity = emb_service.cosine_similarity(seed_embedding, cache[nb_id])
    return similarity >= threshold


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _upsert_paper_full(data: dict) -> Paper:
    """Insert or overwrite a paper with full metadata from a fetch_paper() response."""
    paper = Paper.query.filter_by(semantic_scholar_id=data["paper_id"]).first()
    if paper is None:
        paper = Paper(semantic_scholar_id=data["paper_id"])
        db.session.add(paper)
    paper.title = data.get("title") or ""
    paper.abstract = data.get("abstract")
    paper.year = data.get("year")
    paper.citation_count = data.get("citation_count") or 0
    paper.authors = data.get("authors") or []
    paper.field = data.get("field")
    db.session.flush()
    return paper


def _upsert_paper_stub(data: dict) -> Paper:
    """
    Insert a paper from edge data (title, year, authors — no abstract).
    Does NOT overwrite an existing record so a later full upsert wins.
    """
    paper = Paper.query.filter_by(semantic_scholar_id=data["paper_id"]).first()
    if paper is None:
        paper = Paper(
            semantic_scholar_id=data["paper_id"],
            title=data.get("title") or "",
            year=data.get("year"),
            citation_count=data.get("citation_count") or 0,
            authors=data.get("authors") or [],
        )
        db.session.add(paper)
        db.session.flush()
    return paper


def _upsert_citation(citing: Paper, cited: Paper) -> None:
    """Create a directed citation edge if it doesn't already exist."""
    exists = Citation.query.filter_by(
        citing_paper_id=citing.id,
        cited_paper_id=cited.id,
    ).first()
    if not exists:
        db.session.add(Citation(citing_paper_id=citing.id, cited_paper_id=cited.id))
