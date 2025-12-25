from __future__ import annotations

import httpx

from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path

from downloaders.models import (
    DownloadAttempt,
    DownloadBlacklist,
    DownloadClientConfiguration,
)


@admin.register(DownloadAttempt)
class DownloadAttemptAdmin(admin.ModelAdmin):
    list_display = [
        "release_title",
        "media",
        "indexer",
        "status",
        "download_client",
        "attempted_at",
        "file_size",
    ]
    list_filter = [
        "status",
        "indexer",
        "download_client",
        "attempted_at",
        "post_process_status",
    ]
    search_fields = [
        "release_title",
        "indexer",
        "download_client_download_id",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "attempted_at",
    ]
    fieldsets = (
        (
            "Download Information",
            {
                "fields": (
                    "content_type",
                    "object_id",
                    "release_title",
                    "download_url",
                    "indexer",
                    "indexer_id",
                )
            },
        ),
        (
            "File Details",
            {
                "fields": (
                    "file_size",
                    "seeders",
                    "leechers",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "status",
                    "attempted_at",
                    "error_type",
                    "error_reason",
                )
            },
        ),
        (
            "Download Client",
            {
                "fields": (
                    "download_client",
                    "download_client_download_id",
                )
            },
        ),
        (
            "File Paths",
            {
                "fields": (
                    "raw_file_path",
                    "post_processed_file_path",
                )
            },
        ),
        (
            "Post-Processing",
            {
                "fields": (
                    "post_process_status",
                    "post_process_error_type",
                    "post_process_error_reason",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(DownloadBlacklist)
class DownloadBlacklistAdmin(admin.ModelAdmin):
    list_display = [
        "release_title",
        "content_type",
        "object_id",
        "indexer",
        "reason",
        "blacklisted_by",
        "blacklisted_at",
    ]
    list_filter = [
        "reason",
        "indexer",
        "blacklisted_by",
        "blacklisted_at",
    ]
    search_fields = [
        "release_title",
        "indexer",
        "reason_details",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "blacklisted_at",
    ]
    fieldsets = (
        (
            "Blacklist Information",
            {
                "fields": (
                    "content_type",
                    "object_id",
                    "release_title",
                    "download_url",
                    "indexer",
                    "indexer_id",
                )
            },
        ),
        (
            "Reason",
            {
                "fields": (
                    "reason",
                    "reason_details",
                    "blacklisted_by",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "id",
                    "blacklisted_at",
                    "created_at",
                )
            },
        ),
    )


@admin.register(DownloadClientConfiguration)
class DownloadClientConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "client_type",
        "host",
        "port",
        "use_ssl",
        "enabled",
        "priority",
        "created_at",
    ]
    list_filter = [
        "client_type",
        "enabled",
        "use_ssl",
        "created_at",
    ]
    search_fields = [
        "name",
        "host",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    change_form_template = (
        "admin/downloaders/downloadclientconfiguration/change_form.html"
    )
    fieldsets = (
        (
            "Connection Settings",
            {
                "fields": (
                    "name",
                    "client_type",
                    "host",
                    "port",
                    "use_ssl",
                    "api_key",
                )
            },
        ),
        (
            "Configuration",
            {
                "fields": (
                    "enabled",
                    "priority",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/test-connection/",
                self.admin_site.admin_view(self.test_connection_view),
                name="downloaders_downloadclientconfiguration_test_connection",
            ),
        ]
        return custom_urls + urls

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if object_id:
            extra_context["show_test_button"] = True
        return super().changeform_view(request, object_id, form_url, extra_context)

    def test_connection_view(self, request, object_id):
        config = self.get_object(request, object_id)
        if config is None:
            messages.error(request, "Download client configuration not found")
            return redirect("admin:downloaders_downloadclientconfiguration_changelist")

        try:
            if config.client_type != "sabnzbd":
                messages.error(
                    request,
                    f"✗ {config.name}: Connection testing only supported for SABnzbd",
                )
                return redirect(
                    "admin:downloaders_downloadclientconfiguration_change", object_id
                )

            protocol = "https" if config.use_ssl else "http"
            url = f"{protocol}://{config.host}:{config.port}/api?mode=version&apikey={config.api_key}"

            response = httpx.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            version = data.get("version", "unknown")

            messages.success(
                request,
                f"✓ {config.name}: Connection successful (SABnzbd version: {version})",
            )
        except httpx.TimeoutException:
            messages.error(
                request,
                f"✗ {config.name}: Connection timeout",
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                messages.error(
                    request,
                    f"✗ {config.name}: Authentication failed - check your API key",
                )
            else:
                messages.error(
                    request,
                    f"✗ {config.name}: HTTP error {e.response.status_code}",
                )
        except Exception as e:
            messages.error(request, f"✗ {config.name}: {str(e)}")

        return redirect(
            "admin:downloaders_downloadclientconfiguration_change", object_id
        )
