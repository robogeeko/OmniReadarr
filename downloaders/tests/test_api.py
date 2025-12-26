from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from downloaders.models import (
    BlacklistReason,
    ClientType,
    DownloadAttempt,
    DownloadAttemptStatus,
    DownloadClientConfiguration,
)
from downloaders.services.download import DownloadServiceError
from downloaders.services.search import SearchServiceError
from indexers.prowlarr.results import SearchResult
from media.models import Book


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def book(db):
    return Book.objects.create(
        title="Test Book",
        authors=["Test Author"],
        status="wanted",
    )


@pytest.fixture
def download_client_config(db):
    return DownloadClientConfiguration.objects.create(
        name="Test SABnzbd",
        client_type=ClientType.SABNZBD,
        host="localhost",
        port=8080,
        api_key="test-key",
        enabled=True,
    )


@pytest.fixture
def search_result():
    return SearchResult(
        guid="test-guid-123",
        title="Test Book Release",
        indexer="TestIndexer",
        indexer_id=1,
        size=1024000,
        publish_date=None,
        seeders=10,
        peers=15,
        protocol="torrent",
        download_url="magnet:test",
    )


@pytest.mark.django_db
class TestSearchForMedia:
    def test_search_for_media_success(self, client, book):
        with patch("downloaders.api.SearchService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            result = SearchResult(
                guid="guid-1",
                title="Result 1",
                indexer="Indexer1",
                indexer_id=1,
                size=1000,
                publish_date=None,
                seeders=10,
                peers=15,
                protocol="torrent",
                download_url="magnet:test1",
            )
            mock_service.search_for_media.return_value = [result]

            response = client.post(
                f"/api/downloads/search/{book.id}/",
                content_type="application/json",
            )

            assert response.status_code == 200
            data = json.loads(response.content)
            assert "results" in data
            assert "total" in data
            assert len(data["results"]) == 1
            assert data["results"][0]["guid"] == "guid-1"

    def test_search_for_media_not_found(self, client):
        fake_id = uuid4()
        response = client.post(
            f"/api/downloads/search/{fake_id}/",
            content_type="application/json",
        )

        assert response.status_code == 404
        data = json.loads(response.content)
        assert "error" in data

    def test_search_for_media_invalid_id(self, client):
        response = client.post(
            "/api/downloads/search/invalid-id/",
            content_type="application/json",
        )

        assert response.status_code == 404

    def test_search_for_media_service_error(self, client, book):
        with patch("downloaders.api.SearchService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.search_for_media.side_effect = SearchServiceError(
                "Search failed"
            )

            response = client.post(
                f"/api/downloads/search/{book.id}/",
                content_type="application/json",
            )

            assert response.status_code == 500
            data = json.loads(response.content)
            assert "error" in data


@pytest.mark.django_db
class TestInitiateDownload:
    def test_initiate_download_success(
        self, client, book, download_client_config, search_result
    ):
        with (
            patch("downloaders.api.SearchService") as mock_search_service_class,
            patch("downloaders.api.DownloadService") as mock_download_service_class,
        ):
            mock_search_service = MagicMock()
            mock_search_service_class.return_value = mock_search_service
            mock_search_service.search_for_media.return_value = [search_result]

            mock_download_service = MagicMock()
            mock_download_service_class.return_value = mock_download_service

            content_type = ContentType.objects.get_for_model(book)
            attempt = DownloadAttempt.objects.create(
                content_type=content_type,
                object_id=book.id,
                indexer="TestIndexer",
                indexer_id="1",
                release_title="Test Release",
                download_url="magnet:test",
                status=DownloadAttemptStatus.SENT,
                download_client=download_client_config,
            )

            mock_download_service.initiate_download.return_value = attempt

            response = client.post(
                "/api/downloads/initiate/",
                json.dumps(
                    {
                        "media_id": str(book.id),
                        "indexer_id": 1,
                        "guid": "test-guid-123",
                    }
                ),
                content_type="application/json",
            )

            assert response.status_code == 200
            data = json.loads(response.content)
            assert data["success"] is True
            assert "attempt_id" in data

    def test_initiate_download_missing_fields(self, client):
        response = client.post(
            "/api/downloads/initiate/",
            json.dumps({}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data

    def test_initiate_download_media_not_found(self, client):
        fake_id = uuid4()
        response = client.post(
            "/api/downloads/initiate/",
            json.dumps(
                {
                    "media_id": str(fake_id),
                    "indexer_id": 1,
                    "guid": "test-guid",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 404
        data = json.loads(response.content)
        assert "error" in data

    def test_initiate_download_service_error(self, client, book, search_result):
        with (
            patch("downloaders.api.SearchService") as mock_search_service_class,
            patch("downloaders.api.DownloadService") as mock_download_service_class,
        ):
            mock_search_service = MagicMock()
            mock_search_service_class.return_value = mock_search_service
            mock_search_service.search_for_media.return_value = [search_result]

            mock_download_service = MagicMock()
            mock_download_service_class.return_value = mock_download_service
            mock_download_service.initiate_download.side_effect = DownloadServiceError(
                "Active download exists"
            )

            response = client.post(
                "/api/downloads/initiate/",
                json.dumps(
                    {
                        "media_id": str(book.id),
                        "indexer_id": 1,
                        "guid": "test-guid-123",
                    }
                ),
                content_type="application/json",
            )

            assert response.status_code == 400
            data = json.loads(response.content)
            assert data["success"] is False
            assert "error" in data


@pytest.mark.django_db
class TestGetDownloadAttempts:
    def test_get_download_attempts_success(self, client, book, download_client_config):
        content_type = ContentType.objects.get_for_model(book)
        DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="Indexer1",
            indexer_id="1",
            release_title="Release 1",
            download_url="magnet:test1",
            status=DownloadAttemptStatus.DOWNLOADED,
            download_client=download_client_config,
        )
        DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="Indexer2",
            indexer_id="2",
            release_title="Release 2",
            download_url="magnet:test2",
            status=DownloadAttemptStatus.FAILED,
            download_client=download_client_config,
        )

        response = client.get(f"/api/downloads/attempts/{book.id}/")

        assert response.status_code == 200
        data = json.loads(response.content)
        assert "attempts" in data
        assert len(data["attempts"]) == 2

    def test_get_download_attempts_not_found(self, client):
        fake_id = uuid4()
        response = client.get(f"/api/downloads/attempts/{fake_id}/")

        assert response.status_code == 404
        data = json.loads(response.content)
        assert "error" in data


@pytest.mark.django_db
class TestGetDownloadStatus:
    def test_get_download_status_success(self, client, book, download_client_config):
        content_type = ContentType.objects.get_for_model(book)
        attempt = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="1",
            release_title="Test Release",
            download_url="magnet:test",
            status=DownloadAttemptStatus.DOWNLOADING,
            download_client=download_client_config,
            download_client_download_id="sabnzbd-123",
        )

        with patch("downloaders.api.DownloadService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.get_download_status.return_value = attempt

            with patch(
                "downloaders.clients.sabnzbd.SABnzbdClient"
            ) as mock_sabnzbd_class:
                mock_sabnzbd = MagicMock()
                mock_sabnzbd_class.return_value = mock_sabnzbd
                mock_job_status = MagicMock()
                mock_job_status.progress = 50.0
                mock_sabnzbd.get_job_status.return_value = mock_job_status

                response = client.get(f"/api/downloads/attempt/{attempt.id}/status/")

                assert response.status_code == 200
                data = json.loads(response.content)
                assert "status" in data
                assert "progress" in data
                assert data["progress"] == 50.0

    def test_get_download_status_not_found(self, client):
        fake_id = uuid4()
        response = client.get(f"/api/downloads/attempt/{fake_id}/status/")

        assert response.status_code in [404, 500]
        data = json.loads(response.content)
        assert "error" in data
        if response.status_code == 500:
            assert (
                "not found" in data["error"].lower()
                or "Status check failed" in data["error"]
            )


@pytest.mark.django_db
class TestBlacklistRelease:
    def test_blacklist_release_success(self, client, book, download_client_config):
        content_type = ContentType.objects.get_for_model(book)
        attempt = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="1",
            release_title="Test Release",
            download_url="magnet:test",
            status=DownloadAttemptStatus.FAILED,
            download_client=download_client_config,
        )

        with patch("downloaders.api.DownloadService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            response = client.post(
                "/api/downloads/blacklist/",
                json.dumps(
                    {
                        "attempt_id": str(attempt.id),
                        "reason": BlacklistReason.FAILED_DOWNLOAD,
                    }
                ),
                content_type="application/json",
            )

            assert response.status_code == 200
            data = json.loads(response.content)
            assert data["success"] is True

    def test_blacklist_release_missing_fields(self, client):
        response = client.post(
            "/api/downloads/blacklist/",
            json.dumps({}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data

    def test_blacklist_release_invalid_reason(
        self, client, book, download_client_config
    ):
        content_type = ContentType.objects.get_for_model(book)
        attempt = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="1",
            release_title="Test Release",
            download_url="magnet:test",
            status=DownloadAttemptStatus.FAILED,
            download_client=download_client_config,
        )

        response = client.post(
            "/api/downloads/blacklist/",
            json.dumps(
                {
                    "attempt_id": str(attempt.id),
                    "reason": "invalid_reason",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data


@pytest.mark.django_db
class TestDeleteDownloadAttempt:
    def test_delete_download_attempt_success(
        self, client, book, download_client_config
    ):
        content_type = ContentType.objects.get_for_model(book)
        attempt = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="1",
            release_title="Test Release",
            download_url="magnet:test",
            status=DownloadAttemptStatus.DOWNLOADED,
            download_client=download_client_config,
        )

        with patch("downloaders.api.DownloadService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.delete_download_attempt.return_value = {
                "success": True,
                "messages": ["Download attempt deleted"],
            }

            response = client.delete(f"/api/downloads/attempt/{attempt.id}/")

            assert response.status_code == 200
            data = json.loads(response.content)
            assert data["success"] is True
            assert "message" in data

    def test_delete_download_attempt_not_found(self, client):
        fake_id = uuid4()
        response = client.delete(f"/api/downloads/attempt/{fake_id}/")

        assert response.status_code in [404, 500]
        data = json.loads(response.content)
        assert "error" in data or "success" in data
