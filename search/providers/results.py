from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from datetime import date


@dataclass
class BaseNormalizedMetadata(ABC):
    """Base class for normalized metadata - common fields for all media types"""

    provider: str
    provider_id: str
    title: str
    authors: list[str] = field(default_factory=list)
    description: str = ""
    publisher: str = ""
    publication_date: date | None = None
    cover_url: str = ""
    language: str = ""
    genres: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        result = {
            "provider": self.provider,
            "provider_id": self.provider_id,
            "title": self.title,
            "authors": self.authors,
            "description": self.description,
            "publisher": self.publisher,
            "publication_date": (
                self.publication_date.isoformat() if self.publication_date else None
            ),
            "cover_url": self.cover_url,
            "language": self.language,
            "genres": self.genres,
            "tags": self.tags,
        }
        return result


@dataclass
class BookMetadata(BaseNormalizedMetadata):
    """Normalized metadata for books and audiobooks"""

    isbn: str = ""
    isbn13: str = ""
    page_count: int | None = None
    edition: str = ""
    narrators: list[str] = field(default_factory=list)
    duration_seconds: int | None = None
    bitrate: int | None = None
    chapters: int | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        result = super().to_dict()
        result.update(
            {
                "isbn": self.isbn,
                "isbn13": self.isbn13,
                "page_count": self.page_count,
                "edition": self.edition,
                "narrators": self.narrators,
                "duration_seconds": self.duration_seconds,
                "bitrate": self.bitrate,
                "chapters": self.chapters,
            }
        )
        return result

    @classmethod
    def from_dict(cls, data: dict) -> BookMetadata:
        """Create from dictionary"""
        publication_date = None
        if data.get("publication_date"):
            if isinstance(data["publication_date"], str):
                publication_date = date.fromisoformat(data["publication_date"])
            elif isinstance(data["publication_date"], date):
                publication_date = data["publication_date"]

        return cls(
            provider=data.get("provider", ""),
            provider_id=data.get("provider_id", ""),
            title=data.get("title", ""),
            authors=data.get("authors", []),
            description=data.get("description", ""),
            publisher=data.get("publisher", ""),
            publication_date=publication_date,
            cover_url=data.get("cover_url", ""),
            language=data.get("language", ""),
            genres=data.get("genres", []),
            tags=data.get("tags", []),
            isbn=data.get("isbn", ""),
            isbn13=data.get("isbn13", ""),
            page_count=data.get("page_count"),
            edition=data.get("edition", ""),
            narrators=data.get("narrators", []),
            duration_seconds=data.get("duration_seconds"),
            bitrate=data.get("bitrate"),
            chapters=data.get("chapters"),
        )


NormalizedMetadata = BookMetadata
