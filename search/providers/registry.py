from __future__ import annotations

from typing import Any

from search.models import ProviderType, SearchProvider
from search.providers.base import BaseProvider
from search.providers.openlibrary import OpenLibraryProvider

PROVIDER_CLASSES: dict[str, type[BaseProvider]] = {
    ProviderType.OPENLIBRARY: OpenLibraryProvider,
}


def get_provider_instance(provider_model: SearchProvider) -> BaseProvider:
    """
    Create provider instance from database model.

    Args:
        provider_model: SearchProvider database model instance

    Returns:
        Provider instance

    Raises:
        ValueError: If provider type is not registered
    """
    provider_class = PROVIDER_CLASSES.get(provider_model.provider_type)
    if not provider_class:
        raise ValueError(f"Unknown provider type: {provider_model.provider_type}")

    config: dict[str, Any] = {
        "api_key": provider_model.api_key,
        "base_url": provider_model.base_url,
        "enabled": provider_model.enabled,
        "rate_limit_per_minute": provider_model.rate_limit_per_minute,
        **provider_model.config,
    }

    return provider_class(config)


def get_enabled_providers(media_type: str) -> list[BaseProvider]:
    """
    Get all enabled providers for a media type.

    Args:
        media_type: Type of media (book, audiobook, manga, comic)

    Returns:
        List of enabled provider instances, ordered by priority
    """
    providers = SearchProvider.objects.filter(
        enabled=True,
        supports_media_types__contains=[media_type],
    ).order_by("priority")

    return [get_provider_instance(p) for p in providers]
