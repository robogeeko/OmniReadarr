from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from search.providers.base import BaseProvider
from search.providers.results import BookMetadata, NormalizedMetadata


class OpenLibraryProvider(BaseProvider):
    """OpenLibrary API provider"""

    def search(
        self, query: str, media_type: str, language: str | None = None
    ) -> list[NormalizedMetadata]:
        """
        Search OpenLibrary for books.

        Args:
            query: Search query string
            media_type: Type of media (book or audiobook)
            language: Optional language code to filter results (e.g., "en", "eng")

        Returns:
            List of normalized BookMetadata objects
        """
        if media_type not in ["book", "audiobook"]:
            return []

        url = f"{self.base_url}/search.json"
        params = {"q": query, "limit": 50}

        try:
            response = httpx.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            results = []
            for doc in data.get("docs", []):
                normalized = self.normalize_result(doc)
                if normalized:
                    if language:
                        normalized_lang = normalized.language.lower()
                        language_map = {
                            "en": ["eng", "en", "english"],
                            "fr": ["fre", "fr", "french"],
                            "de": ["ger", "de", "german"],
                            "es": ["spa", "es", "spanish"],
                            "it": ["ita", "it", "italian"],
                        }
                        target_langs = language_map.get(
                            language.lower(), [language.lower()]
                        )
                        if normalized_lang and not any(
                            target_lang in normalized_lang
                            or normalized_lang in target_lang
                            for target_lang in target_langs
                        ):
                            continue
                    results.append(normalized)
                    if len(results) >= 20:
                        break

            return results
        except httpx.HTTPError:
            return []

    def fetch_by_identifier(
        self, identifier: str, identifier_type: str
    ) -> NormalizedMetadata | None:
        """
        Fetch book metadata by ISBN or OpenLibrary ID.

        Args:
            identifier: ISBN or OpenLibrary ID
            identifier_type: Type of identifier (isbn, isbn13, openlibrary_id)

        Returns:
            Normalized BookMetadata or None if not found
        """
        if identifier_type == "openlibrary_id":
            url = f"{self.base_url}/works/{identifier}.json"
            try:
                response = httpx.get(url, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return self.normalize_result(data)
            except httpx.HTTPError:
                return None

        elif identifier_type in ["isbn", "isbn13"]:
            query = f"isbn:{identifier}"
            results = self.search(query, "book", language=None)
            return results[0] if results else None

        return None

    def normalize_result(self, raw_result: dict[str, Any]) -> NormalizedMetadata | None:
        """
        Normalize OpenLibrary result to BookMetadata.

        Args:
            raw_result: Raw result from OpenLibrary API

        Returns:
            Normalized BookMetadata object
        """
        title = raw_result.get("title", "")
        if not title:
            return None

        provider_id = (
            raw_result.get("key", "").replace("/works/", "").replace("/books/", "")
        )

        authors = []
        if "author_name" in raw_result:
            authors = raw_result["author_name"]
        elif "authors" in raw_result:
            authors = [
                author.get("name", "") if isinstance(author, dict) else str(author)
                for author in raw_result["authors"]
            ]

        isbn_list = raw_result.get("isbn", [])
        isbn = ""
        isbn13 = ""
        for isbn_val in isbn_list:
            isbn_str = str(isbn_val)
            if len(isbn_str) == 10:
                isbn = isbn_str
            elif len(isbn_str) == 13:
                isbn13 = isbn_str

        publication_date = None
        publish_date = raw_result.get("first_publish_year") or raw_result.get(
            "publish_date", []
        )
        if publish_date:
            if isinstance(publish_date, list) and publish_date:
                publish_date = publish_date[0]
            if isinstance(publish_date, str):
                try:
                    year = int(publish_date.split("-")[0])
                    publication_date = date(year, 1, 1)
                except (ValueError, IndexError):
                    pass
            elif isinstance(publish_date, int):
                publication_date = date(publish_date, 1, 1)

        cover_url = ""
        cover_id = raw_result.get("cover_i")
        if cover_id:
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

        page_count = raw_result.get("number_of_pages_median") or raw_result.get(
            "number_of_pages"
        )

        publisher_list = raw_result.get("publisher", [])
        publisher = publisher_list[0] if publisher_list else ""

        language_list = raw_result.get("language", [])
        language = language_list[0] if language_list else ""

        description = ""
        if "first_sentence" in raw_result:
            first_sentence = raw_result["first_sentence"]
            if isinstance(first_sentence, list):
                description = " ".join(first_sentence)
            else:
                description = str(first_sentence)

        subjects = raw_result.get("subject", [])
        genres = subjects[:5] if subjects else []

        return BookMetadata(
            provider="openlibrary",
            provider_id=provider_id,
            title=title,
            authors=authors,
            isbn=isbn,
            isbn13=isbn13,
            description=description,
            publisher=publisher,
            publication_date=publication_date,
            page_count=page_count,
            cover_url=cover_url,
            language=language,
            genres=genres,
        )

    def test_connection(self) -> bool:
        """Test if OpenLibrary is accessible"""
        try:
            response = httpx.get(
                f"{self.base_url}/search.json", params={"q": "test"}, timeout=5.0
            )
            return response.status_code == 200
        except httpx.HTTPError:
            return False
