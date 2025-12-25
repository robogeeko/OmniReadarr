from __future__ import annotations

from django.core.validators import MinValueValidator
from django.db import models

from core.models import BaseModel


class ProwlarrConfiguration(BaseModel):
    name = models.CharField(max_length=100)
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=9696, validators=[MinValueValidator(1)])
    api_key = models.CharField(max_length=255)
    use_ssl = models.BooleanField(default=False)
    base_path = models.CharField(max_length=500, blank=True)
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)
    timeout = models.IntegerField(default=30, validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "Prowlarr Configuration"
        verbose_name_plural = "Prowlarr Configurations"
        ordering = ["priority", "name"]

    def __str__(self) -> str:
        return self.name
