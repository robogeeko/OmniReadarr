from __future__ import annotations

import httpx

from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path

from indexers.models import ProwlarrConfiguration


@admin.register(ProwlarrConfiguration)
class ProwlarrConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "host",
        "port",
        "use_ssl",
        "enabled",
        "priority",
        "timeout",
        "created_at",
    ]
    list_filter = [
        "enabled",
        "use_ssl",
        "created_at",
    ]
    search_fields = [
        "name",
        "host",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    change_form_template = "admin/indexers/prowlarrconfiguration/change_form.html"
    fieldsets = (
        (
            "Connection Settings",
            {
                "fields": (
                    "name",
                    "host",
                    "port",
                    "use_ssl",
                    "base_path",
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
                    "timeout",
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

    def save_model(self, request, obj, form, change):
        if not change:
            existing = ProwlarrConfiguration.objects.filter(enabled=True).first()
            if existing:
                from django.contrib import messages

                messages.warning(
                    request,
                    "Only one ProwlarrConfiguration should be enabled. "
                    "Please disable the existing one first.",
                )
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/test-connection/",
                self.admin_site.admin_view(self.test_connection_view),
                name="indexers_prowlarrconfiguration_test_connection",
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
            messages.error(request, "Prowlarr configuration not found")
            return redirect("admin:indexers_prowlarrconfiguration_changelist")

        try:
            protocol = "https" if config.use_ssl else "http"
            base_path = config.base_path.strip("/") if config.base_path else ""
            url = f"{protocol}://{config.host}:{config.port}"
            if base_path:
                url = f"{url}/{base_path}"
            url = f"{url}/api/v1/system/status"

            response = httpx.get(
                url,
                headers={"X-Api-Key": config.api_key},
                timeout=config.timeout,
            )
            response.raise_for_status()

            messages.success(
                request,
                f"✓ {config.name}: Connection successful (Prowlarr version: {response.json().get('version', 'unknown')})",
            )
        except httpx.TimeoutException:
            messages.error(
                request,
                f"✗ {config.name}: Connection timeout after {config.timeout} seconds",
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

        return redirect("admin:indexers_prowlarrconfiguration_change", object_id)
