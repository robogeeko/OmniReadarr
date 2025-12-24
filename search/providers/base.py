from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from search.providers.results import NormalizedMetadata


class BaseProvider(ABC):
    """Abstract base class for all metadata providers"""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url")
        self.enabled = config.get("enabled", True)
        self.rate_limit_per_minute = config.get("rate_limit_per_minute", 60)

    @abstractmethod
    def search(
        self, query: str, media_type: str, language: str | None = None
    ) -> list[NormalizedMetadata]:
        """
        Search provider and return normalized results.

        Args:
            query: Search query string
            media_type: Hint for type of media to search for (book, audiobook, manga, comic).
                       Providers should return the appropriate metadata type based on what they
                       actually find, not necessarily what media_type suggests.
            language: Optional language code to filter results (e.g., "en", "eng", "fre")

        Returns:
            List of normalized metadata objects. Each provider should return the appropriate
            metadata type (BookMetadata, AudiobookMetadata, etc.) based on the data available.
            Different providers may return different types for the same search - this is expected.
        """
        pass

    @abstractmethod
    def fetch_by_identifier(
        self, identifier: str, identifier_type: str
    ) -> NormalizedMetadata | None:
        """
        Fetch metadata by identifier (ISBN, OpenLibrary ID, etc.).

        Args:
            identifier: Identifier value (e.g., ISBN, ID)
            identifier_type: Type of identifier (isbn, isbn13, openlibrary_id, etc.)

        Returns:
            Normalized metadata object or None if not found
        """
        pass

    @abstractmethod
    def normalize_result(self, raw_result: dict[str, Any]) -> NormalizedMetadata | None:
        """
        Normalize provider-specific format to standard format.

        Args:
            raw_result: Raw result from provider API

        Returns:
            Normalized metadata object with standard fields, or None if result is invalid
        """
        pass

    def test_connection(self) -> bool:
        """
        Test if provider is accessible.

        Returns:
            True if provider is accessible, False otherwise
        """
        return True
