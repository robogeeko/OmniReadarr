from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SearchResult:
    guid: str
    title: str
    indexer: str
    indexer_id: int
    size: int | None
    publish_date: datetime | None
    seeders: int | None
    peers: int | None
    protocol: str
    download_url: str
    info_url: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> SearchResult:
        publish_date = None
        if data.get("publishDate"):
            try:
                publish_date = datetime.fromisoformat(
                    data["publishDate"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        return cls(
            guid=data["guid"],
            title=data["title"],
            indexer=data["indexer"],
            indexer_id=data["indexerId"],
            size=data.get("size"),
            publish_date=publish_date,
            seeders=data.get("seeders"),
            peers=data.get("peers"),
            protocol=data.get("protocol", "unknown"),
            download_url=data.get("downloadUrl", ""),
            info_url=data.get("infoUrl"),
        )


@dataclass
class IndexerCapabilities:
    supports_rss: bool
    supports_search: bool
    supports_query: bool
    supports_book_search: bool
    categories: list[int]

    @classmethod
    def from_dict(cls, data: dict) -> IndexerCapabilities:
        return cls(
            supports_rss=data.get("supportsRss", False),
            supports_search=data.get("supportsSearch", False),
            supports_query=data.get("supportsQuery", False),
            supports_book_search=data.get("supportsBookSearch", False),
            categories=data.get("categories", []),
        )


@dataclass
class IndexerInfo:
    id: int
    name: str
    protocol: str
    capabilities: IndexerCapabilities
    enabled: bool

    @classmethod
    def from_dict(cls, data: dict) -> IndexerInfo:
        return cls(
            id=data["id"],
            name=data["name"],
            protocol=data.get("protocol", "unknown"),
            capabilities=IndexerCapabilities.from_dict(data),
            enabled=data.get("enabled", True),
        )

