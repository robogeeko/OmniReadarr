from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from processing.utils.file_discovery import FileDiscoveryError, find_downloaded_file


class TestFileDiscovery:
    def test_find_downloaded_file_by_release_title(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "Test Book Release.epub"
            test_file.write_text("test content")
            
            result = find_downloaded_file(
                completed_downloads_path=tmpdir,
                release_title="Test Book Release",
            )
            
            assert result == str(test_file)

    def test_find_downloaded_file_by_download_client_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "file_SABnzbd_nzo_abc123.epub"
            test_file.write_text("test content")
            
            result = find_downloaded_file(
                completed_downloads_path=tmpdir,
                release_title="Some Title",
                download_client_id="SABnzbd_nzo_abc123",
            )
            
            assert result == str(test_file)

    def test_find_downloaded_file_with_client_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            client_file = Path(tmpdir) / "other_SABnzbd_nzo_abc123.mobi"
            client_file.write_text("test content")
            
            result = find_downloaded_file(
                completed_downloads_path=tmpdir,
                release_title="Some Title",
                download_client_id="SABnzbd_nzo_abc123",
            )
            
            assert result == str(client_file)
            assert "SABnzbd_nzo_abc123" in result

    def test_find_downloaded_file_supports_multiple_formats(self):
        formats = [".epub", ".mobi", ".azw", ".azw3", ".pdf", ".txt", ".rtf", ".fb2", ".lit"]
        
        for ext in formats:
            with tempfile.TemporaryDirectory() as tmpdir:
                test_file = Path(tmpdir) / f"Test Book{ext}"
                test_file.write_text("test content")
                
                result = find_downloaded_file(
                    completed_downloads_path=tmpdir,
                    release_title="Test Book",
                )
                
                assert result == str(test_file)

    def test_find_downloaded_file_searches_subdirectories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            test_file = subdir / "Test Book Release.epub"
            test_file.write_text("test content")
            
            result = find_downloaded_file(
                completed_downloads_path=tmpdir,
                release_title="Test Book Release",
            )
            
            assert result == str(test_file)

    def test_find_downloaded_file_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test book release.EPUB"
            test_file.write_text("test content")
            
            result = find_downloaded_file(
                completed_downloads_path=tmpdir,
                release_title="Test Book Release",
            )
            
            assert result == str(test_file)

    def test_find_downloaded_file_path_not_exists(self):
        with pytest.raises(FileDiscoveryError, match="does not exist"):
            find_downloaded_file(
                completed_downloads_path="/nonexistent/path",
                release_title="Test Book",
            )

    def test_find_downloaded_file_path_not_directory(self):
        with tempfile.NamedTemporaryFile() as tmpfile:
            with pytest.raises(FileDiscoveryError, match="not a directory"):
                find_downloaded_file(
                    completed_downloads_path=tmpfile.name,
                    release_title="Test Book",
                )

    def test_find_downloaded_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "other_file.txt").write_text("test")
            
            with pytest.raises(FileDiscoveryError, match="Could not find downloaded file"):
                find_downloaded_file(
                    completed_downloads_path=tmpdir,
                    release_title="Nonexistent Book",
                )

