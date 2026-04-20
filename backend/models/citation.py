from sqlalchemy import UniqueConstraint

from backend.db import db


class Citation(db.Model):
    __tablename__ = "citations"
    __table_args__ = (
        UniqueConstraint("citing_paper_id", "cited_paper_id", name="uq_citation_edge"),
    )

    id = db.Column(db.Integer, primary_key=True)
    # The paper that contains the reference (points outward)
    citing_paper_id = db.Column(
        db.Integer, db.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The paper being referenced (pointed to)
    cited_paper_id = db.Column(
        db.Integer, db.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    citing_paper = db.relationship(
        "Paper", foreign_keys=[citing_paper_id], backref="outgoing_citations"
    )
    cited_paper = db.relationship(
        "Paper", foreign_keys=[cited_paper_id], backref="incoming_citations"
    )

    def to_dict(self) -> dict:
        return {
            "citing_paper_id": self.citing_paper_id,
            "cited_paper_id": self.cited_paper_id,
        }
