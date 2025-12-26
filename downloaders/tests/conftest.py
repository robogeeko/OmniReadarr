import pytest

from media.models import Audiobook, Book


@pytest.fixture
def book():
    return Book.objects.create(
        title="Test Book",
        authors=["Test Author"],
        status="wanted",
    )


@pytest.fixture
def audiobook():
    return Audiobook.objects.create(
        title="Test Audiobook",
        authors=["Test Author"],
        status="wanted",
    )

