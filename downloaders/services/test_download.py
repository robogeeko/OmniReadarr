from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from django.contrib.contenttypes.models import ContentType

from core.models import MediaStatus
from downloaders.models import (
    BlacklistReason,
    ClientType,
    DownloadAttempt,
    DownloadAttemptStatus,
    DownloadBlacklist,
    DownloadClientConfiguration,
)
from downloaders.clients.sabnzbd import SABnzbdClientError
from downloaders.services.download import DownloadService, DownloadServiceError
from indexers.prowlarr.results import SearchResult
from media.models import Book


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
        protocol="usenet",
        download_url="https://example.com/file.nzb",
    )


@pytest.fixture
def mock_prowlarr_client():
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.get_download_url = MagicMock()
    return mock


@pytest.fixture
def download_service(mock_prowlarr_client):
    return DownloadService(prowlarr_client=mock_prowlarr_client)


class TestDownloadServiceInitiateDownload:
    def test_initiate_download_success(
        self, download_service, book, search_result, download_client_config
    ):
        download_service.prowlarr_client.get_download_url.return_value = (
            "https://nzbgeek.info/api?t=get&id=123&apikey=abc"
        )

        mock_sabnzbd_client = MagicMock()
        mock_sabnzbd_client.add_download.return_value = {
            "status": True,
            "nzo_id": "SABnzbd_nzo_abc123",
            "message": "Download added",
        }

        with patch.object(
            download_service, "sabnzbd_client_factory", return_value=mock_sabnzbd_client
        ):
            attempt = download_service.initiate_download(book, search_result)

        assert attempt.status == DownloadAttemptStatus.DOWNLOADING
        assert attempt.download_client_download_id == "SABnzbd_nzo_abc123"
        assert attempt.indexer == "TestIndexer"
        assert attempt.release_title == "Test Book Release"

        book.refresh_from_db()
        assert book.status == MediaStatus.DOWNLOADING

        download_service.prowlarr_client.get_download_url.assert_called_once_with(
            indexer_id=1, guid="test-guid-123"
        )
        mock_sabnzbd_client.add_download.assert_called_once_with(
            url="https://nzbgeek.info/api?t=get&id=123&apikey=abc", category="books"
        )

    def test_initiate_download_with_active_download(
        self, download_service, book, search_result, download_client_config
    ):
        content_type = ContentType.objects.get_for_model(book)
        DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="Existing",
            indexer_id="1",
            release_title="Existing Download",
            download_url="magnet:existing",
            status=DownloadAttemptStatus.DOWNLOADING,
            download_client=download_client_config,
        )

        with pytest.raises(
            DownloadServiceError, match="already has an active download"
        ):
            download_service.initiate_download(book, search_result)

    def test_initiate_download_no_client_config(
        self, download_service, book, search_result
    ):
        with pytest.raises(
            DownloadServiceError, match="No enabled SABnzbd configuration"
        ):
            download_service.initiate_download(book, search_result)

    def test_initiate_download_missing_url(
        self, download_service, book, download_client_config
    ):
        search_result_no_url = SearchResult(
            guid="test-guid-123",
            title="Test Book Release",
            indexer="TestIndexer",
            indexer_id=1,
            size=1024000,
            publish_date=None,
            seeders=10,
            peers=15,
            protocol="usenet",
            download_url="",
        )

        with pytest.raises(DownloadServiceError, match="Download URL is missing"):
            download_service.initiate_download(book, search_result_no_url)

    def test_initiate_download_torrent_protocol(
        self, download_service, book, download_client_config
    ):
        search_result_torrent = SearchResult(
            guid="test-guid-123",
            title="Test Book Release",
            indexer="TestIndexer",
            indexer_id=1,
            size=1024000,
            publish_date=None,
            seeders=10,
            peers=15,
            protocol="torrent",
            download_url="https://example.com/test.nzb",
        )

        with pytest.raises(
            DownloadServiceError, match="SABnzbd only supports Usenet downloads"
        ):
            download_service.initiate_download(book, search_result_torrent)

    def test_initiate_download_invalid_url_format(
        self, download_service, book, download_client_config
    ):
        search_result_invalid = SearchResult(
            guid="test-guid-123",
            title="Test Book Release",
            indexer="TestIndexer",
            indexer_id=1,
            size=1024000,
            publish_date=None,
            seeders=10,
            peers=15,
            protocol="usenet",
            download_url="invalid-url",
        )

        with pytest.raises(DownloadServiceError, match="Invalid download URL format"):
            download_service.initiate_download(book, search_result_invalid)

    def test_initiate_download_sabnzbd_error(
        self, download_service, book, search_result, download_client_config
    ):
        mock_sabnzbd_client = MagicMock()
        mock_sabnzbd_client.add_download.side_effect = SABnzbdClientError(
            "SABnzbd error"
        )

        with patch.object(
            download_service, "sabnzbd_client_factory", return_value=mock_sabnzbd_client
        ):
            with pytest.raises(
                DownloadServiceError, match="Failed to initiate download"
            ):
                download_service.initiate_download(book, search_result)

        attempt = DownloadAttempt.objects.filter(
            content_type=ContentType.objects.get_for_model(book),
            object_id=book.id,
        ).first()

        assert attempt is not None
        assert attempt.status == DownloadAttemptStatus.FAILED
        assert attempt.error_type == "sabnzbd_error"


class TestDownloadServiceGetDownloadStatus:
    def test_get_download_status_completed(
        self, download_service, book, download_client_config
    ):
        content_type = ContentType.objects.get_for_model(book)
        attempt = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="1",
            release_title="Test Release",
            download_url="https://example.com/test.nzb",
            status=DownloadAttemptStatus.DOWNLOADING,
            download_client=download_client_config,
            download_client_download_id="sabnzbd-123",
        )

        mock_sabnzbd_client = MagicMock()
        mock_job_status = MagicMock()
        mock_job_status.status = "Completed"
        mock_job_status.path = "/downloads/test/file.epub"
        mock_sabnzbd_client.get_job_status.return_value = mock_job_status

        with patch.object(
            download_service, "sabnzbd_client_factory", return_value=mock_sabnzbd_client
        ):
            result = download_service.get_download_status(attempt.id)

        assert result.status == DownloadAttemptStatus.DOWNLOADED
        assert result.raw_file_path == "/downloads/test/file.epub"

        book.refresh_from_db()
        assert book.status == MediaStatus.DOWNLOADED

    def test_get_download_status_downloading(
        self, download_service, book, download_client_config
    ):
        content_type = ContentType.objects.get_for_model(book)
        attempt = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="1",
            release_title="Test Release",
            download_url="https://example.com/test.nzb",
            status=DownloadAttemptStatus.SENT,
            download_client=download_client_config,
            download_client_download_id="sabnzbd-123",
        )

        mock_sabnzbd_client = MagicMock()
        mock_job_status = MagicMock()
        mock_job_status.status = "Downloading"
        mock_sabnzbd_client.get_job_status.return_value = mock_job_status

        with patch.object(
            download_service, "sabnzbd_client_factory", return_value=mock_sabnzbd_client
        ):
            result = download_service.get_download_status(attempt.id)

        assert result.status == DownloadAttemptStatus.DOWNLOADING

        book.refresh_from_db()
        assert book.status == MediaStatus.DOWNLOADING

    def test_get_download_status_not_found(
        self, download_service, book, download_client_config
    ):
        content_type = ContentType.objects.get_for_model(book)
        attempt = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="1",
            release_title="Test Release",
            download_url="https://example.com/test.nzb",
            status=DownloadAttemptStatus.DOWNLOADING,
            download_client=download_client_config,
            download_client_download_id="sabnzbd-123",
        )

        mock_sabnzbd_client = MagicMock()
        mock_sabnzbd_client.get_job_status.return_value = None

        with patch.object(
            download_service, "sabnzbd_client_factory", return_value=mock_sabnzbd_client
        ):
            result = download_service.get_download_status(attempt.id)

        assert result.status == DownloadAttemptStatus.FAILED
        assert result.error_type == "not_found"

    @pytest.mark.django_db
    def test_get_download_status_attempt_not_found(self, download_service):
        fake_id = uuid4()
        with pytest.raises(
            DownloadServiceError, match=f"Download attempt {fake_id} not found"
        ):
            download_service.get_download_status(fake_id)


class TestDownloadServiceMarkAsBlacklisted:
    def test_mark_as_blacklisted(self, download_service, book, download_client_config):
        content_type = ContentType.objects.get_for_model(book)
        attempt = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="1",
            release_title="Test Release",
            download_url="https://example.com/test.nzb",
            status=DownloadAttemptStatus.DOWNLOADING,
            download_client=download_client_config,
        )

        download_service.mark_as_blacklisted(
            attempt.id, reason=BlacklistReason.FAILED_DOWNLOAD
        )

        attempt.refresh_from_db()
        assert attempt.status == DownloadAttemptStatus.BLACKLISTED

        blacklist = DownloadBlacklist.objects.filter(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="1",
        ).first()

        assert blacklist is not None
        assert blacklist.reason == BlacklistReason.FAILED_DOWNLOAD

    @pytest.mark.django_db
    def test_mark_as_blacklisted_attempt_not_found(self, download_service):
        fake_id = uuid4()
        with pytest.raises(
            DownloadServiceError, match=f"Download attempt {fake_id} not found"
        ):
            download_service.mark_as_blacklisted(fake_id)


class TestDownloadServiceDeleteDownloadAttempt:
    def test_delete_download_attempt_with_active_download(
        self, download_service, book, download_client_config
    ):
        content_type = ContentType.objects.get_for_model(book)
        attempt = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="1",
            release_title="Test Release",
            download_url="https://example.com/test.nzb",
            status=DownloadAttemptStatus.DOWNLOADING,
            download_client=download_client_config,
            download_client_download_id="sabnzbd-123",
        )

        book.status = MediaStatus.DOWNLOADING
        book.save()

        mock_sabnzbd_client = MagicMock()
        mock_sabnzbd_client.delete_job.return_value = True

        with patch.object(
            download_service, "sabnzbd_client_factory", return_value=mock_sabnzbd_client
        ):
            result = download_service.delete_download_attempt(attempt.id)

        assert result["success"] is True
        assert "Download removed from SABnzbd" in result["messages"]
        assert "Media status reset to WANTED" in result["messages"]

        assert not DownloadAttempt.objects.filter(id=attempt.id).exists()

        book.refresh_from_db()
        assert book.status == MediaStatus.WANTED

    def test_delete_download_attempt_with_files(
        self, download_service, book, download_client_config, tmp_path
    ):
        content_type = ContentType.objects.get_for_model(book)
        raw_file = tmp_path / "raw.epub"
        raw_file.write_text("test content")
        post_file = tmp_path / "post.epub"
        post_file.write_text("test content")

        attempt = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="1",
            release_title="Test Release",
            download_url="https://example.com/test.nzb",
            status=DownloadAttemptStatus.DOWNLOADED,
            download_client=download_client_config,
            raw_file_path=str(raw_file),
            post_processed_file_path=str(post_file),
        )

        result = download_service.delete_download_attempt(attempt.id)

        assert result["success"] is True
        assert "Raw file deleted" in result["messages"]
        assert "Post-processed file deleted" in result["messages"]

        assert not raw_file.exists()
        assert not post_file.exists()

    def test_delete_download_attempt_with_other_downloads(
        self, download_service, book, download_client_config
    ):
        content_type = ContentType.objects.get_for_model(book)
        attempt1 = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="1",
            release_title="Test Release 1",
            download_url="magnet:test1",
            status=DownloadAttemptStatus.DOWNLOADED,
            download_client=download_client_config,
        )
        DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="2",
            release_title="Test Release 2",
            download_url="magnet:test2",
            status=DownloadAttemptStatus.DOWNLOADING,
            download_client=download_client_config,
        )

        book.status = MediaStatus.DOWNLOADED
        book.save()

        result = download_service.delete_download_attempt(attempt1.id)

        assert result["success"] is True

        book.refresh_from_db()
        assert book.status == MediaStatus.DOWNLOADED

    @pytest.mark.django_db
    def test_delete_download_attempt_not_found(self, download_service):
        fake_id = uuid4()
        with pytest.raises(
            DownloadServiceError, match=f"Download attempt {fake_id} not found"
        ):
            download_service.delete_download_attempt(fake_id)
