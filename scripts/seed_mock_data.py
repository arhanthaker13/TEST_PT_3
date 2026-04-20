"""
Seed the database with mock paper data for local testing.

    python scripts/seed_mock_data.py

Clears existing data and inserts all papers and citations from
data/mock_papers.json. Safe to run multiple times.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app import create_app
from backend.db import db
from backend.models.paper import Paper
from backend.models.citation import Citation
from backend.services.mock_semantic_scholar import MockSemanticScholarService, _load


def seed_mock_data() -> dict:
    data = _load()
    papers_by_mock_id: dict[str, Paper] = {}

    # Wipe existing data
    Citation.query.delete()
    Paper.query.delete()

    for p in data["papers"]:
        paper = Paper(
            semantic_scholar_id=p["id"],
            title=p["title"],
            abstract=p.get("abstract"),
            year=p.get("year"),
            citation_count=p.get("citation_count", 0),
            authors=p.get("authors", []),
        )
        db.session.add(paper)
        db.session.flush()
        papers_by_mock_id[p["id"]] = paper

    for edge in data["citations"]:
        citing = papers_by_mock_id.get(edge["citing_id"])
        cited = papers_by_mock_id.get(edge["cited_id"])
        if citing and cited:
            db.session.add(Citation(citing_paper_id=citing.id, cited_paper_id=cited.id))

    db.session.commit()
    return {"papers_seeded": len(data["papers"]), "citations_seeded": len(data["citations"])}


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
        result = seed_mock_data()
        print(f"Seeded {result['papers_seeded']} papers and {result['citations_seeded']} citations.")
