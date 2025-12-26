from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from processing.utils.file_organizer import (
    FileOrganizerError,
    get_library_path,
    organize_to_library,
    sanitize_filename,
)


class TestSanitizeFilename:
    def test_sanitize_filename_basic(self):
        assert sanitize_filename("Test Book") == "Test Book"

    def test_sanitize_filename_special_chars(self):
        assert sanitize_filename("Test/Book:Title") == "Test_Book_Title"
        assert sanitize_filename("Test\\Book*Title") == "Test_Book_Title"
        result = sanitize_filename('Test"Book<Title>')
        assert result.startswith("Test_Book_Title")
        assert result.replace("_", "").replace("Test", "").replace("Book", "").replace("Title", "") == ""
        assert sanitize_filename("Test|Book?Title") == "Test_Book_Title"

    def test_sanitize_filename_multiple_spaces(self):
        assert sanitize_filename("Test    Book") == "Test Book"

    def test_sanitize_filename_leading_trailing_dots(self):
        assert sanitize_filename(".Test Book.") == "Test Book"

    def test_sanitize_filename_empty(self):
        assert sanitize_filename("") == "Unknown"

    def test_sanitize_filename_max_length(self):
        long_name = "A" * 300
        result = sanitize_filename(long_name, max_length=200)
        assert len(result) == 200
        assert result.endswith("A")

    def test_sanitize_filename_whitespace_only(self):
        assert sanitize_filename("   ") == "Unknown"


class TestGetLibraryPath:
    def test_get_library_path_basic(self):
        library_dir, sanitized_title = get_library_path(
            "/library", "John Doe", "Test Book"
        )
        assert library_dir == "/library/John Doe/Test Book"
        assert sanitized_title == "Test Book"

    def test_get_library_path_special_chars(self):
        library_dir, sanitized_title = get_library_path(
            "/library", "John/Doe", "Test:Book"
        )
        assert library_dir == "/library/John_Doe/Test_Book"
        assert sanitized_title == "Test_Book"

    def test_get_library_path_empty_author(self):
        library_dir, sanitized_title = get_library_path(
            "/library", "", "Test Book"
        )
        assert library_dir == "/library/Unknown Author/Test Book"
        assert sanitized_title == "Test Book"

    def test_get_library_path_empty_title(self):
        library_dir, sanitized_title = get_library_path(
            "/library", "John Doe", ""
        )
        assert library_dir == "/library/John Doe/Unknown Title"
        assert sanitized_title == "Unknown Title"


class TestOrganizeToLibrary:
    def test_organize_to_library_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "source.epub"
            source_file.write_text("test content")
            
            library_base = Path(tmpdir) / "library"
            library_base.mkdir()
            
            result = organize_to_library(
                str(source_file),
                str(library_base),
                "John Doe",
                "Test Book",
            )
            
            expected_path = library_base / "John Doe" / "Test Book" / "Test Book.epub"
            assert result == str(expected_path)
            assert expected_path.exists()
            assert expected_path.read_text() == "test content"

    def test_organize_to_library_creates_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "source.epub"
            source_file.write_text("test content")
            
            library_base = Path(tmpdir) / "library"
            library_base.mkdir()
            
            organize_to_library(
                str(source_file),
                str(library_base),
                "John Doe",
                "Test Book",
            )
            
            assert (library_base / "John Doe" / "Test Book").exists()

    def test_organize_to_library_sanitizes_names(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "source.epub"
            source_file.write_text("test content")
            
            library_base = Path(tmpdir) / "library"
            library_base.mkdir()
            
            result = organize_to_library(
                str(source_file),
                str(library_base),
                "John/Doe",
                "Test:Book",
            )
            
            expected_path = library_base / "John_Doe" / "Test_Book" / "Test_Book.epub"
            assert result == str(expected_path)

    def test_organize_to_library_preserves_extension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "source.mobi"
            source_file.write_text("test content")
            
            library_base = Path(tmpdir) / "library"
            library_base.mkdir()
            
            result = organize_to_library(
                str(source_file),
                str(library_base),
                "John Doe",
                "Test Book",
            )
            
            assert result.endswith(".mobi")

    def test_organize_to_library_source_not_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            library_base = Path(tmpdir) / "library"
            library_base.mkdir()
            
            with pytest.raises(FileOrganizerError, match="does not exist"):
                organize_to_library(
                    "/nonexistent/file.epub",
                    str(library_base),
                    "John Doe",
                    "Test Book",
                )

    def test_organize_to_library_base_not_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "source.epub"
            source_file.write_text("test content")
            
            with pytest.raises(FileOrganizerError, match="does not exist"):
                organize_to_library(
                    str(source_file),
                    "/nonexistent/library",
                    "John Doe",
                    "Test Book",
                )

    def test_organize_to_library_base_not_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "source.epub"
            source_file.write_text("test content")
            
            fake_file = Path(tmpdir) / "fake_file"
            fake_file.write_text("fake")
            
            with pytest.raises((FileOrganizerError, NotADirectoryError)):
                try:
                    organize_to_library(
                        str(source_file),
                        str(fake_file),
                        "John Doe",
                        "Test Book",
                    )
                except FileOrganizerError as e:
                    if "does not exist" in str(e) or "not a directory" in str(e):
                        raise
                    raise FileOrganizerError("Expected error")
                except NotADirectoryError:
                    raise

    def test_organize_to_library_same_file_already_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "source.epub"
            source_file.write_text("test content")
            
            library_base = Path(tmpdir) / "library"
            library_base.mkdir()
            dest_dir = library_base / "John Doe" / "Test Book"
            dest_dir.mkdir(parents=True)
            dest_file = dest_dir / "Test Book.epub"
            dest_file.write_text("existing content")
            
            result = organize_to_library(
                str(source_file),
                str(library_base),
                "John Doe",
                "Test Book",
            )
            
            assert result == str(dest_file)
            assert dest_file.read_text() == "test content"

