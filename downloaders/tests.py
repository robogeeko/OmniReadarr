from __future__ import annotations


import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from downloaders.models import (
    BlacklistReason,
    ClientType,
    DownloadAttempt,
    DownloadAttemptStatus,
    DownloadBlacklist,
    DownloadClientConfiguration,
)
from media.models import Audiobook, Book


@pytest.mark.django_db
class TestDownloadAttempt:
    def test_create_download_attempt(self, book):
        client_config = DownloadClientConfiguration.objects.create(
            name="Test SABnzbd",
            host="localhost",
            port=8080,
            api_key="key",
        )
        content_type = ContentType.objects.get_for_model(Book)
        attempt = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="123",
            release_title="Test Release",
            download_url="http://example.com/file.nzb",
            download_client=client_config,
        )
        assert attempt.media == book
        assert attempt.indexer == "TestIndexer"
        assert attempt.indexer_id == "123"
        assert attempt.release_title == "Test Release"
        assert attempt.download_url == "http://example.com/file.nzb"
        assert attempt.status == DownloadAttemptStatus.PENDING
        assert attempt.download_client == client_config
        assert "Test Release" in str(attempt)

    def test_download_attempt_defaults(self, book):
        content_type = ContentType.objects.get_for_model(Book)
        attempt = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="123",
            release_title="Test Release",
            download_url="http://example.com/file.nzb",
        )
        assert attempt.status == DownloadAttemptStatus.PENDING
        assert attempt.file_size is None
        assert attempt.seeders is None
        assert attempt.leechers is None
        assert attempt.download_client is None
        assert attempt.download_client_download_id == ""
        assert attempt.raw_file_path == ""
        assert attempt.post_processed_file_path == ""
        assert attempt.post_process_status == ""

    def test_download_attempt_with_audiobook(self, audiobook):
        content_type = ContentType.objects.get_for_model(Audiobook)
        attempt = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=audiobook.id,
            indexer="TestIndexer",
            indexer_id="123",
            release_title="Test Audiobook Release",
            download_url="http://example.com/file.nzb",
        )
        assert attempt.media == audiobook

    def test_download_attempt_ordering(self, book):
        content_type = ContentType.objects.get_for_model(Book)
        attempt1 = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="1",
            release_title="Release 1",
            download_url="http://example.com/1.nzb",
        )
        attempt2 = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="2",
            release_title="Release 2",
            download_url="http://example.com/2.nzb",
        )
        attempts = list(DownloadAttempt.objects.all())
        assert attempts[0] == attempt2
        assert attempts[1] == attempt1

    def test_download_attempt_seeders_validation(self, book):
        content_type = ContentType.objects.get_for_model(Book)
        attempt = DownloadAttempt(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="123",
            release_title="Test Release",
            download_url="http://example.com/file.nzb",
            seeders=-1,
        )
        with pytest.raises(ValidationError):
            attempt.full_clean()

    def test_download_attempt_leechers_validation(self, book):
        content_type = ContentType.objects.get_for_model(Book)
        attempt = DownloadAttempt(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="123",
            release_title="Test Release",
            download_url="http://example.com/file.nzb",
            leechers=-1,
        )
        with pytest.raises(ValidationError):
            attempt.full_clean()


@pytest.mark.django_db
class TestDownloadBlacklist:
    def test_create_download_blacklist(self, book):
        content_type = ContentType.objects.get_for_model(Book)
        blacklist = DownloadBlacklist.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="123",
            release_title="Bad Release",
            download_url="http://example.com/bad.nzb",
            reason=BlacklistReason.FAILED_DOWNLOAD,
            blacklisted_by="user",
        )
        assert blacklist.media == book
        assert blacklist.indexer == "TestIndexer"
        assert blacklist.indexer_id == "123"
        assert blacklist.release_title == "Bad Release"
        assert blacklist.reason == BlacklistReason.FAILED_DOWNLOAD
        assert blacklist.blacklisted_by == "user"
        assert "Bad Release" in str(blacklist)

    def test_download_blacklist_unique_constraint(self, book):
        content_type = ContentType.objects.get_for_model(Book)
        DownloadBlacklist.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="123",
            release_title="Bad Release",
            download_url="http://example.com/bad.nzb",
            reason=BlacklistReason.FAILED_DOWNLOAD,
        )
        with pytest.raises(Exception):
            DownloadBlacklist.objects.create(
                content_type=content_type,
                object_id=book.id,
                indexer="TestIndexer",
                indexer_id="123",
                release_title="Bad Release 2",
                download_url="http://example.com/bad2.nzb",
                reason=BlacklistReason.WRONG_FILE,
            )

    def test_download_blacklist_different_media_allowed(self, book, audiobook):
        book_content_type = ContentType.objects.get_for_model(Book)
        audiobook_content_type = ContentType.objects.get_for_model(Audiobook)
        DownloadBlacklist.objects.create(
            content_type=book_content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="123",
            release_title="Bad Release",
            download_url="http://example.com/bad.nzb",
            reason=BlacklistReason.FAILED_DOWNLOAD,
        )
        DownloadBlacklist.objects.create(
            content_type=audiobook_content_type,
            object_id=audiobook.id,
            indexer="TestIndexer",
            indexer_id="123",
            release_title="Bad Release",
            download_url="http://example.com/bad.nzb",
            reason=BlacklistReason.FAILED_DOWNLOAD,
        )
        assert DownloadBlacklist.objects.count() == 2

    def test_download_blacklist_ordering(self, book):
        content_type = ContentType.objects.get_for_model(Book)
        blacklist1 = DownloadBlacklist.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="1",
            release_title="Bad Release 1",
            download_url="http://example.com/bad1.nzb",
            reason=BlacklistReason.FAILED_DOWNLOAD,
        )
        blacklist2 = DownloadBlacklist.objects.create(
            content_type=content_type,
            object_id=book.id,
            indexer="TestIndexer",
            indexer_id="2",
            release_title="Bad Release 2",
            download_url="http://example.com/bad2.nzb",
            reason=BlacklistReason.WRONG_FILE,
        )
        blacklists = list(DownloadBlacklist.objects.all())
        assert blacklists[0] == blacklist2
        assert blacklists[1] == blacklist1


@pytest.mark.django_db
class TestDownloadClientConfiguration:
    def test_create_download_client_configuration(self):
        config = DownloadClientConfiguration.objects.create(
            name="Main SABnzbd",
            client_type=ClientType.SABNZBD,
            host="localhost",
            port=8080,
            api_key="test-api-key",
        )
        assert config.name == "Main SABnzbd"
        assert config.client_type == ClientType.SABNZBD
        assert config.host == "localhost"
        assert config.port == 8080
        assert config.api_key == "test-api-key"
        assert config.use_ssl is False
        assert config.enabled is True
        assert config.priority == 0
        assert "SABnzbd" in str(config)

    def test_download_client_configuration_defaults(self):
        config = DownloadClientConfiguration.objects.create(
            name="Test",
            host="localhost",
            port=8080,
            api_key="key",
        )
        assert config.client_type == ClientType.SABNZBD
        assert config.use_ssl is False
        assert config.enabled is True
        assert config.priority == 0

    def test_download_client_configuration_ordering(self):
        config1 = DownloadClientConfiguration.objects.create(
            name="B Config",
            host="localhost",
            port=8080,
            api_key="key",
            priority=2,
        )
        config2 = DownloadClientConfiguration.objects.create(
            name="A Config",
            host="localhost",
            port=8080,
            api_key="key",
            priority=1,
        )
        configs = list(DownloadClientConfiguration.objects.all())
        assert configs[0] == config2
        assert configs[1] == config1

    def test_download_client_configuration_port_validation(self):
        config = DownloadClientConfiguration(
            name="Test",
            host="localhost",
            port=0,
            api_key="key",
        )
        with pytest.raises(ValidationError):
            config.full_clean()
