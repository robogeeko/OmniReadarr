from __future__ import annotations

from django.contrib import admin

from media.models import Audiobook, Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "authors_display",
        "series",
        "series_index",
        "status",
        "isbn",
        "isbn13",
        "publisher",
        "publication_date",
        "language",
        "provider",
        "added_date",
    ]
    list_filter = [
        "status",
        "language",
        "publisher",
        "publication_date",
        "added_date",
        "provider",
    ]
    search_fields = [
        "title",
        "sort_title",
        "isbn",
        "isbn13",
        "authors",
        "series",
        "description",
        "provider",
        "external_id",
    ]
    readonly_fields = ["id", "created_at", "updated_at", "added_date"]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "id",
                    "title",
                    "sort_title",
                    "authors",
                    "description",
                )
            },
        ),
        (
            "Series Information",
            {
                "fields": (
                    "series",
                    "series_index",
                )
            },
        ),
        (
            "Publication Details",
            {
                "fields": (
                    "isbn",
                    "isbn13",
                    "publisher",
                    "publication_date",
                    "language",
                    "page_count",
                    "edition",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "genres",
                    "tags",
                    "rating",
                    "identifiers",
                )
            },
        ),
        (
            "Media Files",
            {
                "fields": (
                    "cover_url",
                    "cover_path",
                )
            },
        ),
        (
            "Status & Provider",
            {
                "fields": (
                    "status",
                    "provider",
                    "external_id",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "added_date",
                )
            },
        ),
    )

    def authors_display(self, obj: Book) -> str:
        return ", ".join(obj.authors) if obj.authors else "-"

    authors_display.short_description = "Authors"


@admin.register(Audiobook)
class AudiobookAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "authors_display",
        "narrators_display",
        "series",
        "series_index",
        "status",
        "duration_display",
        "publisher",
        "publication_date",
        "language",
        "provider",
        "added_date",
    ]
    list_filter = [
        "status",
        "language",
        "publisher",
        "publication_date",
        "added_date",
        "provider",
    ]
    search_fields = [
        "title",
        "sort_title",
        "authors",
        "narrators",
        "series",
        "description",
        "provider",
        "external_id",
    ]
    readonly_fields = ["id", "created_at", "updated_at", "added_date"]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "id",
                    "title",
                    "sort_title",
                    "authors",
                    "description",
                )
            },
        ),
        (
            "Series Information",
            {
                "fields": (
                    "series",
                    "series_index",
                )
            },
        ),
        (
            "Publication Details",
            {
                "fields": (
                    "publisher",
                    "publication_date",
                    "language",
                )
            },
        ),
        (
            "Audiobook Details",
            {
                "fields": (
                    "narrators",
                    "duration_seconds",
                    "bitrate",
                    "chapters",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "genres",
                    "tags",
                    "rating",
                    "identifiers",
                )
            },
        ),
        (
            "Media Files",
            {
                "fields": (
                    "cover_url",
                    "cover_path",
                )
            },
        ),
        (
            "Status & Provider",
            {
                "fields": (
                    "status",
                    "provider",
                    "external_id",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "added_date",
                )
            },
        ),
    )

    def authors_display(self, obj: Audiobook) -> str:
        return ", ".join(obj.authors) if obj.authors else "-"

    authors_display.short_description = "Authors"

    def narrators_display(self, obj: Audiobook) -> str:
        return ", ".join(obj.narrators) if obj.narrators else "-"

    narrators_display.short_description = "Narrators"

    def duration_display(self, obj: Audiobook) -> str:
        if not obj.duration_seconds:
            return "-"
        hours = obj.duration_seconds // 3600
        minutes = (obj.duration_seconds % 3600) // 60
        seconds = obj.duration_seconds % 60
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    duration_display.short_description = "Duration"
