from __future__ import annotations

from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError

from media.models import Audiobook, Book
from media.utils import get_media_by_id


@pytest.mark.django_db
class TestGetMediaById:
    def test_returns_book_when_book_exists(self):
        book = Book.objects.create(
            title="Test Book",
            authors=["Test Author"],
            status="wanted",
        )
        result = get_media_by_id(book.id)
        assert result is not None
        assert isinstance(result, Book)
        assert result.id == book.id
        assert result.title == "Test Book"

    def test_returns_audiobook_when_audiobook_exists(self):
        audiobook = Audiobook.objects.create(
            title="Test Audiobook",
            authors=["Test Author"],
            status="wanted",
        )
        result = get_media_by_id(audiobook.id)
        assert result is not None
        assert isinstance(result, Audiobook)
        assert result.id == audiobook.id
        assert result.title == "Test Audiobook"

    def test_returns_none_when_neither_exists(self):
        non_existent_id = uuid4()
        result = get_media_by_id(non_existent_id)
        assert result is None

    def test_returns_book_when_both_exist_with_same_id(self):
        book_id = uuid4()
        Book.objects.create(
            id=book_id,
            title="Test Book",
            authors=["Test Author"],
            status="wanted",
        )
        Audiobook.objects.create(
            id=book_id,
            title="Test Audiobook",
            authors=["Test Author"],
            status="wanted",
        )
        result = get_media_by_id(book_id)
        assert result is not None
        assert isinstance(result, Book)
        assert result.title == "Test Book"

    def test_handles_invalid_uuid_format(self):
        with pytest.raises(ValidationError):
            get_media_by_id("not-a-uuid")  # type: ignore[arg-type]
