from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.contenttypes.models import ContentType

from downloaders.models import DownloadBlacklist
from downloaders.services.search import SearchService
from indexers.prowlarr.client import ProwlarrClient, ProwlarrClientError
from indexers.prowlarr.results import SearchResult
from media.models import Audiobook, Book


@pytest.fixture
def book(db):
    return Book.objects.create(
        title="Test Book",
        authors=["Test Author"],
        status="wanted",
    )


@pytest.fixture
def book_with_isbn(db):
    return Book.objects.create(
        title="Test Book",
        authors=["Test Author"],
        isbn="1234567890",
        isbn13="9781234567890",
        status="wanted",
    )


@pytest.fixture
def audiobook(db):
    return Audiobook.objects.create(
        title="Test Audiobook",
        authors=["Test Author"],
        status="wanted",
    )


@pytest.fixture
def mock_prowlarr_client():
    client = MagicMock(spec=ProwlarrClient)
    return client


@pytest.fixture
def search_service(mock_prowlarr_client):
    return SearchService(prowlarr_client=mock_prowlarr_client)


class TestSearchServiceInit:
    def test_init_with_client(self, mock_prowlarr_client):
        service = SearchService(prowlarr_client=mock_prowlarr_client)
        assert service.prowlarr_client == mock_prowlarr_client

    def test_init_without_client(self):
        with patch("downloaders.services.search.ProwlarrClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            service = SearchService()
            assert service.prowlarr_client == mock_client


class TestSearchServiceGetCategory:
    def test_get_category_for_book(self, search_service, book):
        category = search_service._get_category_for_media(book)
        assert category == 7020

    def test_get_category_for_audiobook(self, search_service, audiobook):
        category = search_service._get_category_for_media(audiobook)
        assert category == 3030

    def test_get_category_for_invalid_media_type(self, search_service):
        class InvalidMedia:
            pass

        invalid_media = InvalidMedia()
        with pytest.raises(Exception, match="Invalid media type"):
            search_service._get_category_for_media(invalid_media)


class TestSearchServiceBuildQueries:
    def test_build_queries_with_title_and_author(self, search_service, book):
        queries = search_service._build_search_queries(book)

        assert len(queries) >= 2
        assert any("Test Book" in q[0] and "Test Author" in q[0] for q in queries)
        assert any(q[0] == "Test Book" for q in queries)

    def test_build_queries_with_isbn(self, search_service, book_with_isbn):
        queries = search_service._build_search_queries(book_with_isbn)

        isbn_queries = [q for q in queries if q[1] == 0]
        assert len(isbn_queries) == 2
        assert any(q[0] == "1234567890" for q in isbn_queries)
        assert any(q[0] == "9781234567890" for q in isbn_queries)

    def test_build_queries_title_only(self, search_service):
        book = Book(title="Test Book", authors=[])
        queries = search_service._build_search_queries(book)

        assert len(queries) == 1
        assert queries[0][0] == "Test Book"
        assert queries[0][1] == 3


class TestSearchServiceDeduplicate:
    def test_deduplicate_results(self, search_service):
        result1 = SearchResult(
            guid="guid-1",
            title="Book 1",
            indexer="Indexer1",
            indexer_id=1,
            size=1000,
            publish_date=None,
            seeders=10,
            peers=15,
            protocol="torrent",
            download_url="magnet:test1",
        )
        result2 = SearchResult(
            guid="guid-1",
            title="Book 1",
            indexer="Indexer2",
            indexer_id=2,
            size=1000,
            publish_date=None,
            seeders=10,
            peers=15,
            protocol="torrent",
            download_url="magnet:test1",
        )
        result3 = SearchResult(
            guid="guid-2",
            title="Book 2",
            indexer="Indexer1",
            indexer_id=1,
            size=1000,
            publish_date=None,
            seeders=10,
            peers=15,
            protocol="torrent",
            download_url="magnet:test2",
        )

        results = [(result1, 1), (result2, 1), (result3, 2)]
        deduplicated = search_service._deduplicate_results(results)

        assert len(deduplicated) == 2
        assert deduplicated[0][0].guid == "guid-1"
        assert deduplicated[1][0].guid == "guid-2"


class TestSearchServiceFilterBlacklisted:
    def test_filter_blacklisted(self, search_service, book):
        result = SearchResult(
            guid="guid-1",
            title="Book 1",
            indexer="Indexer1",
            indexer_id=1,
            size=1000,
            publish_date=None,
            seeders=10,
            peers=15,
            protocol="torrent",
            download_url="magnet:test1",
        )

        content_type = ContentType.objects.get_for_model(book)
        DownloadBlacklist.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="Indexer1",
            indexer_id="1",
            release_title="Book 1",
            download_url="magnet:test1",
            reason="failed_download",
        )

        results = [(result, 1)]
        filtered = search_service._filter_blacklisted(book, results)

        assert len(filtered) == 0

    def test_filter_not_blacklisted(self, search_service, book):
        result = SearchResult(
            guid="guid-1",
            title="Book 1",
            indexer="Indexer1",
            indexer_id=1,
            size=1000,
            publish_date=None,
            seeders=10,
            peers=15,
            protocol="torrent",
            download_url="magnet:test1",
        )

        results = [(result, 1)]
        filtered = search_service._filter_blacklisted(book, results)

        assert len(filtered) == 1


class TestSearchServiceIsBlacklisted:
    def test_is_blacklisted_true(self, search_service, book):
        result = SearchResult(
            guid="guid-1",
            title="Book 1",
            indexer="Indexer1",
            indexer_id=1,
            size=1000,
            publish_date=None,
            seeders=10,
            peers=15,
            protocol="torrent",
            download_url="magnet:test1",
        )

        content_type = ContentType.objects.get_for_model(book)
        DownloadBlacklist.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="Indexer1",
            indexer_id="1",
            release_title="Book 1",
            download_url="magnet:test1",
            reason="failed_download",
        )

        assert search_service.is_blacklisted(book, result) is True

    def test_is_blacklisted_false(self, search_service, book):
        result = SearchResult(
            guid="guid-1",
            title="Book 1",
            indexer="Indexer1",
            indexer_id=1,
            size=1000,
            publish_date=None,
            seeders=10,
            peers=15,
            protocol="torrent",
            download_url="magnet:test1",
        )

        assert search_service.is_blacklisted(book, result) is False


class TestSearchServiceSortResults:
    def test_sort_results(self, search_service):
        result1 = SearchResult(
            guid="guid-1",
            title="Book A",
            indexer="Indexer2",
            indexer_id=2,
            size=1000,
            publish_date=None,
            seeders=10,
            peers=15,
            protocol="torrent",
            download_url="magnet:test1",
        )
        result2 = SearchResult(
            guid="guid-2",
            title="Book B",
            indexer="Indexer1",
            indexer_id=1,
            size=1000,
            publish_date=None,
            seeders=10,
            peers=15,
            protocol="torrent",
            download_url="magnet:test2",
        )

        results = [(result1, 2), (result2, 1)]
        sorted_results = search_service._sort_results(results)

        assert len(sorted_results) == 2
        assert sorted_results[0].guid == "guid-2"
        assert sorted_results[1].guid == "guid-1"


class TestSearchServiceSearchForMedia:
    @patch("downloaders.services.search.ProwlarrClient")
    def test_search_for_media_success(self, mock_client_class, book):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        result1 = SearchResult(
            guid="guid-1",
            title="Test Book",
            indexer="Indexer1",
            indexer_id=1,
            size=1000,
            publish_date=None,
            seeders=10,
            peers=15,
            protocol="torrent",
            download_url="magnet:test1",
        )
        result2 = SearchResult(
            guid="guid-2",
            title="Test Book",
            indexer="Indexer2",
            indexer_id=2,
            size=1000,
            publish_date=None,
            seeders=10,
            peers=15,
            protocol="torrent",
            download_url="magnet:test2",
        )

        mock_client.search.return_value = [result1, result2]

        service = SearchService()
        results = service.search_for_media(book)

        assert len(results) > 0
        assert mock_client.search.called
        mock_client.search.assert_called_with(
            query="Test Book",
            category=7020,
            limit=50,
        )

    @patch("downloaders.services.search.ProwlarrClient")
    def test_search_for_media_uses_correct_category_for_book(self, mock_client_class, book):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.search.return_value = []

        service = SearchService()
        service.search_for_media(book)

        mock_client.search.assert_called_with(
            query="Test Book",
            category=7020,
            limit=50,
        )

    @patch("downloaders.services.search.ProwlarrClient")
    def test_search_for_media_uses_correct_category_for_audiobook(self, mock_client_class, audiobook):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.search.return_value = []

        service = SearchService()
        service.search_for_media(audiobook)

        mock_client.search.assert_called_with(
            query="Test Audiobook",
            category=3030,
            limit=50,
        )

    @patch("downloaders.services.search.ProwlarrClient")
    def test_search_for_media_limits_to_50(self, mock_client_class, book):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        results_list = []
        for i in range(60):
            results_list.append(
                SearchResult(
                    guid=f"guid-{i}",
                    title=f"Book {i}",
                    indexer="Indexer1",
                    indexer_id=1,
                    size=1000,
                    publish_date=None,
                    seeders=10,
                    peers=15,
                    protocol="torrent",
                    download_url=f"magnet:test{i}",
                )
            )

        mock_client.search.return_value = results_list

        service = SearchService()
        results = service.search_for_media(book)

        assert len(results) <= 50

    @patch("downloaders.services.search.ProwlarrClient")
    def test_search_for_media_handles_errors(self, mock_client_class, book):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.search.side_effect = ProwlarrClientError("Search failed")

        service = SearchService()
        results = service.search_for_media(book)

        assert len(results) == 0

