from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock


from processing.utils.metadata_generator import (
    escape_xml_text,
    generate_opf,
)


class TestEscapeXmlText:
    def test_escape_xml_text_basic(self):
        assert escape_xml_text("Test") == "Test"

    def test_escape_xml_text_ampersand(self):
        assert escape_xml_text("A & B") == "A &amp; B"

    def test_escape_xml_text_less_than(self):
        assert escape_xml_text("A < B") == "A &lt; B"

    def test_escape_xml_text_greater_than(self):
        assert escape_xml_text("A > B") == "A &gt; B"

    def test_escape_xml_text_quotes(self):
        assert escape_xml_text('A "B" C') == "A &quot;B&quot; C"
        assert escape_xml_text("A 'B' C") == "A &apos;B&apos; C"

    def test_escape_xml_text_empty(self):
        assert escape_xml_text("") == ""

    def test_escape_xml_text_none(self):
        assert escape_xml_text("") == ""


class TestGenerateOpf:
    def test_generate_opf_basic(self):
        media = MagicMock()
        media.title = "Test Book"
        media.language = ""
        media.isbn = None
        media.isbn13 = None
        media.authors = []
        media.description = ""
        media.publication_date = None
        media.publisher = ""
        media.genres = []
        media.cover_path = None
        
        with tempfile.TemporaryDirectory() as tmpdir:
            opf_path = Path(tmpdir) / "test.opf"
            generate_opf(media, str(opf_path))
            
            assert opf_path.exists()
            content = opf_path.read_text()
            assert "<?xml" in content
            assert "Test Book" in content

    def test_generate_opf_with_all_fields(self):
        media = MagicMock()
        media.title = "Test Book"
        media.language = "en"
        media.isbn = "1234567890"
        media.isbn13 = None
        media.authors = ["Doe, John"]
        media.description = "A test book description"
        media.publication_date = date(2020, 1, 1)
        media.publisher = "Test Publisher"
        media.genres = ["Fiction", "Science Fiction"]
        media.cover_path = "/path/to/cover.jpg"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            opf_path = Path(tmpdir) / "test.opf"
            generate_opf(media, str(opf_path))
            
            assert opf_path.exists()
            content = opf_path.read_text()
            assert "Test Book" in content
            assert "en" in content
            assert "1234567890" in content
            assert "John Doe" in content
            assert "A test book description" in content
            assert "2020-01-01" in content
            assert "Test Publisher" in content
            assert "Fiction" in content
            assert "cover.jpg" in content

    def test_generate_opf_with_isbn13(self):
        media = MagicMock()
        media.title = "Test Book"
        media.language = ""
        media.isbn = None
        media.isbn13 = "9781234567890"
        media.authors = []
        media.description = ""
        media.publication_date = None
        media.publisher = ""
        media.genres = []
        media.cover_path = None
        
        with tempfile.TemporaryDirectory() as tmpdir:
            opf_path = Path(tmpdir) / "test.opf"
            generate_opf(media, str(opf_path))
            
            content = opf_path.read_text()
            assert "9781234567890" in content

    def test_generate_opf_author_without_comma(self):
        media = MagicMock()
        media.title = "Test Book"
        media.language = ""
        media.isbn = None
        media.isbn13 = None
        media.authors = ["John Doe"]
        media.description = ""
        media.publication_date = None
        media.publisher = ""
        media.genres = []
        media.cover_path = None
        
        with tempfile.TemporaryDirectory() as tmpdir:
            opf_path = Path(tmpdir) / "test.opf"
            generate_opf(media, str(opf_path))
            
            content = opf_path.read_text()
            assert "John Doe" in content

    def test_generate_opf_multiple_authors(self):
        media = MagicMock()
        media.title = "Test Book"
        media.language = ""
        media.isbn = None
        media.isbn13 = None
        media.authors = ["Doe, John", "Smith, Jane"]
        media.description = ""
        media.publication_date = None
        media.publisher = ""
        media.genres = []
        media.cover_path = None
        
        with tempfile.TemporaryDirectory() as tmpdir:
            opf_path = Path(tmpdir) / "test.opf"
            generate_opf(media, str(opf_path))
            
            content = opf_path.read_text()
            assert "John Doe" in content
            assert "Jane Smith" in content

    def test_generate_opf_escapes_description(self):
        media = MagicMock()
        media.title = "Test Book"
        media.language = ""
        media.isbn = None
        media.isbn13 = None
        media.authors = []
        media.description = "A <b>bold</b> description & more"
        media.publication_date = None
        media.publisher = ""
        media.genres = []
        media.cover_path = None
        
        with tempfile.TemporaryDirectory() as tmpdir:
            opf_path = Path(tmpdir) / "test.opf"
            generate_opf(media, str(opf_path))
            
            content = opf_path.read_text()
            assert "&amp;" in content
            assert "<b>" not in content
            assert "&lt;" in content or "&amp;lt;" in content

    def test_generate_opf_creates_output_directory(self):
        media = MagicMock()
        media.title = "Test Book"
        media.language = ""
        media.isbn = None
        media.isbn13 = None
        media.authors = []
        media.description = ""
        media.publication_date = None
        media.publisher = ""
        media.genres = []
        media.cover_path = None
        
        with tempfile.TemporaryDirectory() as tmpdir:
            opf_path = Path(tmpdir) / "subdir" / "test.opf"
            generate_opf(media, str(opf_path))
            
            assert opf_path.exists()

