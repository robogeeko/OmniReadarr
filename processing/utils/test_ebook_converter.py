from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from processing.utils.ebook_converter import EbookConverterError, convert_to_epub


class TestEbookConverter:
    def test_convert_to_epub_already_epub(self):
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmpfile:
            tmpfile.write(b"test epub content")
            tmpfile_path = tmpfile.name
        
        try:
            result = convert_to_epub(tmpfile_path, tmpfile_path.replace(".epub", "_converted.epub"))
            assert result == tmpfile_path
        finally:
            Path(tmpfile_path).unlink()

    @patch("subprocess.run")
    def test_convert_to_epub_success(self, mock_run):
        input_path = "/tmp/test.mobi"
        output_path = "/tmp/test.epub"
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Conversion successful"
        mock_run.return_value = mock_result
        
        with patch("os.path.exists", return_value=True):
            result = convert_to_epub(input_path, output_path)
        
        assert result == output_path
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0][0] == "ebook-convert"
        assert call_args[0][0][1] == input_path
        assert call_args[0][0][2] == output_path

    @patch("subprocess.run")
    def test_convert_to_epub_custom_path(self, mock_run):
        input_path = "/tmp/test.mobi"
        output_path = "/tmp/test.epub"
        custom_path = "/usr/local/bin/ebook-convert"
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        with patch("os.path.exists", return_value=True):
            result = convert_to_epub(input_path, output_path, ebook_convert_path=custom_path)
        
        assert result == output_path
        call_args = mock_run.call_args
        assert call_args[0][0][0] == custom_path

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_convert_to_epub_creates_output_directory(self, mock_makedirs, mock_run):
        input_path = "/tmp/test.mobi"
        output_path = "/tmp/subdir/test.epub"
        
        call_count = [0]
        def exists_side_effect(path):
            call_count[0] += 1
            if path == input_path:
                return True
            if path == output_path:
                if call_count[0] <= 2:
                    return False
                return True
            if path == "/tmp/subdir":
                return False
            return False
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        with patch("os.path.exists", side_effect=exists_side_effect):
            convert_to_epub(input_path, output_path)
        
        mock_makedirs.assert_called()
        call_args = mock_makedirs.call_args
        assert "/tmp/subdir" in str(call_args[0][0])

    @patch("subprocess.run")
    def test_convert_to_epub_file_not_found(self, mock_run):
        input_path = "/nonexistent/test.mobi"
        
        with pytest.raises(EbookConverterError, match="does not exist"):
            convert_to_epub(input_path, "/tmp/test.epub")

    @patch("subprocess.run")
    def test_convert_to_epub_timeout(self, mock_run):
        input_path = "/tmp/test.mobi"
        output_path = "/tmp/test.epub"
        
        mock_run.side_effect = subprocess.TimeoutExpired("ebook-convert", 300)
        
        with patch("os.path.exists", return_value=True):
            with pytest.raises(EbookConverterError, match="timed out"):
                convert_to_epub(input_path, output_path)

    @patch("subprocess.run")
    def test_convert_to_epub_conversion_fails(self, mock_run):
        input_path = "/tmp/test.mobi"
        output_path = "/tmp/test.epub"
        
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Conversion failed"
        mock_run.side_effect = subprocess.CalledProcessError(1, "ebook-convert", stderr="Conversion failed")
        
        with patch("os.path.exists", return_value=True):
            with pytest.raises(EbookConverterError, match="Conversion failed"):
                convert_to_epub(input_path, output_path)

    @patch("subprocess.run")
    def test_convert_to_epub_output_file_not_created(self, mock_run):
        input_path = "/tmp/test.mobi"
        output_path = "/tmp/test.epub"
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        with patch("os.path.exists", side_effect=lambda p: p == input_path):
            with pytest.raises(EbookConverterError, match="output file not found"):
                convert_to_epub(input_path, output_path)

    @patch("subprocess.run")
    def test_convert_to_epub_ebook_convert_not_found(self, mock_run):
        input_path = "/tmp/test.mobi"
        output_path = "/tmp/test.epub"
        
        mock_run.side_effect = FileNotFoundError()
        
        with patch("os.path.exists", return_value=True):
            with pytest.raises(EbookConverterError, match="ebook-convert not found"):
                convert_to_epub(input_path, output_path)

