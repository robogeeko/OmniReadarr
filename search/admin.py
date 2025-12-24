from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import path
from django.utils import timezone

from search.models import ProviderType, SearchProvider
from search.providers.registry import get_provider_instance


@admin.register(SearchProvider)
class SearchProviderAdmin(admin.ModelAdmin):
    list_display = ["name", "provider_type", "enabled", "priority", "last_checked_at"]
    list_filter = ["provider_type", "enabled"]
    search_fields = ["name"]
    readonly_fields = ["last_checked_at", "last_error", "created_at", "updated_at"]
    actions = ["test_connection", "test_search"]
    change_form_template = "admin/search/searchprovider/change_form.html"

    fieldsets = [
        (
            "Basic",
            {
                "fields": ["name", "provider_type", "enabled"],
            },
        ),
        (
            "API Configuration",
            {
                "fields": ["api_key", "base_url"],
            },
        ),
        (
            "Settings",
            {
                "fields": [
                    "priority",
                    "rate_limit_per_minute",
                    "supports_media_types",
                ],
            },
        ),
        (
            "Advanced",
            {
                "fields": ["config"],
                "classes": ["collapse"],
            },
        ),
        (
            "Status",
            {
                "fields": ["last_checked_at", "last_error", "created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    def save_model(self, request, obj, form, change):
        if not change:
            if obj.provider_type == ProviderType.OPENLIBRARY:
                if not obj.base_url:
                    obj.base_url = "https://openlibrary.org"
                if not obj.supports_media_types:
                    obj.supports_media_types = ["book", "audiobook"]
        super().save_model(request, obj, form, change)

    @admin.action(description="Test connection for selected providers")
    def test_connection(self, request, queryset):
        for provider in queryset:
            try:
                provider_instance = get_provider_instance(provider)
                if provider_instance.test_connection():
                    provider.last_checked_at = timezone.now()
                    provider.last_error = ""
                    provider.save(update_fields=["last_checked_at", "last_error"])
                    self.message_user(
                        request,
                        f"✓ {provider.name}: Connection successful",
                        messages.SUCCESS,
                    )
                else:
                    provider.last_error = "Connection test failed"
                    provider.save(update_fields=["last_error"])
                    self.message_user(
                        request,
                        f"✗ {provider.name}: Connection test failed",
                        messages.ERROR,
                    )
            except Exception as e:
                provider.last_error = str(e)
                provider.save(update_fields=["last_error"])
                self.message_user(
                    request,
                    f"✗ {provider.name}: {str(e)}",
                    messages.ERROR,
                )

    @admin.action(description="Test search for selected providers")
    def test_search(self, request, queryset):
        test_query = "python programming"
        test_media_type = "book"

        for provider in queryset:
            try:
                provider_instance = get_provider_instance(provider)
                results = provider_instance.search(
                    test_query, test_media_type, language=None, title=None, author=None
                )

                provider.last_checked_at = timezone.now()
                provider.last_error = ""
                provider.save(update_fields=["last_checked_at", "last_error"])

                if results:
                    result_preview = results[0]
                    self.message_user(
                        request,
                        f"✓ {provider.name}: Found {len(results)} results. "
                        f"First result: '{result_preview.title}' by {', '.join(result_preview.authors) if result_preview.authors else 'Unknown'}",
                        messages.SUCCESS,
                    )
                else:
                    self.message_user(
                        request,
                        f"⚠ {provider.name}: Search successful but no results found",
                        messages.WARNING,
                    )
            except Exception as e:
                provider.last_error = str(e)
                provider.save(update_fields=["last_error"])
                self.message_user(
                    request,
                    f"✗ {provider.name}: {str(e)}",
                    messages.ERROR,
                )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/test-connection/",
                self.admin_site.admin_view(self.test_connection_view),
                name="search_searchprovider_test_connection",
            ),
            path(
                "<path:object_id>/test-search/",
                self.admin_site.admin_view(self.test_search_view),
                name="search_searchprovider_test_search",
            ),
        ]
        return custom_urls + urls

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if object_id:
            extra_context["show_test_buttons"] = True
        return super().changeform_view(request, object_id, form_url, extra_context)

    def test_connection_view(self, request, object_id):
        provider = self.get_object(request, object_id)
        if provider is None:
            messages.error(request, "Provider not found")
            return redirect("admin:search_searchprovider_changelist")

        try:
            provider_instance = get_provider_instance(provider)
            if provider_instance.test_connection():
                provider.last_checked_at = timezone.now()
                provider.last_error = ""
                provider.save(update_fields=["last_checked_at", "last_error"])
                messages.success(request, f"✓ {provider.name}: Connection successful")
            else:
                provider.last_error = "Connection test failed"
                provider.save(update_fields=["last_error"])
                messages.error(request, f"✗ {provider.name}: Connection test failed")
        except Exception as e:
            provider.last_error = str(e)
            provider.save(update_fields=["last_error"])
            messages.error(request, f"✗ {provider.name}: {str(e)}")

        return redirect("admin:search_searchprovider_change", object_id)

    def test_search_view(self, request, object_id):
        provider = self.get_object(request, object_id)
        if provider is None:
            messages.error(request, "Provider not found")
            return redirect("admin:search_searchprovider_changelist")

        results = []

        if request.method == "POST":
            query = request.POST.get("query", "").strip()
            title = request.POST.get("title", "").strip()
            author = request.POST.get("author", "").strip()
            media_type = request.POST.get("media_type", "book")
            language = request.POST.get("language", "").strip() or None

            if not query and not title and not author:
                messages.error(request, "Please enter a search term, title, or author")
            else:
                try:
                    provider_instance = get_provider_instance(provider)
                    search_results = provider_instance.search(
                        query if query else "",
                        media_type,
                        language=language if language else None,
                        title=title if title else None,
                        author=author if author else None,
                    )
                    provider.last_checked_at = timezone.now()
                    provider.last_error = ""
                    provider.save(update_fields=["last_checked_at", "last_error"])

                    results = [
                        {
                            "title": r.title,
                            "authors": (
                                ", ".join(r.authors) if r.authors else "Unknown"
                            ),
                            "publisher": r.publisher or "-",
                            "publication_date": (
                                r.publication_date.isoformat()
                                if r.publication_date
                                else "-"
                            ),
                            "isbn": r.isbn or "-",
                            "isbn13": r.isbn13 or "-",
                            "language": r.language or "-",
                            "description": (
                                r.description[:200] + "..."
                                if r.description and len(r.description) > 200
                                else r.description or "-"
                            ),
                            "cover_url": r.cover_url or "",
                            "provider": r.provider,
                            "provider_id": r.provider_id,
                        }
                        for r in search_results
                    ]

                    if results:
                        messages.success(
                            request,
                            f"✓ Found {len(results)} results from {provider.name}",
                        )
                    else:
                        messages.warning(
                            request,
                            f"⚠ No results found from {provider.name}",
                        )
                except Exception as e:
                    provider.last_error = str(e)
                    provider.save(update_fields=["last_error"])
                    messages.error(request, f"Error: {str(e)}")

        context = {
            **self.admin_site.each_context(request),
            "title": f"Test Search - {provider.name}",
            "provider": provider,
            "results": results,
            "opts": self.model._meta,
            "has_view_permission": self.has_view_permission(request, provider),
        }

        return render(request, "admin/search/searchprovider/test_search.html", context)
