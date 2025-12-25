from __future__ import annotations

from django.http import Http404
from django.shortcuts import get_object_or_404, render

from media.models import Audiobook, Book


def format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def media_detail_view(request, media_id: str, media_type: str):
    if media_type == "book":
        media = get_object_or_404(Book, id=media_id)
    elif media_type == "audiobook":
        media = get_object_or_404(Audiobook, id=media_id)
    else:
        raise Http404("Invalid media type")

    duration_formatted = None
    if media_type == "audiobook" and media.duration_seconds:
        duration_formatted = format_duration(media.duration_seconds)

    context = {
        "media": media,
        "media_type": media_type,
        "media_type_display": "Book" if media_type == "book" else "Audiobook",
        "duration_formatted": duration_formatted,
    }

    return render(request, "media/detail.html", context)


def library_view(request):
    media_type_filter = request.GET.get("media_type", "").strip()

    books = Book.objects.all()
    audiobooks = Audiobook.objects.all()

    all_media = []

    if not media_type_filter or media_type_filter == "book":
        for book in books.order_by("-added_date"):
            all_media.append(
                {
                    "id": book.id,
                    "title": book.title,
                    "authors": book.authors,
                    "series": book.series,
                    "series_index": book.series_index,
                    "status": book.status,
                    "status_display": book.get_status_display(),
                    "added_date": book.added_date,
                    "media_type": "book",
                    "media_type_display": "Book",
                }
            )

    if not media_type_filter or media_type_filter == "audiobook":
        for audiobook in audiobooks.order_by("-added_date"):
            all_media.append(
                {
                    "id": audiobook.id,
                    "title": audiobook.title,
                    "authors": audiobook.authors,
                    "series": audiobook.series,
                    "series_index": audiobook.series_index,
                    "status": audiobook.status,
                    "status_display": audiobook.get_status_display(),
                    "added_date": audiobook.added_date,
                    "media_type": "audiobook",
                    "media_type_display": "Audiobook",
                }
            )

    all_media.sort(key=lambda x: x["added_date"], reverse=True)

    context = {
        "media_items": all_media,
        "selected_media_type": media_type_filter,
    }

    return render(request, "media/library.html", context)
