from __future__ import annotations

import httpx

from indexers.models import ProwlarrConfiguration
from indexers.prowlarr.results import IndexerInfo, SearchResult


class ProwlarrClientError(Exception):
    pass


class ProwlarrClient:
    def __init__(self, config: ProwlarrConfiguration | None = None):
        if config is None:
            config = ProwlarrConfiguration.objects.filter(enabled=True).first()
            if config is None:
                raise ProwlarrClientError("No enabled Prowlarr configuration found")

        self.config = config
        self.base_url = self._build_base_url()
        self.headers = {"X-Api-Key": config.api_key}

    def _build_base_url(self) -> str:
        protocol = "https" if self.config.use_ssl else "http"
        base_path = self.config.base_path.strip("/") if self.config.base_path else ""
        url = f"{protocol}://{self.config.host}:{self.config.port}"
        if base_path:
            url = f"{url}/{base_path}"
        return url

    def test_connection(self) -> bool:
        try:
            url = f"{self.base_url}/api/v1/system/status"
            response = httpx.get(
                url,
                headers=self.headers,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            return True
        except Exception:
            return False

    def search(
        self,
        query: str,
        category: int | None = 7000,
        indexer: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort_key: str | None = None,
        sort_dir: str = "desc",
    ) -> list[SearchResult]:
        params: dict[str, str | int] = {
            "q": query,
            "limit": limit,
            "offset": offset,
            "sortdir": sort_dir,
        }

        if category:
            params["cat"] = category
        if indexer:
            params["indexer"] = indexer
        if sort_key:
            params["sortkey"] = sort_key

        try:
            url = f"{self.base_url}/api/v1/search"
            response = httpx.get(
                url,
                headers=self.headers,
                params=params,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data:
                try:
                    results.append(SearchResult.from_dict(item))
                except (KeyError, ValueError):
                    continue

            return results
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ProwlarrClientError("Authentication failed - check API key")
            raise ProwlarrClientError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.TimeoutException:
            raise ProwlarrClientError(
                f"Request timeout after {self.config.timeout} seconds"
            )
        except Exception as e:
            raise ProwlarrClientError(f"Search failed: {str(e)}")

    def get_indexers(self) -> list[IndexerInfo]:
        try:
            url = f"{self.base_url}/api/v1/indexer"
            response = httpx.get(
                url,
                headers=self.headers,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            data = response.json()

            indexers = []
            for item in data:
                try:
                    indexers.append(IndexerInfo.from_dict(item))
                except (KeyError, ValueError):
                    continue

            return indexers
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ProwlarrClientError("Authentication failed - check API key")
            raise ProwlarrClientError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
        except httpx.TimeoutException:
            raise ProwlarrClientError(
                f"Request timeout after {self.config.timeout} seconds"
            )
        except Exception as e:
            raise ProwlarrClientError(f"Failed to get indexers: {str(e)}")

    def get_indexer_capabilities(self, indexer_id: int) -> IndexerInfo | None:
        indexers = self.get_indexers()
        for indexer in indexers:
            if indexer.id == indexer_id:
                return indexer
        return None
