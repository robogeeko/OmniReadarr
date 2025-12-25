from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import httpx
import pytest

from indexers.models import ProwlarrConfiguration
from indexers.prowlarr.client import ProwlarrClient, ProwlarrClientError
from indexers.prowlarr.results import SearchResult


@pytest.fixture
def prowlarr_config(db):
    return ProwlarrConfiguration.objects.create(
        name="Test Prowlarr",
        host="localhost",
        port=9696,
        api_key="test-api-key",
        use_ssl=False,
        timeout=30,
    )


@pytest.fixture
def client(prowlarr_config):
    return ProwlarrClient(prowlarr_config)


class TestProwlarrClientInit:
    def test_init_with_config(self, prowlarr_config):
        client = ProwlarrClient(prowlarr_config)
        assert client.config == prowlarr_config
        assert client.base_url == "http://localhost:9696"
        assert client.headers == {"X-Api-Key": "test-api-key"}

    def test_init_without_config_uses_enabled(self, db):
        config = ProwlarrConfiguration.objects.create(
            name="Enabled Config",
            host="prowlarr.example.com",
            port=9696,
            api_key="key",
            enabled=True,
        )
        client = ProwlarrClient()
        assert client.config == config

    def test_init_without_config_no_enabled(self, db):
        ProwlarrConfiguration.objects.create(
            name="Disabled Config",
            host="prowlarr.example.com",
            port=9696,
            api_key="key",
            enabled=False,
        )
        with pytest.raises(ProwlarrClientError, match="No enabled Prowlarr configuration"):
            ProwlarrClient()

    def test_build_base_url_with_ssl(self, prowlarr_config):
        prowlarr_config.use_ssl = True
        prowlarr_config.save()
        client = ProwlarrClient(prowlarr_config)
        assert client.base_url == "https://localhost:9696"

    def test_build_base_url_with_base_path(self, prowlarr_config):
        prowlarr_config.base_path = "/prowlarr"
        prowlarr_config.save()
        client = ProwlarrClient(prowlarr_config)
        assert client.base_url == "http://localhost:9696/prowlarr"

    def test_build_base_url_with_base_path_trailing_slash(self, prowlarr_config):
        prowlarr_config.base_path = "/prowlarr/"
        prowlarr_config.save()
        client = ProwlarrClient(prowlarr_config)
        assert client.base_url == "http://localhost:9696/prowlarr"


class TestProwlarrClientTestConnection:
    @patch("httpx.get")
    def test_test_connection_success(self, mock_get, client):
        mock_response = httpx.Response(200, json={"version": "1.0.0"})
        mock_response._request = None
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response

        result = client.test_connection()

        assert result is True
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "http://localhost:9696/api/v1/system/status"
        assert call_args[1]["headers"] == {"X-Api-Key": "test-api-key"}
        assert call_args[1]["timeout"] == 30

    @patch("httpx.get")
    def test_test_connection_failure(self, mock_get, client):
        mock_get.side_effect = httpx.HTTPStatusError("Error", request=None, response=None)

        result = client.test_connection()

        assert result is False

    @patch("httpx.get")
    def test_test_connection_timeout(self, mock_get, client):
        mock_get.side_effect = httpx.TimeoutException("Timeout")

        result = client.test_connection()

        assert result is False


class TestProwlarrClientSearch:
    @patch("httpx.get")
    def test_search_success(self, mock_get, client):
        mock_response = httpx.Response(
            200,
            json=[
                {
                    "guid": "guid-123",
                    "title": "Test Book",
                    "indexer": "TestIndexer",
                    "indexerId": 1,
                    "size": 1024000,
                    "publishDate": "2020-01-15T00:00:00Z",
                    "seeders": 10,
                    "peers": 15,
                    "protocol": "torrent",
                    "downloadUrl": "magnet:?xt=urn:btih:...",
                    "infoUrl": "https://example.com",
                }
            ],
        )
        mock_response._request = None
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response

        results = client.search("test query")

        assert len(results) == 1
        assert results[0].guid == "guid-123"
        assert results[0].title == "Test Book"
        assert results[0].indexer == "TestIndexer"
        assert results[0].indexer_id == 1
        assert results[0].size == 1024000
        assert results[0].seeders == 10
        assert results[0].peers == 15
        assert results[0].protocol == "torrent"
        assert results[0].download_url == "magnet:?xt=urn:btih:..."
        assert results[0].info_url == "https://example.com"

        call_args = mock_get.call_args
        assert call_args[0][0] == "http://localhost:9696/api/v1/search"
        assert call_args[1]["params"]["q"] == "test query"
        assert call_args[1]["params"]["limit"] == 50

    @patch("httpx.get")
    def test_search_with_all_params(self, mock_get, client):
        mock_response = httpx.Response(200, json=[])
        mock_response._request = None
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response

        client.search(
            query="test",
            category=7000,
            indexer="TestIndexer",
            limit=25,
            offset=10,
            sort_key="seeders",
            sort_dir="asc",
        )

        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert params["q"] == "test"
        assert params["cat"] == 7000
        assert params["indexer"] == "TestIndexer"
        assert params["limit"] == 25
        assert params["offset"] == 10
        assert params["sortkey"] == "seeders"
        assert params["sortdir"] == "asc"

    @patch("httpx.get")
    def test_search_without_category(self, mock_get, client):
        mock_response = httpx.Response(200, json=[])
        mock_response._request = None
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response

        client.search(query="test", category=None)

        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert "cat" not in params

    @patch("httpx.get")
    def test_search_handles_invalid_results(self, mock_get, client):
        mock_response = httpx.Response(
            200,
            json=[
                {"guid": "valid", "title": "Valid", "indexer": "Test", "indexerId": 1},
                {"invalid": "data"},
            ],
        )
        mock_response._request = None
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response

        results = client.search("test")

        assert len(results) == 1
        assert results[0].guid == "valid"

    @patch("httpx.get")
    def test_search_authentication_error(self, mock_get, client):
        mock_response = httpx.Response(401, text="Unauthorized")
        mock_get.side_effect = httpx.HTTPStatusError("Unauthorized", request=None, response=mock_response)

        with pytest.raises(ProwlarrClientError, match="Authentication failed"):
            client.search("test")

    @patch("httpx.get")
    def test_search_timeout(self, mock_get, client):
        mock_get.side_effect = httpx.TimeoutException("Timeout")

        with pytest.raises(ProwlarrClientError, match="Request timeout"):
            client.search("test")

    @patch("httpx.get")
    def test_search_http_error(self, mock_get, client):
        mock_response = httpx.Response(500, text="Internal Server Error")
        mock_get.side_effect = httpx.HTTPStatusError("Error", request=None, response=mock_response)

        with pytest.raises(ProwlarrClientError, match="HTTP error 500"):
            client.search("test")


class TestProwlarrClientGetIndexers:
    @patch("httpx.get")
    def test_get_indexers_success(self, mock_get, client):
        mock_response = httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "name": "TestIndexer",
                    "protocol": "torrent",
                    "supportsRss": True,
                    "supportsSearch": True,
                    "supportsQuery": True,
                    "supportsBookSearch": False,
                    "categories": [7000, 7010],
                    "enabled": True,
                }
            ],
        )
        mock_response._request = None
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response

        indexers = client.get_indexers()

        assert len(indexers) == 1
        assert indexers[0].id == 1
        assert indexers[0].name == "TestIndexer"
        assert indexers[0].protocol == "torrent"
        assert indexers[0].capabilities.supports_rss is True
        assert indexers[0].capabilities.supports_search is True
        assert indexers[0].capabilities.supports_query is True
        assert indexers[0].capabilities.supports_book_search is False
        assert indexers[0].capabilities.categories == [7000, 7010]
        assert indexers[0].enabled is True

    @patch("httpx.get")
    def test_get_indexers_handles_invalid_data(self, mock_get, client):
        mock_response = httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "name": "Valid",
                    "protocol": "torrent",
                    "supportsRss": True,
                    "supportsSearch": True,
                    "supportsQuery": True,
                    "supportsBookSearch": False,
                    "categories": [],
                },
                {"invalid": "data"},
            ],
        )
        mock_response._request = None
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response

        indexers = client.get_indexers()

        assert len(indexers) == 1
        assert indexers[0].name == "Valid"

    @patch("httpx.get")
    def test_get_indexers_authentication_error(self, mock_get, client):
        mock_response = httpx.Response(401, text="Unauthorized")
        mock_get.side_effect = httpx.HTTPStatusError("Unauthorized", request=None, response=mock_response)

        with pytest.raises(ProwlarrClientError, match="Authentication failed"):
            client.get_indexers()


class TestProwlarrClientGetIndexerCapabilities:
    @patch("httpx.get")
    def test_get_indexer_capabilities_found(self, mock_get, client):
        mock_response = httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "name": "Indexer1",
                    "protocol": "torrent",
                    "supportsRss": True,
                    "supportsSearch": True,
                    "supportsQuery": True,
                    "supportsBookSearch": False,
                    "categories": [],
                },
                {
                    "id": 2,
                    "name": "Indexer2",
                    "protocol": "usenet",
                    "supportsRss": True,
                    "supportsSearch": True,
                    "supportsQuery": True,
                    "supportsBookSearch": True,
                    "categories": [7000],
                },
            ],
        )
        mock_response._request = None
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response

        indexer = client.get_indexer_capabilities(2)

        assert indexer is not None
        assert indexer.id == 2
        assert indexer.name == "Indexer2"

    @patch("httpx.get")
    def test_get_indexer_capabilities_not_found(self, mock_get, client):
        mock_response = httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "name": "Indexer1",
                    "protocol": "torrent",
                    "supportsRss": True,
                    "supportsSearch": True,
                    "supportsQuery": True,
                    "supportsBookSearch": False,
                    "categories": [],
                }
            ],
        )
        mock_response._request = None
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response

        indexer = client.get_indexer_capabilities(999)

        assert indexer is None


class TestSearchResult:
    def test_from_dict_complete(self):
        data = {
            "guid": "guid-123",
            "title": "Test Book",
            "indexer": "TestIndexer",
            "indexerId": 1,
            "size": 1024000,
            "publishDate": "2020-01-15T00:00:00Z",
            "seeders": 10,
            "peers": 15,
            "protocol": "torrent",
            "downloadUrl": "magnet:?xt=urn:btih:...",
            "infoUrl": "https://example.com",
        }

        result = SearchResult.from_dict(data)

        assert result.guid == "guid-123"
        assert result.title == "Test Book"
        assert result.indexer == "TestIndexer"
        assert result.indexer_id == 1
        assert result.size == 1024000
        assert isinstance(result.publish_date, datetime)
        assert result.seeders == 10
        assert result.peers == 15
        assert result.protocol == "torrent"
        assert result.download_url == "magnet:?xt=urn:btih:..."
        assert result.info_url == "https://example.com"

    def test_from_dict_minimal(self):
        data = {
            "guid": "guid-123",
            "title": "Test Book",
            "indexer": "TestIndexer",
            "indexerId": 1,
            "protocol": "usenet",
            "downloadUrl": "https://example.com/file.nzb",
        }

        result = SearchResult.from_dict(data)

        assert result.guid == "guid-123"
        assert result.size is None
        assert result.publish_date is None
        assert result.seeders is None
        assert result.peers is None
        assert result.info_url is None

    def test_from_dict_invalid_date(self):
        data = {
            "guid": "guid-123",
            "title": "Test Book",
            "indexer": "TestIndexer",
            "indexerId": 1,
            "publishDate": "invalid-date",
            "protocol": "torrent",
            "downloadUrl": "magnet:?xt=urn:btih:...",
        }

        result = SearchResult.from_dict(data)

        assert result.publish_date is None

