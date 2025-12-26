from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from processing.utils.cover_downloader import CoverDownloadError, download_cover


class TestCoverDownloader:
    @patch("httpx.Client")
    def test_download_cover_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "cover.jpg"
            result = download_cover("https://example.com/cover.jpg", str(output_path))

            assert result == str(output_path)
            assert output_path.exists()
            assert output_path.read_bytes() == b"fake image data"

    @patch("httpx.Client")
    def test_download_cover_creates_directory(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "cover.jpg"
            download_cover("https://example.com/cover.jpg", str(output_path))

            assert output_path.parent.exists()

    @patch("httpx.Client")
    def test_download_cover_follows_redirects(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "cover.jpg"
            download_cover("https://example.com/cover.jpg", str(output_path))

            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args[1]
            assert call_kwargs.get("follow_redirects") is True

    @patch("httpx.Client")
    def test_download_cover_warns_on_unexpected_content_type(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "cover.jpg"
            result = download_cover("https://example.com/cover.jpg", str(output_path))

            assert result == str(output_path)

    @patch("httpx.Client")
    def test_download_cover_empty_url(self, mock_client_class):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "cover.jpg"
            with pytest.raises(CoverDownloadError, match="Cover URL is empty"):
                download_cover("", str(output_path))

    @patch("httpx.Client")
    def test_download_cover_http_error(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_client.get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "cover.jpg"
            with pytest.raises(CoverDownloadError, match="HTTP error"):
                download_cover("https://example.com/cover.jpg", str(output_path))

    @patch("httpx.Client")
    def test_download_cover_timeout(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "cover.jpg"
            with pytest.raises(CoverDownloadError, match="Timeout"):
                download_cover(
                    "https://example.com/cover.jpg", str(output_path), timeout=10
                )

    @patch("httpx.Client")
    def test_download_cover_file_not_written(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nonexistent" / "cover.jpg"
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                with pytest.raises(
                    CoverDownloadError, match="Failed to download cover"
                ):
                    download_cover("https://example.com/cover.jpg", str(output_path))
