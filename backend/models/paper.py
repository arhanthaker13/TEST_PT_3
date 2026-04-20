from sqlalchemy import JSON, func

from backend.db import db


class Paper(db.Model):
    __tablename__ = "papers"

    id = db.Column(db.Integer, primary_key=True)
    semantic_scholar_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    title = db.Column(db.Text, nullable=False)
    abstract = db.Column(db.Text, nullable=True)
    year = db.Column(db.Integer, nullable=True)
    citation_count = db.Column(db.Integer, default=0, nullable=False)
    authors = db.Column(JSON, nullable=True)
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "semantic_scholar_id": self.semantic_scholar_id,
            "title": self.title,
            "abstract": self.abstract,
            "year": self.year,
            "citation_count": self.citation_count,
            "authors": self.authors or [],
        }
