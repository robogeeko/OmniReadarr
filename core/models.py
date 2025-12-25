from __future__ import annotations

import uuid
from typing import Any

from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class MediaStatus(models.TextChoices):
    WANTED = "wanted", "Wanted"
    SEARCHING = "searching", "Searching"
    DOWNLOADING = "downloading", "Downloading"
    DOWNLOADED = "downloaded", "Downloaded"
    POST_PROCESSED_FAILED = "post_processed_failed", "Post-Processed Failed"
    POST_PROCESSED_SUCCESS = "post_processed_success", "Post-Processed Success"
    ARCHIVED = "archived", "Archived"


class Media(BaseModel):
    title = models.CharField(max_length=500)
    sort_title = models.CharField(max_length=500, blank=True)

    authors = ArrayField(
        models.CharField(max_length=200),
        default=list,
        blank=True,
    )
    series = models.CharField(max_length=300, blank=True)
    series_index = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    publication_date = models.DateField(null=True, blank=True)
    added_date = models.DateTimeField(auto_now_add=True)

    description = models.TextField(blank=True)
    genres = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
    )
    tags = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
    )

    identifiers = models.JSONField(default=dict, blank=True)

    cover_url = models.URLField(max_length=1000, blank=True)
    cover_path = models.CharField(max_length=1000, blank=True)

    language = models.CharField(max_length=10, blank=True)
    publisher = models.CharField(max_length=300, blank=True)

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )

    status = models.CharField(
        max_length=20,
        choices=MediaStatus.choices,
        default=MediaStatus.WANTED,
    )

    provider = models.CharField(max_length=50, blank=True)
    external_id = models.CharField(max_length=500, blank=True)

    class Meta:
        abstract = True
        ordering = ["sort_title", "title"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["series", "series_index"]),
            models.Index(fields=["added_date"]),
            models.Index(fields=["language"]),
            models.Index(fields=["publisher"]),
            models.Index(fields=["provider", "external_id"]),
        ]

    def __str__(self) -> str:
        return str(self.title)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.sort_title:
            self.sort_title = self.title
        super().save(*args, **kwargs)
