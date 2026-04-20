import pytest
from unittest.mock import MagicMock, patch

from backend.services.semantic_scholar import (
    SemanticScholarService,
    PaperNotFoundError,
    RateLimitError,
)

# Realistic fixture matching Semantic Scholar API response shape
PAPER_FIXTURE = {
    "paperId": "204e3073870fae3d05bcbc2f6a8e263d08cafc29",
    "title": "Attention Is All You Need",
    "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
    "year": 2017,
    "publicationDate": "2017-06-12",
    "authors": [
        {"authorId": "1", "name": "Ashish Vaswani"},
        {"authorId": "2", "name": "Noam Shazeer"},
    ],
    "citationCount": 100000,
    "referenceCount": 1,
    "externalIds": {"ArXiv": "1706.03762", "DOI": "10.48550/arXiv.1706.03762"},
    "references": [
        {
            "paperId": "ref-001",
            "title": "Neural Machine Translation by Jointly Learning to Align and Translate",
            "year": 2015,
            "authors": [{"authorId": "3", "name": "Dzmitry Bahdanau"}],
            "citationCount": 20000,
        }
    ],
    "citations": [
        {
            "paperId": "cit-001",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "year": 2018,
            "authors": [{"authorId": "4", "name": "Jacob Devlin"}],
            "citationCount": 80000,
        }
    ],
}


def _mock_response(status_code: int, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


@pytest.fixture
def service() -> SemanticScholarService:
    svc = SemanticScholarService()
    return svc


# ---------------------------------------------------------------------------
# fetch_paper
# ---------------------------------------------------------------------------

class TestFetchPaper:
    def test_returns_normalized_metadata(self, service):
        service.session.get = MagicMock(return_value=_mock_response(200, PAPER_FIXTURE))

        paper = service.fetch_paper("204e3073870fae3d05bcbc2f6a8e263d08cafc29")

        assert paper["paper_id"] == "204e3073870fae3d05bcbc2f6a8e263d08cafc29"
        assert paper["title"] == "Attention Is All You Need"
        assert paper["year"] == 2017
        assert paper["publication_date"] == "2017-06-12"
        assert paper["citation_count"] == 100000
        assert paper["reference_count"] == 1
        assert paper["external_ids"] == {"ArXiv": "1706.03762", "DOI": "10.48550/arXiv.1706.03762"}

    def test_authors_are_extracted_as_name_list(self, service):
        service.session.get = MagicMock(return_value=_mock_response(200, PAPER_FIXTURE))

        paper = service.fetch_paper("204e3073870fae3d05bcbc2f6a8e263d08cafc29")

        assert paper["authors"] == ["Ashish Vaswani", "Noam Shazeer"]

    def test_references_are_normalized(self, service):
        service.session.get = MagicMock(return_value=_mock_response(200, PAPER_FIXTURE))

        paper = service.fetch_paper("204e3073870fae3d05bcbc2f6a8e263d08cafc29")

        assert len(paper["references"]) == 1
        ref = paper["references"][0]
        assert ref["paper_id"] == "ref-001"
        assert ref["title"] == "Neural Machine Translation by Jointly Learning to Align and Translate"
        assert ref["year"] == 2015
        assert ref["authors"] == ["Dzmitry Bahdanau"]
        assert ref["citation_count"] == 20000

    def test_citations_are_normalized(self, service):
        service.session.get = MagicMock(return_value=_mock_response(200, PAPER_FIXTURE))

        paper = service.fetch_paper("204e3073870fae3d05bcbc2f6a8e263d08cafc29")

        assert len(paper["citations"]) == 1
        cit = paper["citations"][0]
        assert cit["paper_id"] == "cit-001"
        assert cit["title"] == "BERT: Pre-training of Deep Bidirectional Transformers"

    def test_raises_not_found_for_invalid_id(self, service):
        service.session.get = MagicMock(return_value=_mock_response(404))

        with pytest.raises(PaperNotFoundError):
            service.fetch_paper("definitely-not-a-real-id")

    @patch("backend.services.semantic_scholar.time.sleep")
    def test_raises_rate_limit_after_exhausting_retries(self, mock_sleep, service):
        service.session.get = MagicMock(return_value=_mock_response(429))

        with pytest.raises(RateLimitError):
            service.fetch_paper("some-id")

        # 3 attempts total, sleeps on first 2 (exponential: 2s, 4s)
        assert service.session.get.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)

    @patch("backend.services.semantic_scholar.time.sleep")
    def test_retries_on_rate_limit_then_succeeds(self, mock_sleep, service):
        service.session.get = MagicMock(side_effect=[
            _mock_response(429),
            _mock_response(200, PAPER_FIXTURE),
        ])

        paper = service.fetch_paper("204e3073870fae3d05bcbc2f6a8e263d08cafc29")

        assert paper["title"] == "Attention Is All You Need"
        assert service.session.get.call_count == 2
        mock_sleep.assert_called_once_with(2)


# ---------------------------------------------------------------------------
# search_paper
# ---------------------------------------------------------------------------

class TestSearchPaper:
    def test_returns_normalized_list_of_results(self, service):
        response_data = {"data": [PAPER_FIXTURE], "total": 1}
        service.session.get = MagicMock(return_value=_mock_response(200, response_data))

        results = service.search_paper("Attention Is All You Need")

        assert len(results) == 1
        assert results[0]["title"] == "Attention Is All You Need"
        assert results[0]["authors"] == ["Ashish Vaswani", "Noam Shazeer"]

    def test_returns_empty_list_when_no_results(self, service):
        service.session.get = MagicMock(return_value=_mock_response(200, {"data": []}))

        results = service.search_paper("xyznonexistentpaper99999")

        assert results == []

    @patch("backend.services.semantic_scholar.time.sleep")
    def test_raises_rate_limit_after_exhausting_retries(self, mock_sleep, service):
        service.session.get = MagicMock(return_value=_mock_response(429))

        with pytest.raises(RateLimitError):
            service.search_paper("some query")

        assert service.session.get.call_count == 3
