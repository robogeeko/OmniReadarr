from __future__ import annotations

from django.contrib.contenttypes.models import ContentType

from core.models import Media
from downloaders.models import DownloadBlacklist
from indexers.prowlarr.client import ProwlarrClient
from indexers.prowlarr.results import SearchResult


class SearchServiceError(Exception):
    pass


class SearchService:
    def __init__(self, prowlarr_client: ProwlarrClient | None = None):
        if prowlarr_client is None:
            prowlarr_client = ProwlarrClient()
        self.prowlarr_client = prowlarr_client

    def search_for_media(self, media: Media) -> list[SearchResult]:
        all_results: list[tuple[SearchResult, int]] = []

        queries = self._build_search_queries(media)

        for priority, query in queries:
            try:
                results = self.prowlarr_client.search(
                    query=query,
                    category=7000,
                    limit=50,
                )
                for result in results:
                    all_results.append((result, priority))
            except Exception:
                continue

        deduplicated = self._deduplicate_results(all_results)
        filtered = self._filter_blacklisted(media, deduplicated)
        sorted_results = self._sort_results(filtered)

        return sorted_results[:50]

    def _build_search_queries(self, media: Media) -> list[tuple[str, int]]:
        queries: list[tuple[str, int]] = []

        title = media.title.strip()
        authors = [a.strip() for a in media.authors if a.strip()]

        if title and authors:
            author_str = " ".join(authors[:2])
            queries.append((f"{title} {author_str}", 1))
            queries.append((f"{author_str} {title}", 2))

        if title:
            queries.append((title, 3))

        if hasattr(media, "isbn") and media.isbn:
            queries.append((media.isbn, 0))

        if hasattr(media, "isbn13") and media.isbn13:
            queries.append((media.isbn13, 0))

        return queries

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
