# Search App - Final Architecture

## Configuration Storage Decision

**Provider Configuration**: Database model (users configure via UI)
**Search Results**: Not stored (live API calls only)
**Metadata Cache**: Not stored (always fresh)

## Models Needed

### SearchProvider (Database Model)
**Purpose**: Store user-configurable provider settings

**Fields**:
- `name` - Display name (e.g., "Google Books")
- `provider_type` - Type enum (google_books, openlibrary, etc.)
- `enabled` - Whether provider is active (user toggle)
- `api_key` - API key (encrypted/stored securely)
- `priority` - Search order (user configurable)
- `rate_limit_per_minute` - Rate limit setting
- `supports_media_types` - ArrayField of supported types
- `config` - JSONField for provider-specific settings
- `last_checked_at` - Last health check
- `last_error` - Last error message

**Why Database**:
- Users configure via UI
- Settings persist across restarts
- Can enable/disable without code changes
- API keys stored securely

## Code Structure

### Directory Layout

```
search/
├── __init__.py
├── models.py              # SearchProvider model only
├── providers/
│   ├── __init__.py
│   ├── base.py           # BaseProvider abstract class
│   ├── google_books.py   # GoogleBooksProvider
│   ├── openlibrary.py    # OpenLibraryProvider
│   ├── mangadex.py       # MangaDexProvider
│   ├── comicvine.py      # ComicVineProvider
│   └── registry.py       # Provider registry/factory
├── normalizers.py        # Normalize metadata formats
├── search.py             # Main search orchestration
└── admin.py              # Django admin for SearchProvider
```

### Base Provider Interface

```python
# search/providers/base.py
from abc import ABC, abstractmethod
from typing import Any

class BaseProvider(ABC):
    """Abstract base class for all metadata providers"""
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url")
        self.enabled = config.get("enabled", True)
    
    @abstractmethod
    def search(self, query: str, media_type: str) -> list[dict[str, Any]]:
        """Search provider and return normalized results"""
        pass
    
    @abstractmethod
    def fetch_by_identifier(
        self, identifier: str, identifier_type: str
    ) -> dict[str, Any] | None:
        """Fetch metadata by identifier (ISBN, etc.)"""
        pass
    
    @abstractmethod
    def normalize_result(self, raw_result: dict[str, Any]) -> dict[str, Any]:
        """Normalize provider-specific format to standard format"""
        pass
    
    def test_connection(self) -> bool:
        """Test if provider is accessible"""
        # Default implementation, can be overridden
        return True
```

### Concrete Provider Implementation

```python
# search/providers/google_books.py
import httpx
from typing import Any

from search.providers.base import BaseProvider

class GoogleBooksProvider(BaseProvider):
    """Google Books API provider"""
    
    def search(self, query: str, media_type: str) -> list[dict[str, Any]]:
        if media_type not in ["book", "audiobook"]:
            return []
        
        url = f"{self.base_url}/volumes"
        params = {"q": query, "key": self.api_key}
        
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        
        results = response.json().get("items", [])
        return [self.normalize_result(r) for r in results]
    
    def fetch_by_identifier(
        self, identifier: str, identifier_type: str
    ) -> dict[str, Any] | None:
        if identifier_type not in ["isbn", "isbn13"]:
            return None
        
        query = f"isbn:{identifier}"
        results = self.search(query, "book")
        return results[0] if results else None
    
    def normalize_result(self, raw_result: dict[str, Any]) -> dict[str, Any]:
        volume_info = raw_result.get("volumeInfo", {})
        return {
            "provider": "google_books",
            "provider_id": raw_result.get("id"),
            "title": volume_info.get("title"),
            "authors": volume_info.get("authors", []),
            "isbn": self._extract_isbn(volume_info),
            "isbn13": self._extract_isbn13(volume_info),
            "description": volume_info.get("description"),
            "publisher": volume_info.get("publisher"),
            "publication_date": volume_info.get("publishedDate"),
            "page_count": volume_info.get("pageCount"),
            "cover_url": self._extract_cover_url(volume_info),
            "language": volume_info.get("language"),
            "genres": volume_info.get("categories", []),
        }
    
    def _extract_isbn(self, volume_info: dict) -> str:
        # Extract ISBN-10 from industryIdentifiers
        pass
    
    def _extract_isbn13(self, volume_info: dict) -> str:
        # Extract ISBN-13 from industryIdentifiers
        pass
    
    def _extract_cover_url(self, volume_info: dict) -> str:
        # Extract cover URL from imageLinks
        pass
```

### Provider Registry

```python
# search/providers/registry.py
from typing import Any

from search.models import SearchProvider
from search.providers.base import BaseProvider
from search.providers.google_books import GoogleBooksProvider
from search.providers.openlibrary import OpenLibraryProvider
# ... other providers

PROVIDER_CLASSES = {
    "google_books": GoogleBooksProvider,
    "openlibrary": OpenLibraryProvider,
    "mangadex": MangaDexProvider,
    "comicvine": ComicVineProvider,
}

def get_provider_instance(provider_model: SearchProvider) -> BaseProvider:
    """Create provider instance from database model"""
    provider_class = PROVIDER_CLASSES.get(provider_model.provider_type)
    if not provider_class:
        raise ValueError(f"Unknown provider type: {provider_model.provider_type}")
    
    config = {
        "api_key": provider_model.api_key,
        "base_url": provider_model.base_url,
        "enabled": provider_model.enabled,
        "rate_limit_per_minute": provider_model.rate_limit_per_minute,
        **provider_model.config,  # Provider-specific config
    }
    
    return provider_class(config)

def get_enabled_providers(media_type: str) -> list[BaseProvider]:
    """Get all enabled providers for a media type"""
    providers = SearchProvider.objects.filter(
        enabled=True,
        supports_media_types__contains=[media_type]
    ).order_by("priority")
    
    return [get_provider_instance(p) for p in providers]
```

### Search Orchestration

```python
# search/search.py
from typing import Any
import asyncio

from search.providers.registry import get_enabled_providers

async def search_providers(
    query: str, media_type: str
) -> list[dict[str, Any]]:
    """
    Search all enabled providers and return normalized, deduplicated results.
    """
    providers = get_enabled_providers(media_type)
    
    # Search all providers in parallel
    tasks = [provider.search(query, media_type) for provider in providers]
    results_lists = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Flatten and deduplicate results
    all_results = []
    for results in results_lists:
        if isinstance(results, Exception):
            # Log error, continue with other providers
            continue
        all_results.extend(results)
    
    # Deduplicate by ISBN or title+author
    deduplicated = deduplicate_results(all_results)
    
    # Rank results
    ranked = rank_results(deduplicated, query)
    
    return ranked

def deduplicate_results(results: list[dict]) -> list[dict]:
    """Remove duplicate results based on ISBN or title+author"""
    seen = set()
    unique = []
    
    for result in results:
        # Try ISBN first
        key = result.get("isbn13") or result.get("isbn")
        if not key:
            # Fall back to title+author
            title = result.get("title", "").lower()
            authors = ",".join(result.get("authors", [])).lower()
            key = f"{title}|{authors}"
        
        if key not in seen:
            seen.add(key)
            unique.append(result)
    
    return unique

def rank_results(results: list[dict], query: str) -> list[dict]:
    """Rank results by relevance"""
    # Simple ranking: exact title match > partial match > other
    # Could be enhanced with more sophisticated scoring
    return sorted(results, key=lambda r: _score_result(r, query), reverse=True)

def _score_result(result: dict, query: str) -> int:
    """Score a result for ranking"""
    title = result.get("title", "").lower()
    query_lower = query.lower()
    
    if title == query_lower:
        return 100
    elif query_lower in title:
        return 50
    else:
        return 0
```

## Django Admin Configuration

```python
# search/admin.py
from django.contrib import admin
from search.models import SearchProvider

@admin.register(SearchProvider)
class SearchProviderAdmin(admin.ModelAdmin):
    list_display = ["name", "provider_type", "enabled", "priority"]
    list_filter = ["provider_type", "enabled"]
    search_fields = ["name"]
    fieldsets = [
        ("Basic", {"fields": ["name", "provider_type", "enabled"]}),
        ("API", {"fields": ["api_key", "base_url"]}),
        ("Settings", {"fields": ["priority", "rate_limit_per_minute", "supports_media_types"]}),
        ("Advanced", {"fields": ["config"], "classes": ["collapse"]}),
    ]
```

## Benefits of This Structure

1. **User Configuration**: Users can enable/disable providers via UI
2. **Extensible**: Easy to add new providers (just add class + register)
3. **Testable**: Each provider is isolated and testable
4. **Type Safe**: Abstract base class enforces interface
5. **No Result Storage**: Results are ephemeral, no database bloat
6. **Parallel Search**: Can search multiple providers simultaneously

## Standard Metadata Format

All providers normalize to this format:

```python
{
    "provider": "google_books",
    "provider_id": "...",
    "title": "...",
    "authors": ["..."],
    "isbn": "...",
    "isbn13": "...",
    "description": "...",
    "publisher": "...",
    "publication_date": "2024-01-01",
    "page_count": 300,
    "cover_url": "...",
    "language": "en",
    "genres": ["..."],
    # Media-type specific fields in nested dict or separate keys
}
```
