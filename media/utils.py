from __future__ import annotations

from uuid import UUID

from core.models import Media
from media.models import Audiobook, Book


def get_media_by_id(media_id: UUID) -> Media | None:
    try:
        return Book.objects.get(id=media_id)
    except Book.DoesNotExist:
        try:
            return Audiobook.objects.get(id=media_id)
        except Audiobook.DoesNotExist:
            return None
