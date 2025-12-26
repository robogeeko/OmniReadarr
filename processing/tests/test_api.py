from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from core.models_processing import ProcessingConfiguration
from downloaders.models import DownloadAttempt, DownloadAttemptStatus
from media.models import Book


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def book(db):
    return Book.objects.create(
        title="Test Book",
        authors=["John Doe"],
    )


@pytest.fixture
def download_attempt(db, book):
    content_type = ContentType.objects.get_for_model(book)
    return DownloadAttempt.objects.create(
        content_type=content_type,
        object_id=book.id,
        indexer="TestIndexer",
        indexer_id="1",
        release_title="Test Book Release",
        download_url="https://example.com/file.nzb",
        status=DownloadAttemptStatus.DOWNLOADED,
    )


@pytest.fixture
def processing_config(db):
    return ProcessingConfiguration.objects.create(
        name="Test Config",
        completed_downloads_path="/tmp/downloads",
        library_base_path="/tmp/library",
        enabled=True,
    )


class TestConvertToEpubAPI:
    def test_convert_to_epub_success(self, client, download_attempt, processing_config):
        with patch(
            "processing.api.convert_to_epub_for_attempt"
        ) as mock_convert:
            mock_convert.return_value = {
                "success": True,
                "message": "Successfully converted to EPUB",
            }
            
            response = client.post(
                f"/api/processing/convert/{download_attempt.id}/",
                content_type="application/json",
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Successfully converted" in data["message"]
            mock_convert.assert_called_once_with(download_attempt.id)

    def test_convert_to_epub_failure(self, client, download_attempt, processing_config):
        with patch(
            "processing.api.convert_to_epub_for_attempt"
        ) as mock_convert:
            mock_convert.return_value = {
                "success": False,
                "error": "Conversion failed",
            }
            
            response = client.post(
                f"/api/processing/convert/{download_attempt.id}/",
                content_type="application/json",
            )
            
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False
            assert "error" in data

    def test_convert_to_epub_not_found(self, client):
        fake_id = uuid4()
        response = client.post(
            f"/api/processing/convert/{fake_id}/",
            content_type="application/json",
        )
        
        assert response.status_code in (200, 400, 500)
        data = response.json()
        assert data["success"] is False

    def test_convert_to_epub_exception(self, client, download_attempt, processing_config):
        with patch(
            "processing.api.convert_to_epub_for_attempt"
        ) as mock_convert:
            mock_convert.side_effect = Exception("Unexpected error")
            
            response = client.post(
                f"/api/processing/convert/{download_attempt.id}/",
                content_type="application/json",
            )
            
            assert response.status_code == 500
            data = response.json()
            assert data["success"] is False
            assert "error" in data

    def test_convert_to_epub_get_method_not_allowed(self, client, download_attempt):
        response = client.get(f"/api/processing/convert/{download_attempt.id}/")
        assert response.status_code == 405


class TestOrganizeToLibraryAPI:
    def test_organize_to_library_success(self, client, download_attempt, book, processing_config):
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            downloads_dir = Path(tmpdir) / "downloads"
            downloads_dir.mkdir()
            library_dir = Path(tmpdir) / "library"
            library_dir.mkdir()
            
            source_file = downloads_dir / "test.epub"
            source_file.write_text("test content")
            
            processing_config.completed_downloads_path = str(downloads_dir)
            processing_config.library_base_path = str(library_dir)
            processing_config.save()
            
            download_attempt.raw_file_path = str(source_file)
            download_attempt.save()
            
            response = client.post(
                f"/api/processing/organize/{download_attempt.id}/",
                content_type="application/json",
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_organize_to_library_failure(self, client, download_attempt, book, processing_config):
        response = client.post(
            f"/api/processing/organize/{download_attempt.id}/",
            content_type="application/json",
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_organize_to_library_not_found(self, client):
        fake_id = uuid4()
        response = client.post(
            f"/api/processing/organize/{fake_id}/",
            content_type="application/json",
        )
        
        assert response.status_code in (400, 500)
        data = response.json()
        assert data["success"] is False

    def test_organize_to_library_exception(self, client, download_attempt, book, processing_config):
        with patch(
            "processing.api.organize_to_library_for_attempt"
        ) as mock_organize:
            mock_organize.side_effect = Exception("Unexpected error")
            
            response = client.post(
                f"/api/processing/organize/{download_attempt.id}/",
                content_type="application/json",
            )
            
            assert response.status_code == 500
            data = response.json()
            assert data["success"] is False
            assert "error" in data

    def test_organize_to_library_get_method_not_allowed(self, client, download_attempt):
        response = client.get(f"/api/processing/organize/{download_attempt.id}/")
        assert response.status_code == 405

