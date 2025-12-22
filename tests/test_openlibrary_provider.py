from __future__ import annotations

from datetime import date
from unittest.mock import Mock, patch

import httpx
import pytest

from search.providers.openlibrary import OpenLibraryProvider
from search.providers.results import BookMetadata


@pytest.fixture
def provider_config() -> dict:
    return {
        "api_key": "",
        "base_url": "https://openlibrary.org",
        "enabled": True,
        "rate_limit_per_minute": 60,
    }


@pytest.fixture
def provider(provider_config: dict) -> OpenLibraryProvider:
    return OpenLibraryProvider(provider_config)


@pytest.fixture
def mock_search_response() -> dict:
    return {
        "numFound": 2,
        "docs": [
            {
                "key": "/works/OL123456W",
                "title": "Dune",
                "author_name": ["Frank Herbert"],
                "isbn": ["0441013597", "9780441013593"],
                "first_publish_year": 1965,
                "cover_i": 12345,
                "number_of_pages_median": 688,
                "publisher": ["Ace Books"],
                "language": ["eng"],
                "first_sentence": [
                    "A beginning is the time for taking the most delicate care."
                ],
                "subject": ["Science fiction", "Fiction"],
            },
            {
                "key": "/works/OL789012W",
                "title": "Test Book",
                "author_name": ["Test Author"],
                "isbn": ["1234567890"],
                "first_publish_year": 2020,
            },
        ],
    }


@pytest.fixture
def mock_work_response() -> dict:
    return {
        "key": "/works/OL123456W",
        "title": "Dune",
        "authors": [{"name": "Frank Herbert"}],
        "isbn": ["0441013597", "9780441013593"],
        "first_publish_year": 1965,
        "cover_i": 12345,
        "number_of_pages": 688,
        "publisher": ["Ace Books"],
        "language": ["eng"],
        "first_sentence": [
            "A beginning is the time for taking the most delicate care."
        ],
        "subject": ["Science fiction", "Fiction"],
    }


class TestOpenLibraryProviderSearch:
    def test_search_returns_results(
        self, provider: OpenLibraryProvider, mock_search_response: dict
    ):
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_search_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            results = provider.search("dune", "book")

            assert len(results) == 2
            assert all(isinstance(r, BookMetadata) for r in results)
            assert results[0].title == "Dune"
            assert results[0].authors == ["Frank Herbert"]

    def test_search_filters_invalid_results(self, provider: OpenLibraryProvider):
        invalid_response = {
            "numFound": 1,
            "docs": [
                {"key": "/works/OL123", "title": ""},
            ],
        }

        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = invalid_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            results = provider.search("test", "book")

            assert len(results) == 0

    def test_search_handles_http_error(self, provider: OpenLibraryProvider):
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection error")

            results = provider.search("dune", "book")

            assert len(results) == 0

    def test_search_filters_unsupported_media_types(
        self, provider: OpenLibraryProvider
    ):
        results = provider.search("test", "manga")
        assert len(results) == 0

        results = provider.search("test", "comic")
        assert len(results) == 0


class TestOpenLibraryProviderFetchByIdentifier:
    def test_fetch_by_openlibrary_id(
        self, provider: OpenLibraryProvider, mock_work_response: dict
    ):
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_work_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = provider.fetch_by_identifier("OL123456W", "openlibrary_id")

            assert result is not None
            assert isinstance(result, BookMetadata)
            assert result.title == "Dune"
            assert result.provider_id == "OL123456W"

    def test_fetch_by_isbn(
        self, provider: OpenLibraryProvider, mock_search_response: dict
    ):
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_search_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = provider.fetch_by_identifier("0441013597", "isbn")

            assert result is not None
            assert isinstance(result, BookMetadata)
            assert result.title == "Dune"

    def test_fetch_by_isbn13(
        self, provider: OpenLibraryProvider, mock_search_response: dict
    ):
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_search_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = provider.fetch_by_identifier("9780441013593", "isbn13")

            assert result is not None
            assert isinstance(result, BookMetadata)

    def test_fetch_by_identifier_handles_http_error(
        self, provider: OpenLibraryProvider
    ):
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection error")

            result = provider.fetch_by_identifier("OL123456W", "openlibrary_id")

            assert result is None

    def test_fetch_by_unsupported_identifier_type(self, provider: OpenLibraryProvider):
        result = provider.fetch_by_identifier("test", "unknown_type")
        assert result is None


class TestOpenLibraryProviderNormalizeResult:
    def test_normalize_result_with_author_name(self, provider: OpenLibraryProvider):
        raw_result = {
            "key": "/works/OL123456W",
            "title": "Dune",
            "author_name": ["Frank Herbert"],
            "isbn": ["0441013597", "9780441013593"],
            "first_publish_year": 1965,
            "cover_i": 12345,
            "number_of_pages_median": 688,
            "publisher": ["Ace Books"],
            "language": ["eng"],
            "first_sentence": [
                "A beginning is the time for taking the most delicate care."
            ],
            "subject": ["Science fiction", "Fiction"],
        }

        result = provider.normalize_result(raw_result)

        assert result is not None
        assert isinstance(result, BookMetadata)
        assert result.provider == "openlibrary"
        assert result.provider_id == "OL123456W"
        assert result.title == "Dune"
        assert result.authors == ["Frank Herbert"]
        assert result.isbn == "0441013597"
        assert result.isbn13 == "9780441013593"
        assert result.publication_date == date(1965, 1, 1)
        assert result.page_count == 688
        assert result.cover_url == "https://covers.openlibrary.org/b/id/12345-L.jpg"
        assert result.publisher == "Ace Books"
        assert result.language == "eng"
        assert (
            result.description
            == "A beginning is the time for taking the most delicate care."
        )
        assert result.genres == ["Science fiction", "Fiction"]

    def test_normalize_result_with_authors_list(self, provider: OpenLibraryProvider):
        raw_result = {
            "key": "/works/OL123456W",
            "title": "Test Book",
            "authors": [{"name": "Author One"}, {"name": "Author Two"}],
            "isbn": ["1234567890"],
        }

        result = provider.normalize_result(raw_result)

        assert result is not None
        assert result.authors == ["Author One", "Author Two"]

    def test_normalize_result_with_publish_date_string(
        self, provider: OpenLibraryProvider
    ):
        raw_result = {
            "key": "/works/OL123456W",
            "title": "Test Book",
            "publish_date": ["2020-01-15"],
        }

        result = provider.normalize_result(raw_result)

        assert result is not None
        assert result.publication_date == date(2020, 1, 1)

    def test_normalize_result_with_publish_date_int(
        self, provider: OpenLibraryProvider
    ):
        raw_result = {
            "key": "/works/OL123456W",
            "title": "Test Book",
            "first_publish_year": 2020,
        }

        result = provider.normalize_result(raw_result)

        assert result is not None
        assert result.publication_date == date(2020, 1, 1)

    def test_normalize_result_with_first_sentence_list(
        self, provider: OpenLibraryProvider
    ):
        raw_result = {
            "key": "/works/OL123456W",
            "title": "Test Book",
            "first_sentence": ["Sentence one.", "Sentence two."],
        }

        result = provider.normalize_result(raw_result)

        assert result is not None
        assert result.description == "Sentence one. Sentence two."

    def test_normalize_result_returns_none_for_missing_title(
        self, provider: OpenLibraryProvider
    ):
        raw_result = {
            "key": "/works/OL123456W",
            "title": "",
        }

        result = provider.normalize_result(raw_result)

        assert result is None

    def test_normalize_result_handles_missing_fields(
        self, provider: OpenLibraryProvider
    ):
        raw_result = {
            "key": "/works/OL123456W",
            "title": "Minimal Book",
        }

        result = provider.normalize_result(raw_result)

        assert result is not None
        assert result.title == "Minimal Book"
        assert result.authors == []
        assert result.isbn == ""
        assert result.isbn13 == ""
        assert result.publication_date is None
        assert result.page_count is None
        assert result.cover_url == ""
        assert result.publisher == ""
        assert result.language == ""
        assert result.description == ""
        assert result.genres == []

    def test_normalize_result_extracts_provider_id(self, provider: OpenLibraryProvider):
        raw_result = {
            "key": "/works/OL123456W",
            "title": "Test Book",
        }

        result = provider.normalize_result(raw_result)

        assert result is not None
        assert result.provider_id == "OL123456W"

        raw_result["key"] = "/books/OL789012M"
        result = provider.normalize_result(raw_result)
        assert result is not None
        assert result.provider_id == "OL789012M"


class TestOpenLibraryProviderTestConnection:
    def test_test_connection_success(self, provider: OpenLibraryProvider):
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = provider.test_connection()

            assert result is True

    def test_test_connection_failure(self, provider: OpenLibraryProvider):
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection error")

            result = provider.test_connection()

            assert result is False

    def test_test_connection_non_200_status(self, provider: OpenLibraryProvider):
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            result = provider.test_connection()

            assert result is False
