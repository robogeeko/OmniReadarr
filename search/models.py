from __future__ import annotations

from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.db import models

from core.models import BaseModel


class ProviderType(models.TextChoices):
    GOOGLE_BOOKS = "google_books", "Google Books"
    OPENLIBRARY = "openlibrary", "OpenLibrary"
    MANGADEX = "mangadex", "MangaDex"
    COMICVINE = "comicvine", "ComicVine"
    GOODREADS = "goodreads", "Goodreads"
    ANILIST = "anilist", "AniList"


class SearchProvider(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    provider_type = models.CharField(
        max_length=50,
        choices=ProviderType.choices,
    )
    enabled = models.BooleanField(default=True)
    api_key = models.CharField(max_length=500, blank=True)
    base_url = models.URLField(max_length=500)
    priority = models.IntegerField(default=0)
    rate_limit_per_minute = models.IntegerField(
        default=60, validators=[MinValueValidator(1)]
    )
    supports_media_types = ArrayField(
        models.CharField(max_length=20),
        default=list,
        blank=True,
    )
    config = models.JSONField(default=dict, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        ordering = ["priority", "name"]
        indexes = [
            models.Index(fields=["provider_type", "enabled"]),
            models.Index(fields=["enabled", "priority"]),
        ]

    def __str__(self) -> str:
        return str(self.name)
