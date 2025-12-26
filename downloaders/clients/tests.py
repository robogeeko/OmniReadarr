from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from downloaders.models import ClientType, DownloadClientConfiguration
from downloaders.clients.sabnzbd import SABnzbdClient, SABnzbdClientError
from downloaders.clients.results import HistoryItem, JobStatus, QueueItem


@pytest.fixture
def sabnzbd_config(db):
    return DownloadClientConfiguration.objects.create(
        name="Test SABnzbd",
        client_type=ClientType.SABNZBD,
        host="localhost",
        port=8080,
        api_key="test-api-key",
        use_ssl=False,
    )


@pytest.fixture
def client(sabnzbd_config):
    return SABnzbdClient(sabnzbd_config)


class TestSABnzbdClientInit:
    def test_init_with_config(self, sabnzbd_config):
        client = SABnzbdClient(sabnzbd_config)
        assert client.config == sabnzbd_config
        assert client.base_url == "http://localhost:8080"

    def test_init_without_config_uses_enabled(self, db):
        config = DownloadClientConfiguration.objects.create(
            name="Enabled Config",
            client_type=ClientType.SABNZBD,
            host="sabnzbd.example.com",
            port=8080,
            api_key="key",
            enabled=True,
        )
        client = SABnzbdClient()
        assert client.config == config

    def test_init_without_config_no_enabled(self, db):
        DownloadClientConfiguration.objects.create(
            name="Disabled Config",
            client_type=ClientType.SABNZBD,
            host="sabnzbd.example.com",
            port=8080,
            api_key="key",
            enabled=False,
        )
        with pytest.raises(
            SABnzbdClientError, match="No enabled SABnzbd configuration"
        ):
            SABnzbdClient()

    def test_init_wrong_client_type(self, db):
        config = DownloadClientConfiguration.objects.create(
            name="Wrong Type",
            client_type="wrong_type",
            host="localhost",
            port=8080,
            api_key="key",
        )
        with pytest.raises(
            SABnzbdClientError, match="Configuration is not for SABnzbd"
        ):
            SABnzbdClient(config)

    def test_build_base_url_with_ssl(self, sabnzbd_config):
        sabnzbd_config.use_ssl = True
        sabnzbd_config.save()
        client = SABnzbdClient(sabnzbd_config)
        assert client.base_url == "https://localhost:8080"


class TestSABnzbdClientTestConnection:
    @patch("httpx.get")
    def test_test_connection_success(self, mock_get, client):
        mock_response = httpx.Response(200, json={"version": "4.0.0", "status": True})
        mock_response._request = None
        mock_response.raise_for_status = lambda: None  # type: ignore[assignment]
        mock_get.return_value = mock_response

        result = client.test_connection()

        assert result is True
        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert params["mode"] == "version"
        assert params["apikey"] == "test-api-key"
        assert params["output"] == "json"

    @patch("httpx.get")
    def test_test_connection_failure(self, mock_get, client):
        mock_request = httpx.Request("GET", "http://test.com")
        mock_response = httpx.Response(500, text="Error")
        mock_get.side_effect = httpx.HTTPStatusError(
            "Error", request=mock_request, response=mock_response
        )

        result = client.test_connection()

        assert result is False


class TestSABnzbdClientGetQueue:
    @patch("httpx.get")
    def test_get_queue_success(self, mock_get, client):
        mock_response = httpx.Response(
            200,
            json={
                "queue": {
                    "slots": [
                        {
                            "nzo_id": "SABnzbd_nzo_abc123",
                            "filename": "Test Book.nzb",
                            "status": "Downloading",
                            "mbleft": "45.2",
                            "mb": "500.0",
                            "timeleft": "00:15:30",
                            "percentage": "90.96",
                        }
                    ]
                },
                "status": True,
            },
        )
        mock_response._request = None
        mock_response.raise_for_status = lambda: None  # type: ignore[assignment]
        mock_get.return_value = mock_response

        items = client.get_queue()

        assert len(items) == 1
        assert items[0].nzo_id == "SABnzbd_nzo_abc123"
        assert items[0].filename == "Test Book.nzb"
        assert items[0].status == "Downloading"
        assert items[0].mbleft == 45.2
        assert items[0].mb == 500.0
        assert items[0].timeleft == "00:15:30"
        assert items[0].percentage == 90.96

    @patch("httpx.get")
    def test_get_queue_empty(self, mock_get, client):
        mock_response = httpx.Response(
            200, json={"queue": {"slots": []}, "status": True}
        )
        mock_response._request = None
        mock_response.raise_for_status = lambda: None  # type: ignore[assignment]
        mock_get.return_value = mock_response

        items = client.get_queue()

        assert len(items) == 0

    @patch("httpx.get")
    def test_get_queue_api_error(self, mock_get, client):
        mock_response = httpx.Response(
            200, json={"status": False, "error": "Queue error"}
        )
        mock_response._request = None
        mock_response.raise_for_status = lambda: None  # type: ignore[assignment]
        mock_get.return_value = mock_response

        with pytest.raises(SABnzbdClientError, match="SABnzbd API error"):
            client.get_queue()


class TestSABnzbdClientGetHistory:
    @patch("httpx.get")
    def test_get_history_success(self, mock_get, client):
        mock_response = httpx.Response(
            200,
            json={
                "history": {
                    "slots": [
                        {
                            "nzo_id": "SABnzbd_nzo_xyz789",
                            "name": "Completed Book.nzb",
                            "status": "Completed",
                            "size": "250.5 MB",
                            "bytes": 262144000,
                            "category": "books",
                            "storage": "/downloads/books",
                            "path": "/downloads/books/Completed Book",
                            "completed": "2024-01-15 10:30:00",
                        }
                    ]
                },
                "status": True,
            },
        )
        mock_response._request = None
        mock_response.raise_for_status = lambda: None  # type: ignore[assignment]
        mock_get.return_value = mock_response

        items = client.get_history()

        assert len(items) == 1
        assert items[0].nzo_id == "SABnzbd_nzo_xyz789"
        assert items[0].name == "Completed Book.nzb"
        assert items[0].status == "Completed"
        assert abs(items[0].size - 250.0) < 0.1
        assert items[0].category == "books"
        assert items[0].path == "/downloads/books/Completed Book"


class TestSABnzbdClientDeleteJob:
    @patch("httpx.get")
    def test_delete_job_success(self, mock_get, client):
        mock_response = httpx.Response(
            200, json={"status": True, "nzo_ids": ["SABnzbd_nzo_abc123"]}
        )
        mock_response._request = None
        mock_response.raise_for_status = lambda: None  # type: ignore[assignment]
        mock_get.return_value = mock_response

        result = client.delete_job("SABnzbd_nzo_abc123")

        assert result is True
        call_args = mock_get.call_args
        assert call_args[1]["params"]["name"] == "delete"
        assert call_args[1]["params"]["value"] == "SABnzbd_nzo_abc123"

    @patch("httpx.get")
    def test_delete_job_failure(self, mock_get, client):
        mock_response = httpx.Response(
            200, json={"status": False, "error": "Job not found"}
        )
        mock_response._request = None
        mock_response.raise_for_status = lambda: None  # type: ignore[assignment]
        mock_get.return_value = mock_response

        result = client.delete_job("invalid-id")

        assert result is False

    @patch("httpx.get")
    def test_delete_job_exception(self, mock_get, client):
        mock_get.side_effect = Exception("Network error")

        result = client.delete_job("test-id")

        assert result is False


class TestSABnzbdClientGetJobStatus:
    @patch("httpx.get")
    def test_get_job_status_in_queue(self, mock_get, client):
        mock_response = httpx.Response(
            200,
            json={
                "queue": {
                    "slots": [
                        {
                            "nzo_id": "SABnzbd_nzo_abc123",
                            "filename": "Test Book.nzb",
                            "status": "Downloading",
                            "mbleft": "45.2",
                            "mb": "500.0",
                            "timeleft": "00:15:30",
                            "percentage": "90.96",
                        }
                    ]
                },
                "status": True,
            },
        )
        mock_response._request = None
        mock_response.raise_for_status = lambda: None  # type: ignore[assignment]
        mock_get.return_value = mock_response

        status = client.get_job_status("SABnzbd_nzo_abc123")

        assert status is not None
        assert status.nzo_id == "SABnzbd_nzo_abc123"
        assert status.status == "Downloading"
        assert status.progress == 90.96

    @patch("httpx.get")
    def test_get_job_status_in_history(self, mock_get, client):
        queue_response = httpx.Response(
            200, json={"queue": {"slots": []}, "status": True}
        )
        queue_response._request = None
        queue_response.raise_for_status = lambda: None  # type: ignore[assignment]

        history_response = httpx.Response(
            200,
            json={
                "history": {
                    "slots": [
                        {
                            "nzo_id": "SABnzbd_nzo_xyz789",
                            "name": "Completed Book.nzb",
                            "status": "Completed",
                            "size": "250.5",
                            "category": "books",
                            "storage": "/downloads/books",
                            "path": "/downloads/books/Completed Book",
                            "completed": "2024-01-15 10:30:00",
                        }
                    ]
                },
                "status": True,
            },
        )
        history_response._request = None
        history_response.raise_for_status = lambda: None  # type: ignore[assignment]

        mock_get.side_effect = [queue_response, history_response]

        status = client.get_job_status("SABnzbd_nzo_xyz789")

        assert status is not None
        assert status.nzo_id == "SABnzbd_nzo_xyz789"
        assert status.status == "Completed"
        assert status.progress == 100.0
        assert status.path == "/downloads/books/Completed Book"

    @patch("httpx.get")
    def test_get_job_status_not_found(self, mock_get, client):
        queue_response = httpx.Response(
            200, json={"queue": {"slots": []}, "status": True}
        )
        queue_response._request = None
        queue_response.raise_for_status = lambda: None  # type: ignore[assignment]

        history_response = httpx.Response(
            200, json={"history": {"slots": []}, "status": True}
        )
        history_response._request = None
        history_response.raise_for_status = lambda: None  # type: ignore[assignment]

        mock_get.side_effect = [queue_response, history_response]

        status = client.get_job_status("nonexistent-id")

        assert status is None


class TestQueueItem:
    def test_from_dict_complete(self):
        data = {
            "nzo_id": "SABnzbd_nzo_abc123",
            "filename": "Test Book.nzb",
            "status": "Downloading",
            "mbleft": "45.2",
            "mb": "500.0",
            "timeleft": "00:15:30",
            "percentage": "90.96",
        }

        item = QueueItem.from_dict(data)

        assert item.nzo_id == "SABnzbd_nzo_abc123"
        assert item.filename == "Test Book.nzb"
        assert item.status == "Downloading"
        assert item.mbleft == 45.2
        assert item.mb == 500.0
        assert item.timeleft == "00:15:30"
        assert item.percentage == 90.96


class TestHistoryItem:
    def test_from_dict_complete(self):
        data = {
            "nzo_id": "SABnzbd_nzo_xyz789",
            "name": "Completed Book.nzb",
            "status": "Completed",
            "size": "250.5 MB",
            "bytes": 262144000,
            "category": "books",
            "storage": "/downloads/books",
            "path": "/downloads/books/Completed Book",
            "completed": "2024-01-15 10:30:00",
        }

        item = HistoryItem.from_dict(data)

        assert item.nzo_id == "SABnzbd_nzo_xyz789"
        assert item.name == "Completed Book.nzb"
        assert item.status == "Completed"
        assert abs(item.size - 250.0) < 0.1
        assert item.path == "/downloads/books/Completed Book"


class TestJobStatus:
    def test_from_queue_item(self):
        queue_item = QueueItem(
            nzo_id="test-id",
            filename="test.nzb",
            status="Downloading",
            mbleft=50.0,
            mb=100.0,
            timeleft="00:10:00",
            percentage=50.0,
        )

        status = JobStatus.from_queue_item(queue_item)

        assert status.nzo_id == "test-id"
        assert status.filename == "test.nzb"
        assert status.status == "Downloading"
        assert status.progress == 50.0
        assert status.mbleft == 50.0
        assert status.mb == 100.0

    def test_from_history_item(self):
        history_item = HistoryItem(
            nzo_id="test-id",
            name="test.nzb",
            status="Completed",
            size=100.0,
            category="books",
            storage="/downloads",
            path="/downloads/test",
            completed="2024-01-15",
        )

        status = JobStatus.from_history_item(history_item)

        assert status.nzo_id == "test-id"
        assert status.filename == "test.nzb"
        assert status.status == "Completed"
        assert status.progress == 100.0
        assert status.path == "/downloads/test"


class TestSABnzbdClientAddDownload:
    def test_add_download_success(self, client):
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": True,
                "nzo_ids": ["SABnzbd_nzo_abc123"],
            }
            mock_response.raise_for_status = lambda: None
            mock_get.return_value = mock_response

            result = client.add_download("https://example.com/file.nzb")

            assert result["status"] is True
            assert result["nzo_id"] == "SABnzbd_nzo_abc123"
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args.kwargs["params"]["mode"] == "addurl"
            assert call_args.kwargs["params"]["name"] == "https://example.com/file.nzb"

    def test_add_download_with_category(self, client):
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": True,
                "nzo_ids": ["SABnzbd_nzo_abc123"],
            }
            mock_response.raise_for_status = lambda: None
            mock_get.return_value = mock_response

            result = client.add_download(
                "https://example.com/file.nzb", category="books"
            )

            assert result["status"] is True
            assert result["nzo_id"] == "SABnzbd_nzo_abc123"
            call_args = mock_get.call_args
            assert call_args.kwargs["params"]["cat"] == "books"

    def test_add_download_with_priority(self, client):
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": True,
                "nzo_ids": ["SABnzbd_nzo_abc123"],
            }
            mock_response.raise_for_status = lambda: None
            mock_get.return_value = mock_response

            result = client.add_download(
                "https://example.com/file.nzb", priority="High"
            )

            assert result["status"] is True
            call_args = mock_get.call_args
            assert call_args.kwargs["params"]["priority"] == "High"

    def test_add_download_invalid_url(self, client):
        with pytest.raises(SABnzbdClientError, match="Download URL cannot be empty"):
            client.add_download("")

        with pytest.raises(SABnzbdClientError, match="Download URL cannot be empty"):
            client.add_download("   ")

    def test_add_download_api_error(self, client):
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": False,
                "error": "Invalid URL",
            }
            mock_response.raise_for_status = lambda: None
            mock_get.return_value = mock_response

            with pytest.raises(SABnzbdClientError, match="SABnzbd API error"):
                client.add_download("https://example.com/file.nzb")

    def test_add_download_no_nzo_id(self, client):
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": True, "nzo_ids": []}
            mock_response.raise_for_status = lambda: None
            mock_get.return_value = mock_response

            with pytest.raises(
                SABnzbdClientError, match="SABnzbd did not return a job ID"
            ):
                client.add_download("https://example.com/file.nzb")

    def test_add_download_authentication_error(self, client):
        with patch("httpx.get") as mock_get:
            mock_request = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Unauthorized", request=mock_request, response=mock_response
            )
            mock_get.return_value = mock_response

            with pytest.raises(SABnzbdClientError, match="Authentication failed"):
                client.add_download("https://example.com/file.nzb")

    def test_add_download_timeout(self, client):
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(SABnzbdClientError, match="Request timeout"):
                client.add_download("https://example.com/file.nzb")
