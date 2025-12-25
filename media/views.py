from __future__ import annotations

from django.shortcuts import render

from media.models import Audiobook, Book


def library_view(request):
    books = Book.objects.all().order_by("-added_date")[:50]
    audiobooks = Audiobook.objects.all().order_by("-added_date")[:50]

    context = {
        "books": books,
        "audiobooks": audiobooks,
        "total_books": Book.objects.count(),
        "total_audiobooks": Audiobook.objects.count(),
    }

    return render(request, "media/library.html", context)
