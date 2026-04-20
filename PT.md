PaperTrail is an AI-powered academic paper navigator. It takes a seed paper, crawls its citation network, and presents an interactive visual graph so researchers can explore connected papers, find foundational work, and discover unexpected connections.
The core motivation is twofold: researchers waste too much time on literature review, and the serendipitous discovery that used to happen when browsing library shelves has been lost to keyword search engines. PaperTrail solves both.
Tech Stack

Backend: Python, Flask
Frontend: React, D3.js for graph visualization
Database: PostgreSQL (paper metadata), Neo4j (citation graph relationships)
APIs: Semantic Scholar API (paper data and citations)
NLP: SciBERT embeddings (semantic similarity between papers)
Graph Algorithms: PageRank (paper importance ranking), NetworkX

Project Structure
TEST_PT_1/
├── backend/          # Python Flask API
├── frontend/         # React app with D3.js visualization
├── CLAUDE.md         # This file
├── README.md
├── .gitignore
└── .env.example
How the System Works

User inputs a seed paper (title, DOI, or Semantic Scholar ID)
Backend calls Semantic Scholar API to fetch the paper's metadata, references, and citations
Citation crawler uses BFS with semantic similarity filtering:

For each connected paper, compute SciBERT embedding similarity to the seed
Only follow branches above a relevance threshold (~0.6)
Max depth: 2-3 levels, max papers: ~500
Tracks visited papers to avoid duplicates


PageRank ranks papers by importance in the network (not just raw citation count)
Results stored in PostgreSQL (metadata) and Neo4j (graph relationships)
Frontend renders an interactive D3.js force-directed graph:

Nodes = papers, size = importance
Edges = citation relationships
Users can zoom, click, and explore



MVP Features

Search by paper title or ID
Citation network crawling with semantic filtering
Interactive graph visualization
Paper importance ranking via PageRank
Paper detail view (title, authors, abstract, year, citations)
Export to BibTeX

Coding Conventions

Python: use type hints, docstrings on all functions
React: functional components with hooks
API endpoints: RESTful, prefix with /api/v1/
Environment variables for all API keys and config (never hardcode)
Git: meaningful commit messages, feature branches