from __future__ import annotations

import httpx

from downloaders.models import DownloadClientConfiguration
from downloaders.clients.results import HistoryItem, JobStatus, QueueItem


class SABnzbdClientError(Exception):
    pass


class SABnzbdClient:
    def __init__(self, config: DownloadClientConfiguration | None = None):
        if config is None:
            config = (
                DownloadClientConfiguration.objects.filter(
                    enabled=True, client_type="sabnzbd"
                )
                .order_by("priority")
                .first()
            )
            if config is None:
                raise SABnzbdClientError("No enabled SABnzbd configuration found")

        if config.client_type != "sabnzbd":
            raise SABnzbdClientError(
                f"Configuration is not for SABnzbd (got {config.client_type})"
            )

        self.config = config
        self.base_url = self._build_base_url()

    def _build_base_url(self) -> str:
        protocol = "https" if self.config.use_ssl else "http"
        return f"{protocol}://{self.config.host}:{self.config.port}"

    def _make_request(self, mode: str, params: dict[str, str] | None = None) -> dict:
        request_params: dict[str, str] = {
            "mode": mode,
            "apikey": self.config.api_key,
            "output": "json",
        }
        if params:
            request_params.update(params)

        try:
            url = f"{self.base_url}/api"
            response = httpx.get(url, params=request_params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("status") is False:
                error_msg = data.get("error", "Unknown error")
                raise SABnzbdClientError(f"SABnzbd API error: {error_msg}")

            return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise SABnzbdClientError("Authentication failed - check API key")
            raise SABnzbdClientError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.TimeoutException:
            raise SABnzbdClientError("Request timeout")
        except Exception as e:
            raise SABnzbdClientError(f"Request failed: {str(e)}")

    def test_connection(self) -> bool:
        try:
            data = self._make_request("version")
            return "version" in data
        except Exception:
            return False

    def get_queue(self) -> list[QueueItem]:
        data = self._make_request("queue")
        queue_data = data.get("queue", {})
        slots = queue_data.get("slots", [])

        items = []
        for slot in slots:
            try:
                items.append(QueueItem.from_dict(slot))
            except (KeyError, ValueError):
                continue

        return items

    def get_history(self) -> list[HistoryItem]:
        data = self._make_request("history")
        history_data = data.get("history", {})
        slots = history_data.get("slots", [])

        items = []
        for slot in slots:
            try:
                items.append(HistoryItem.from_dict(slot))
            except (KeyError, ValueError):
                continue

        return items

    def delete_job(self, nzo_id: str) -> bool:
        try:
            data = self._make_request(
                "queue", params={"name": "delete", "value": nzo_id}
            )
            return data.get("status") is True
        except Exception:
            return False

    def get_job_status(self, nzo_id: str) -> JobStatus | None:
        queue_items = self.get_queue()
        for item in queue_items:
            if item.nzo_id == nzo_id:
                return JobStatus.from_queue_item(item)

        history_items = self.get_history()
        for item in history_items:
            if item.nzo_id == nzo_id:
                return JobStatus.from_history_item(item)

        return None
