from __future__ import annotations

from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.db import models

from core.models import Media


class Book(Media):
    isbn = models.CharField(max_length=13, blank=True)
    isbn13 = models.CharField(max_length=13, blank=True)
    page_count = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    edition = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["series", "series_index", "title"]


class Audiobook(Media):
    narrators = ArrayField(
        models.CharField(max_length=200),
        default=list,
        blank=True,
    )
    duration_seconds = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    bitrate = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    chapters = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )

    class Meta:
        ordering = ["series", "series_index", "title"]
