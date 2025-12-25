from __future__ import annotations

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator
from django.db import models

from core.models import BaseModel


class ClientType(models.TextChoices):
    SABNZBD = "sabnzbd", "SABnzbd"


class DownloadClientConfiguration(BaseModel):
    name = models.CharField(max_length=100)
    client_type = models.CharField(
        max_length=20,
        choices=ClientType.choices,
        default=ClientType.SABNZBD,
    )
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=8080, validators=[MinValueValidator(1)])
    use_ssl = models.BooleanField(default=False)
    api_key = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Download Client Configuration"
        verbose_name_plural = "Download Client Configurations"
        ordering = ["priority", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_client_type_display()})"  # type: ignore[attr-defined]


class DownloadAttemptStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    DOWNLOADING = "downloading", "Downloading"
    DOWNLOADED = "downloaded", "Downloaded"
    FAILED = "failed", "Failed"
    BLACKLISTED = "blacklisted", "Blacklisted"


class PostProcessStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class BlacklistReason(models.TextChoices):
    FAILED_DOWNLOAD = "failed_download", "Failed Download"
    WRONG_FILE = "wrong_file", "Wrong File"
    CORRUPTED = "corrupted", "Corrupted"
    LOW_QUALITY = "low_quality", "Low Quality"
    MANUAL = "manual", "Manual"


class DownloadAttempt(BaseModel):
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={"model__in": ("book", "audiobook")},
    )
    object_id = models.UUIDField()
    media = GenericForeignKey("content_type", "object_id")
    indexer = models.CharField(max_length=100)
    indexer_id = models.CharField(max_length=100)
    release_title = models.CharField(max_length=500)
    download_url = models.CharField(max_length=1000)
    file_size = models.BigIntegerField(null=True, blank=True)
    seeders = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    leechers = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    attempted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=DownloadAttemptStatus.choices,
        default=DownloadAttemptStatus.PENDING,
    )
    error_type = models.CharField(max_length=50, blank=True)
    error_reason = models.TextField(blank=True)
    download_client = models.ForeignKey(
        DownloadClientConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="download_attempts",
    )
    download_client_download_id = models.CharField(max_length=100, blank=True)
    raw_file_path = models.CharField(max_length=1000, blank=True)
    post_processed_file_path = models.CharField(max_length=1000, blank=True)
    post_process_status = models.CharField(
        max_length=50,
        choices=PostProcessStatus.choices,
        blank=True,
    )
    post_process_error_type = models.CharField(max_length=50, blank=True)
    post_process_error_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Download Attempt"
        verbose_name_plural = "Download Attempts"
        ordering = ["-attempted_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id", "status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["attempted_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.release_title} ({self.get_status_display()})"  # type: ignore[attr-defined]


class DownloadBlacklist(BaseModel):
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={"model__in": ("book", "audiobook")},
    )
    object_id = models.UUIDField()
    media = GenericForeignKey("content_type", "object_id")
    indexer = models.CharField(max_length=100)
    indexer_id = models.CharField(max_length=100)
    release_title = models.CharField(max_length=500)
    download_url = models.CharField(max_length=1000)
    reason = models.CharField(
        max_length=20,
        choices=BlacklistReason.choices,
    )
    reason_details = models.TextField(blank=True)
    blacklisted_at = models.DateTimeField(auto_now_add=True)
    blacklisted_by = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Download Blacklist"
        verbose_name_plural = "Download Blacklist"
        ordering = ["-blacklisted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id", "indexer", "indexer_id"],
                name="unique_blacklist_entry",
            ),
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["blacklisted_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.release_title} ({self.get_reason_display()})"  # type: ignore[attr-defined]
