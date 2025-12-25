from __future__ import annotations

import logging
from urllib.parse import parse_qs, urlparse

import httpx

from indexers.models import ProwlarrConfiguration
from indexers.prowlarr.results import IndexerInfo, SearchResult

logger = logging.getLogger(__name__)


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
        category: int | list[int] | None = None,
        indexer: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort_key: str | None = None,
        sort_dir: str = "desc",
    ) -> list[SearchResult]:
        params: dict[str, str | int] = {
            "query": query,
            "limit": limit,
            "offset": offset,
            "sortdir": sort_dir,
        }

        if indexer:
            params["indexer"] = indexer
        if sort_key:
            params["sortkey"] = sort_key

        try:
            url = f"{self.base_url}/api/v1/search"
            logger.info(
                f"Prowlarr search request - Query: '{query}', Category: {category}, Limit: {limit}, Params: {params}"
            )
            category_list = []
            if category:
                if isinstance(category, list):
                    category_list = category
                else:
                    category_list = [category]

            params_with_categories = []

            for key, value in params.items():
                params_with_categories.append((key, value))
            for cat in category_list:
                params_with_categories.append(("categories", cat))
            response = httpx.get(
                url,
                headers=self.headers,
                params=params_with_categories,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            try:
                actual_url = str(response.request.url)
                logger.info(
                    f"Prowlarr search response - Status: {response.status_code}, "
                    f"Actual URL: {actual_url}"
                )
                logger.info(
                    f"Prowlarr request headers: {dict(response.request.headers)}"
                )
            except (AttributeError, RuntimeError):
                pass
            data = response.json()
            logger.info(
                f"Prowlarr search response - Results count: {len(data) if isinstance(data, list) else 'N/A'}"
            )
            if isinstance(data, list) and len(data) > 0:
                logger.info("First 5 results:")
                for i, result in enumerate(data[:5], 1):
                    logger.info(
                        f"  {i}. Title: {result.get('title', 'N/A')}, "
                        f"Indexer: {result.get('indexer', 'N/A')}, "
                        f"Categories: {result.get('categories', 'N/A')}, "
                        f"Protocol: {result.get('protocol', 'N/A')}"
                    )

            results = []
            for item in data:
                try:
                    categories = item.get("categories", [])
                    category_ids = []
                    for cat in categories:
                        if isinstance(cat, dict):
                            cat_id = cat.get("id")
                            if cat_id:
                                category_ids.append(cat_id)
                        elif isinstance(cat, int):
                            category_ids.append(cat)

                    is_valid = False
                    for cat_id in category_ids:
                        if (cat_id >= 7000 and cat_id < 8000) or cat_id == 3030:
                            is_valid = True
                            break

                    if not is_valid:
                        continue

                    results.append(SearchResult.from_dict(item))
                except (KeyError, ValueError):
                    continue

            logger.info(
                f"Filtered to {len(results)} results (categories 7000-7999 or 3030) "
                f"out of {len(data)} total results"
            )
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

    def _extract_guid_from_url(self, guid: str) -> str:
        if "?" in guid and "guid=" in guid:
            parsed = urlparse(guid)
            params = parse_qs(parsed.query)
            if "guid" in params:
                return params["guid"][0]
        return guid

    def get_download_url(self, indexer_id: int, guid: str) -> str:
        from urllib.parse import quote

        extracted_guid = self._extract_guid_from_url(guid)
        guid_to_try = extracted_guid if extracted_guid != guid else guid

        for attempt_guid in [guid_to_try, guid]:
            try:
                url_encoded_guid = quote(attempt_guid, safe="")
                url = f"{self.base_url}/api/v1/download/{indexer_id}/{url_encoded_guid}"
                logger.info(
                    f"Fetching download URL from Prowlarr - indexer_id={indexer_id}, "
                    f"attempt_guid={attempt_guid}, url={url}"
                )
                response = httpx.get(
                    url,
                    headers=self.headers,
                    follow_redirects=False,
                    timeout=self.config.timeout,
                )

                logger.info(
                    f"Prowlarr download response - status={response.status_code}, "
                    f"headers={dict(response.headers)}"
                )

                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if location:
                        logger.info(f"Prowlarr redirected to: {location}")
                        return location
                    raise ProwlarrClientError(
                        "Prowlarr returned redirect but no Location header"
                    )

                if response.status_code == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if (
                        "application/x-nzb" in content_type
                        or "application/octet-stream" in content_type
                    ):
                        raise ProwlarrClientError(
                            "Prowlarr returned NZB file directly instead of redirect. "
                            "This endpoint may not be supported. Try using downloadUrl from search result."
                        )

                response.raise_for_status()
                raise ProwlarrClientError(
                    f"Unexpected response from Prowlarr download endpoint: {response.status_code}"
                )
            except httpx.HTTPStatusError as e:
                error_text = e.response.text if e.response else "No response text"
                if e.response.status_code == 404:
                    if attempt_guid == guid:
                        logger.error(
                            f"Prowlarr download endpoint failed - status=404, "
                            f"indexer_id={indexer_id}, guid={attempt_guid}, error={error_text}"
                        )
                        raise ProwlarrClientError(
                            f"Release not found (indexer_id={indexer_id}, guid={attempt_guid}). "
                            f"Original GUID: {guid}. Error: {error_text}"
                        )
                    logger.warning(
                        f"Failed with extracted GUID, trying original GUID: {guid}"
                    )
                    continue
                if e.response.status_code == 401:
                    raise ProwlarrClientError("Authentication failed - check API key")
                raise ProwlarrClientError(
                    f"HTTP error {e.response.status_code}: {error_text}"
                )
            except httpx.TimeoutException:
                raise ProwlarrClientError(
                    f"Request timeout after {self.config.timeout} seconds"
                )
            except ProwlarrClientError:
                raise
            except Exception as e:
                if attempt_guid == guid:
                    raise ProwlarrClientError(f"Failed to get download URL: {str(e)}")
                logger.warning(
                    f"Failed with extracted GUID, trying original GUID: {guid}"
                )
                continue

        raise ProwlarrClientError(
            "Failed to get download URL after trying both GUID formats"
        )

    def get_indexer_api_key(self, indexer_id: int) -> str | None:
        """Get the API key for a specific indexer."""
        try:
            url = f"{self.base_url}/api/v1/indexer/{indexer_id}"
            response = httpx.get(
                url,
                headers=self.headers,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            data = response.json()

            # Look for API key in fields
            fields = data.get("fields", [])
            for field in fields:
                if field.get("name") == "apiKey":
                    return field.get("value")

            return None
        except Exception as e:
            logger.warning(f"Failed to get API key for indexer {indexer_id}: {e}")
            return None

    def send_to_download_client(self, indexer_id: int, guid: str) -> dict:
        extracted_guid = self._extract_guid_from_url(guid)
        try:
            url = f"{self.base_url}/api/v1/command"
            payload = {
                "name": "DownloadRelease",
                "indexerId": indexer_id,
                "guid": extracted_guid,
            }
            logger.info(
                f"Sending download command - indexer_id={indexer_id}, "
                f"original_guid={guid}, extracted_guid={extracted_guid}, payload={payload}"
            )
            response = httpx.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Download command response: {data}")

            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "message": data.get("message", ""),
                "download_client_id": data.get("body", {}).get("downloadClientId"),
            }
        except httpx.HTTPStatusError as e:
            error_text = e.response.text if e.response else "No response text"
            logger.error(
                f"Download command failed - status={e.response.status_code}, "
                f"indexer_id={indexer_id}, guid={guid}, error={error_text}"
            )
            if e.response.status_code == 401:
                raise ProwlarrClientError("Authentication failed - check API key")
            if e.response.status_code == 404:
                raise ProwlarrClientError(
                    f"Release not found (indexer_id={indexer_id}, guid={guid})"
                )
            if e.response.status_code == 500:
                raise ProwlarrClientError(
                    f"Prowlarr server error - indexer_id={indexer_id}, guid={extracted_guid}. "
                    f"This usually means the indexer is not configured or the release is not available. "
                    f"Error: {error_text}"
                )
            raise ProwlarrClientError(
                f"HTTP error {e.response.status_code}: {error_text}"
            )
        except httpx.TimeoutException:
            raise ProwlarrClientError(
                f"Request timeout after {self.config.timeout} seconds"
            )
        except Exception as e:
            raise ProwlarrClientError(f"Download initiation failed: {str(e)}")
