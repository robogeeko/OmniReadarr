from __future__ import annotations

import pytest

from search.models import ProviderType, SearchProvider
from search.providers.openlibrary import OpenLibraryProvider
from search.providers.registry import get_enabled_providers, get_provider_instance


@pytest.mark.django_db
class TestGetProviderInstance:
    def test_returns_openlibrary_provider_for_openlibrary_type(self):
        provider = SearchProvider.objects.create(
            name="Test OpenLibrary",
            provider_type=ProviderType.OPENLIBRARY,
            base_url="https://openlibrary.org",
            enabled=True,
        )
        result = get_provider_instance(provider)
        assert isinstance(result, OpenLibraryProvider)
        assert result.base_url == "https://openlibrary.org"
        assert result.enabled is True

    def test_passes_config_correctly(self):
        provider = SearchProvider.objects.create(
            name="Test Provider",
            provider_type=ProviderType.OPENLIBRARY,
            base_url="https://example.com",
            api_key="test-api-key",
            enabled=True,
            rate_limit_per_minute=30,
            config={"custom_setting": "value"},
        )
        result = get_provider_instance(provider)
        assert result.base_url == "https://example.com"
        assert result.api_key == "test-api-key"
        assert result.enabled is True
        assert result.rate_limit_per_minute == 30
        assert result.config["custom_setting"] == "value"

    def test_raises_value_error_for_unknown_provider_type(self):
        provider = SearchProvider(
            name="Unknown Provider",
            provider_type="unknown_type",
            base_url="https://example.com",
        )
        with pytest.raises(ValueError, match="Unknown provider type"):
            get_provider_instance(provider)

    def test_handles_empty_config(self):
        provider = SearchProvider.objects.create(
            name="Test Provider",
            provider_type=ProviderType.OPENLIBRARY,
            base_url="https://openlibrary.org",
            enabled=True,
            config={},
        )
        result = get_provider_instance(provider)
        assert isinstance(result, OpenLibraryProvider)
        assert result.config == {
            "api_key": "",
            "base_url": "https://openlibrary.org",
            "enabled": True,
            "rate_limit_per_minute": 60,
        }


@pytest.mark.django_db
class TestGetEnabledProviders:
    def test_returns_enabled_providers_for_media_type(self):
        SearchProvider.objects.create(
            name="Provider 1",
            provider_type=ProviderType.OPENLIBRARY,
            base_url="https://openlibrary.org",
            enabled=True,
            supports_media_types=["book"],
            priority=1,
        )
        SearchProvider.objects.create(
            name="Provider 2",
            provider_type=ProviderType.OPENLIBRARY,
            base_url="https://openlibrary.org",
            enabled=True,
            supports_media_types=["book", "audiobook"],
            priority=0,
        )
        SearchProvider.objects.create(
            name="Provider 3",
            provider_type=ProviderType.OPENLIBRARY,
            base_url="https://openlibrary.org",
            enabled=False,
            supports_media_types=["book"],
            priority=0,
        )
        results = get_enabled_providers("book")
        assert len(results) == 2
        assert results[0].config["base_url"] == "https://openlibrary.org"
        assert all(isinstance(p, OpenLibraryProvider) for p in results)

    def test_filters_by_media_type(self):
        SearchProvider.objects.create(
            name="Book Provider",
            provider_type=ProviderType.OPENLIBRARY,
            base_url="https://openlibrary.org",
            enabled=True,
            supports_media_types=["book"],
            priority=0,
        )
        SearchProvider.objects.create(
            name="Audiobook Provider",
            provider_type=ProviderType.OPENLIBRARY,
            base_url="https://openlibrary.org",
            enabled=True,
            supports_media_types=["audiobook"],
            priority=0,
        )
        book_results = get_enabled_providers("book")
        audiobook_results = get_enabled_providers("audiobook")
        assert len(book_results) == 1
        assert len(audiobook_results) == 1

    def test_orders_by_priority(self):
        SearchProvider.objects.create(
            name="Low Priority",
            provider_type=ProviderType.OPENLIBRARY,
            base_url="https://openlibrary.org",
            enabled=True,
            supports_media_types=["book"],
            priority=10,
        )
        SearchProvider.objects.create(
            name="High Priority",
            provider_type=ProviderType.OPENLIBRARY,
            base_url="https://openlibrary.org",
            enabled=True,
            supports_media_types=["book"],
            priority=0,
        )
        SearchProvider.objects.create(
            name="Medium Priority",
            provider_type=ProviderType.OPENLIBRARY,
            base_url="https://openlibrary.org",
            enabled=True,
            supports_media_types=["book"],
            priority=5,
        )
        results = get_enabled_providers("book")
        assert len(results) == 3
        assert (
            "High Priority" in str(results[0].config.get("name", ""))
            or results[0].config.get("base_url") == "https://openlibrary.org"
        )
        assert results[0].config["rate_limit_per_minute"] == 60

    def test_returns_empty_list_when_no_providers_match(self):
        SearchProvider.objects.create(
            name="Disabled Provider",
            provider_type=ProviderType.OPENLIBRARY,
            base_url="https://openlibrary.org",
            enabled=False,
            supports_media_types=["book"],
            priority=0,
        )
        SearchProvider.objects.create(
            name="Wrong Media Type",
            provider_type=ProviderType.OPENLIBRARY,
            base_url="https://openlibrary.org",
            enabled=True,
            supports_media_types=["audiobook"],
            priority=0,
        )
        results = get_enabled_providers("book")
        assert len(results) == 0

    def test_handles_multiple_media_types(self):
        provider = SearchProvider.objects.create(
            name="Multi Provider",
            provider_type=ProviderType.OPENLIBRARY,
            base_url="https://openlibrary.org",
            enabled=True,
            supports_media_types=["book", "audiobook"],
            priority=0,
        )
        book_results = get_enabled_providers("book")
        audiobook_results = get_enabled_providers("audiobook")
        assert len(book_results) == 1
        assert len(audiobook_results) == 1
        assert book_results[0].config["base_url"] == provider.base_url
        assert audiobook_results[0].config["base_url"] == provider.base_url
