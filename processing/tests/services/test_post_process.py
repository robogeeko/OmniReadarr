from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.contenttypes.models import ContentType

from core.models_processing import ProcessingConfiguration
from downloaders.models import DownloadAttempt, DownloadAttemptStatus
from media.models import Book
from processing.services.post_process import (
    convert_to_epub_for_attempt,
    organize_to_library_for_attempt,
)
from processing.utils.ebook_converter import EbookConverterError
from processing.utils.file_discovery import FileDiscoveryError
from processing.utils.file_organizer import FileOrganizerError


@pytest.fixture
def processing_config(db):
    return ProcessingConfiguration.objects.create(
        name="Test Config",
        completed_downloads_path="/tmp/downloads",
        library_base_path="/tmp/library",
        calibre_ebook_convert_path="ebook-convert",
        enabled=True,
    )


@pytest.fixture
def book(db):
    return Book.objects.create(
        title="Test Book",
        authors=["John Doe"],
        description="A test book",
        language="en",
    )


@pytest.fixture
def download_attempt(db, book, processing_config):
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


class TestConvertToEpubForAttempt:
    @pytest.mark.django_db
    def test_convert_to_epub_attempt_not_found(self):
        fake_id = uuid4()
        result = convert_to_epub_for_attempt(fake_id)
        assert result["success"] is False
        error = result.get("error")
        assert isinstance(error, str)
        assert "not found" in error.lower()

    def test_convert_to_epub_no_config(self, download_attempt):
        ProcessingConfiguration.objects.all().delete()
        
        result = convert_to_epub_for_attempt(download_attempt.id)
        assert result["success"] is False
        error = result.get("error")
        assert isinstance(error, str)
        assert "No enabled processing configuration" in error

    @patch("processing.services.post_process.find_downloaded_file")
    @patch("processing.services.post_process.convert_to_epub")
    def test_convert_to_epub_success(
        self, mock_convert, mock_find, download_attempt, processing_config
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "test.mobi"
            input_file.write_text("test content")
            output_file = Path(tmpdir) / "test.epub"
            output_file.write_text("epub content")
            
            mock_find.return_value = str(input_file)
            mock_convert.return_value = str(output_file)
            
            result = convert_to_epub_for_attempt(download_attempt.id)
            
            assert result["success"] is True
            message = result.get("message")
            assert isinstance(message, str)
            assert "Successfully converted" in message
            
            download_attempt.refresh_from_db()
            assert download_attempt.post_processed_file_path == str(output_file)

    @patch("processing.services.post_process.find_downloaded_file")
    def test_convert_to_epub_already_epub(
        self, mock_find, download_attempt, processing_config
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            epub_file = Path(tmpdir) / "test.epub"
            epub_file.write_text("epub content")
            
            mock_find.return_value = str(epub_file)
            
            result = convert_to_epub_for_attempt(download_attempt.id)
            
            assert result["success"] is True
            message = result.get("message")
            assert isinstance(message, str)
            assert "already EPUB format" in message
            
            download_attempt.refresh_from_db()
            assert download_attempt.post_processed_file_path == str(epub_file)

    @patch("processing.services.post_process.find_downloaded_file")
    def test_convert_to_epub_file_discovery_error(
        self, mock_find, download_attempt, processing_config
    ):
        mock_find.side_effect = FileDiscoveryError("File not found")
        
        result = convert_to_epub_for_attempt(download_attempt.id)
        
        assert result["success"] is False
        error = result.get("error")
        assert isinstance(error, str)
        assert "File not found" in error

    @patch("processing.services.post_process.find_downloaded_file")
    @patch("processing.services.post_process.convert_to_epub")
    def test_convert_to_epub_conversion_error(
        self, mock_convert, mock_find, download_attempt, processing_config
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "test.mobi"
            input_file.write_text("test content")
            
            mock_find.return_value = str(input_file)
            mock_convert.side_effect = EbookConverterError("Conversion failed")
            
            result = convert_to_epub_for_attempt(download_attempt.id)
            
            assert result["success"] is False
            error = result.get("error")
            assert isinstance(error, str)
            assert "Conversion failed" in error

    @patch("processing.services.post_process.find_downloaded_file")
    def test_convert_to_epub_uses_existing_raw_file_path(
        self, mock_find, download_attempt, processing_config
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            epub_file = Path(tmpdir) / "test.epub"
            epub_file.write_text("epub content")
            
            download_attempt.raw_file_path = str(epub_file)
            download_attempt.save()
            
            result = convert_to_epub_for_attempt(download_attempt.id)
            
            mock_find.assert_not_called()
            assert result["success"] is True


class TestOrganizeToLibraryForAttempt:
    @pytest.mark.django_db
    def test_organize_to_library_attempt_not_found(self):
        fake_id = uuid4()
        result = organize_to_library_for_attempt(fake_id)
        assert result["success"] is False
        error = result.get("error")
        assert isinstance(error, str)
        assert "not found" in error.lower()

    def test_organize_to_library_no_media(self, db, processing_config):
        content_type = ContentType.objects.get_for_model(Book)
        attempt = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=uuid4(),
            indexer="TestIndexer",
            indexer_id="1",
            release_title="Test Release",
            download_url="https://example.com/file.nzb",
            status=DownloadAttemptStatus.DOWNLOADED,
        )
        
        result = organize_to_library_for_attempt(attempt.id)
        assert result["success"] is False
        error = result.get("error")
        assert isinstance(error, str)
        assert "Media not found" in error

    def test_organize_to_library_no_config(self, download_attempt):
        ProcessingConfiguration.objects.all().delete()
        
        result = organize_to_library_for_attempt(download_attempt.id)
        assert result["success"] is False
        error = result.get("error")
        assert isinstance(error, str)
        assert "No enabled processing configuration" in error

    @patch("processing.services.post_process.find_downloaded_file")
    @patch("processing.services.post_process.organize_to_library")
    @patch("processing.services.post_process.generate_opf")
    @patch("processing.services.post_process.download_cover")
    def test_organize_to_library_success(
        self,
        mock_download_cover,
        mock_generate_opf,
        mock_organize,
        mock_find,
        download_attempt,
        book,
        processing_config,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "test.epub"
            source_file.write_text("test content")
            
            library_file = Path(tmpdir) / "library" / "John Doe" / "Test Book" / "Test Book.epub"
            library_file.parent.mkdir(parents=True)
            library_file.write_text("test content")
            
            opf_file = library_file.parent / "Test Book.opf"
            cover_file = library_file.parent / "Test Book.jpg"
            
            mock_find.return_value = str(source_file)
            mock_organize.return_value = str(library_file)
            mock_generate_opf.return_value = str(opf_file)
            mock_download_cover.return_value = str(cover_file)
            
            book.cover_url = "https://example.com/cover.jpg"
            book.save()
            
            result = organize_to_library_for_attempt(download_attempt.id)
            
            assert result["success"] is True
            message = result.get("message")
            assert isinstance(message, str)
            assert "Successfully organized" in message
            
            book.refresh_from_db()
            assert book.library_path == str(library_file)
            assert book.cover_path == str(cover_file)
            
            download_attempt.refresh_from_db()
            assert download_attempt.post_processed_file_path == str(library_file)

    @patch("processing.services.post_process.find_downloaded_file")
    @patch("processing.services.post_process.organize_to_library")
    @patch("processing.services.post_process.generate_opf")
    def test_organize_to_library_uses_post_processed_file(
        self,
        mock_generate_opf,
        mock_organize,
        mock_find,
        download_attempt,
        book,
        processing_config,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            epub_file = Path(tmpdir) / "test.epub"
            epub_file.write_text("epub content")
            
            library_file = Path(tmpdir) / "library" / "John Doe" / "Test Book" / "Test Book.epub"
            library_file.parent.mkdir(parents=True)
            
            download_attempt.post_processed_file_path = str(epub_file)
            download_attempt.save()
            
            mock_organize.return_value = str(library_file)
            mock_generate_opf.return_value = str(library_file.parent / "Test Book.opf")
            
            result = organize_to_library_for_attempt(download_attempt.id)
            
            mock_find.assert_not_called()
            assert result["success"] is True

    @patch("processing.services.post_process.find_downloaded_file")
    @patch("processing.services.post_process.organize_to_library")
    @patch("processing.services.post_process.generate_opf")
    def test_organize_to_library_uses_raw_file_path(
        self,
        mock_generate_opf,
        mock_organize,
        mock_find,
        download_attempt,
        book,
        processing_config,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_file = Path(tmpdir) / "raw.epub"
            raw_file.write_text("raw content")
            
            library_file = Path(tmpdir) / "library" / "John Doe" / "Test Book" / "Test Book.epub"
            library_file.parent.mkdir(parents=True)
            
            download_attempt.raw_file_path = str(raw_file)
            download_attempt.save()
            
            mock_organize.return_value = str(library_file)
            mock_generate_opf.return_value = str(library_file.parent / "Test Book.opf")
            
            result = organize_to_library_for_attempt(download_attempt.id)
            
            mock_find.assert_not_called()
            assert result["success"] is True

    @patch("processing.services.post_process.find_downloaded_file")
    def test_organize_to_library_file_discovery_error(
        self, mock_find, download_attempt, book, processing_config
    ):
        mock_find.side_effect = FileDiscoveryError("File not found")
        
        result = organize_to_library_for_attempt(download_attempt.id)
        
        assert result["success"] is False
        error = result.get("error")
        assert isinstance(error, str)
        assert "File not found" in error

    @patch("processing.services.post_process.find_downloaded_file")
    @patch("processing.services.post_process.organize_to_library")
    def test_organize_to_library_organization_error(
        self, mock_organize, mock_find, download_attempt, book, processing_config
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "test.epub"
            source_file.write_text("test content")
            
            mock_find.return_value = str(source_file)
            mock_organize.side_effect = FileOrganizerError("Organization failed")
            
            result = organize_to_library_for_attempt(download_attempt.id)
            
            assert result["success"] is False
            error = result.get("error")
            assert isinstance(error, str)
            assert "Organization failed" in error

    @patch("processing.services.post_process.find_downloaded_file")
    @patch("processing.services.post_process.organize_to_library")
    @patch("processing.services.post_process.generate_opf")
    @patch("processing.services.post_process.download_cover")
    def test_organize_to_library_opf_generation_fails_continues(
        self,
        mock_download_cover,
        mock_generate_opf,
        mock_organize,
        mock_find,
        download_attempt,
        book,
        processing_config,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "test.epub"
            source_file.write_text("test content")
            
            library_file = Path(tmpdir) / "library" / "John Doe" / "Test Book" / "Test Book.epub"
            library_file.parent.mkdir(parents=True)
            
            mock_find.return_value = str(source_file)
            mock_organize.return_value = str(library_file)
            mock_generate_opf.side_effect = Exception("OPF generation failed")
            
            result = organize_to_library_for_attempt(download_attempt.id)
            
            assert result["success"] is True

    @patch("processing.services.post_process.find_downloaded_file")
    @patch("processing.services.post_process.organize_to_library")
    @patch("processing.services.post_process.generate_opf")
    @patch("processing.services.post_process.download_cover")
    def test_organize_to_library_cover_download_fails_continues(
        self,
        mock_download_cover,
        mock_generate_opf,
        mock_organize,
        mock_find,
        download_attempt,
        book,
        processing_config,
    ):
        from processing.utils.cover_downloader import CoverDownloadError
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "test.epub"
            source_file.write_text("test content")
            
            library_file = Path(tmpdir) / "library" / "John Doe" / "Test Book" / "Test Book.epub"
            library_file.parent.mkdir(parents=True)
            
            mock_find.return_value = str(source_file)
            mock_organize.return_value = str(library_file)
            mock_generate_opf.return_value = str(library_file.parent / "Test Book.opf")
            mock_download_cover.side_effect = CoverDownloadError("Cover download failed")
            
            book.cover_url = "https://example.com/cover.jpg"
            book.save()
            
            result = organize_to_library_for_attempt(download_attempt.id)
            
            assert result["success"] is True
            
            book.refresh_from_db()
            assert book.library_path == str(library_file)
            assert book.cover_path == ""

    @patch("processing.services.post_process.find_downloaded_file")
    @patch("processing.services.post_process.organize_to_library")
    @patch("processing.services.post_process.generate_opf")
    def test_organize_to_library_no_cover_url(
        self,
        mock_generate_opf,
        mock_organize,
        mock_find,
        download_attempt,
        book,
        processing_config,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "test.epub"
            source_file.write_text("test content")
            
            library_file = Path(tmpdir) / "library" / "John Doe" / "Test Book" / "Test Book.epub"
            library_file.parent.mkdir(parents=True)
            
            mock_find.return_value = str(source_file)
            mock_organize.return_value = str(library_file)
            mock_generate_opf.return_value = str(library_file.parent / "Test Book.opf")
            
            book.cover_url = ""
            book.save()
            
            result = organize_to_library_for_attempt(download_attempt.id)
            
            assert result["success"] is True
            
            book.refresh_from_db()
            assert book.cover_path == ""

    @patch("processing.services.post_process.find_downloaded_file")
    @patch("processing.services.post_process.organize_to_library")
    @patch("processing.services.post_process.generate_opf")
    def test_organize_to_library_no_authors(
        self,
        mock_generate_opf,
        mock_organize,
        mock_find,
        download_attempt,
        book,
        processing_config,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "test.epub"
            source_file.write_text("test content")
            
            library_file = Path(tmpdir) / "library" / "Unknown Author" / "Test Book" / "Test Book.epub"
            library_file.parent.mkdir(parents=True)
            
            book.authors = []
            book.save()
            
            mock_find.return_value = str(source_file)
            mock_organize.return_value = str(library_file)
            mock_generate_opf.return_value = str(library_file.parent / "Test Book.opf")
            
            result = organize_to_library_for_attempt(download_attempt.id)
            
            assert result["success"] is True
            mock_organize.assert_called_once()
            call_args = mock_organize.call_args
            assert call_args[1]["author"] == "Unknown Author"

