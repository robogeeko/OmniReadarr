from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from indexers.models import ProwlarrConfiguration


@pytest.mark.django_db
class TestProwlarrConfiguration:
    def test_create_prowlarr_configuration(self):
        config = ProwlarrConfiguration.objects.create(
            name="Test Prowlarr",
            host="localhost",
            port=9696,
            api_key="test-api-key",
        )
        assert config.name == "Test Prowlarr"
        assert config.host == "localhost"
        assert config.port == 9696
        assert config.api_key == "test-api-key"
        assert config.use_ssl is False
        assert config.enabled is True
        assert config.priority == 0
        assert config.timeout == 30
        assert config.base_path == ""
        assert str(config) == "Test Prowlarr"

    def test_prowlarr_configuration_defaults(self):
        config = ProwlarrConfiguration.objects.create(
            name="Test",
            host="localhost",
            port=9696,
            api_key="key",
        )
        assert config.use_ssl is False
        assert config.enabled is True
        assert config.priority == 0
        assert config.timeout == 30

    def test_prowlarr_configuration_ordering(self):
        config1 = ProwlarrConfiguration.objects.create(
            name="B Config",
            host="localhost",
            port=9696,
            api_key="key",
            priority=2,
        )
        config2 = ProwlarrConfiguration.objects.create(
            name="A Config",
            host="localhost",
            port=9696,
            api_key="key",
            priority=1,
        )
        configs = list(ProwlarrConfiguration.objects.all())
        assert configs[0] == config2
        assert configs[1] == config1

    def test_prowlarr_configuration_port_validation(self):
        config = ProwlarrConfiguration(
            name="Test",
            host="localhost",
            port=0,
            api_key="key",
        )
        with pytest.raises(ValidationError):
            config.full_clean()
