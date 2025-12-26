from __future__ import annotations

from django.db import models

from core.models import BaseModel


class ProcessingConfiguration(BaseModel):
    name = models.CharField(max_length=100, default="Default Configuration")
    completed_downloads_path = models.CharField(max_length=500)
    library_base_path = models.CharField(max_length=500)
    calibre_ebook_convert_path = models.CharField(
        max_length=500, blank=True, default="ebook-convert"
    )
    enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Processing Configuration"
        verbose_name_plural = "Processing Configurations"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

