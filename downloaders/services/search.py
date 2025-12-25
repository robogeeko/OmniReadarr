from __future__ import annotations

import logging

from django.contrib.contenttypes.models import ContentType

from core.models import Media
from downloaders.models import DownloadBlacklist
from indexers.prowlarr.client import ProwlarrClient
from indexers.prowlarr.results import SearchResult
from media.models import Audiobook, Book

logger = logging.getLogger(__name__)


class SearchServiceError(Exception):
    pass


class SearchService:
    def __init__(self, prowlarr_client: ProwlarrClient | None = None):
        if prowlarr_client is None:
            prowlarr_client = ProwlarrClient()
        self.prowlarr_client = prowlarr_client

    def _get_category_for_media(self, media: Media) -> int:
        if isinstance(media, Audiobook):
            return 3030
        elif isinstance(media, Book):
            return 7020
        else:
            raise Exception("Invalid media type")

    def search_for_media(self, media: Media) -> list[SearchResult]:
        all_results: list[tuple[SearchResult, int]] = []

        queries = self._build_search_queries(media)
        category = self._get_category_for_media(media)
        media_type = "audiobook" if isinstance(media, Audiobook) else "book"

        logger.info(
            f"Searching for {media_type}: {media.title} (ID: {media.id}). "
            f"Built {len(queries)} queries: {queries}, Category: {category}"
        )

        for query, priority in queries:
            try:
                logger.info(
                    f"Executing search query (priority {priority}): '{query}' "
                    f"for {media_type}: {media.title}"
                )
                results = self.prowlarr_client.search(
                    query=str(query),
                    category=category,
                    limit=50,
                )
                logger.info(f"Query '{query}' returned {len(results)} results")
                for result in results:
                    all_results.append((result, priority))  # type: ignore[arg-type]
            except Exception as e:
                logger.warning(
                    f"Search query '{query}' failed: {str(e)}",
                    exc_info=True,
                )
                continue

        deduplicated = self._deduplicate_results(all_results)
        filtered = self._filter_blacklisted(media, deduplicated)
        sorted_results = self._sort_results(filtered)

        return sorted_results[:50]

    def _build_search_queries(self, media: Media) -> list[tuple[str, int]]:
        title = media.title.strip()
        return [(title, 0)]

    def _deduplicate_results(
        self, results: list[tuple[SearchResult, int]]
    ) -> list[tuple[SearchResult, int]]:
        seen_guids: set[str] = set()
        deduplicated: list[tuple[SearchResult, int]] = []

        for result, priority in results:
            if result.guid not in seen_guids:
                seen_guids.add(result.guid)
                deduplicated.append((result, priority))

        return deduplicated

    def _filter_blacklisted(
        self, media: Media, results: list[tuple[SearchResult, int]]
    ) -> list[tuple[SearchResult, int]]:
        filtered = []
        for result, priority in results:
            if not self.is_blacklisted(media, result):
                filtered.append((result, priority))

        return filtered

    def is_blacklisted(self, media: Media, release: SearchResult) -> bool:
        content_type = ContentType.objects.get_for_model(media)

        return DownloadBlacklist.objects.filter(
            content_type=content_type,
            object_id=media.id,
            indexer=release.indexer,
            indexer_id=str(release.indexer_id),
        ).exists()

    def _sort_results(
        self, results: list[tuple[SearchResult, int]]
    ) -> list[SearchResult]:
        sorted_results = sorted(
            results, key=lambda x: (x[1], x[0].indexer.lower(), x[0].title.lower())
        )
        return [result for result, _ in sorted_results]
