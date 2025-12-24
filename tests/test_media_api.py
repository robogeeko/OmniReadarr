from __future__ import annotations

import json
from datetime import date

import pytest
from django.test import Client
from django.urls import reverse

from core.models import MediaStatus
from media.models import Audiobook, Book


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture
def sample_metadata() -> dict:
    return {
        "provider": "openlibrary",
        "provider_id": "OL123456W",
        "title": "Test Book",
        "authors": ["Test Author"],
        "description": "A test book",
        "publisher": "Test Publisher",
        "publication_date": "2020-01-01",
        "cover_url": "https://example.com/cover.jpg",
        "language": "en",
        "genres": ["Fiction"],
        "tags": [],
        "isbn": "1234567890",
        "isbn13": "1234567890123",
        "page_count": 300,
        "edition": "1st",
        "narrators": [],
        "duration_seconds": None,
        "bitrate": None,
        "chapters": None,
    }


@pytest.fixture
def sample_book(sample_metadata: dict) -> Book:
    return Book.objects.create(
        provider="openlibrary",
        external_id="OL123456W",
        title=sample_metadata["title"],
        authors=sample_metadata["authors"],
        description=sample_metadata["description"],
        publisher=sample_metadata["publisher"],
        publication_date=date(2020, 1, 1),
        cover_url=sample_metadata["cover_url"],
        language=sample_metadata["language"],
        genres=sample_metadata["genres"],
        status=MediaStatus.WANTED,
    )


@pytest.fixture
def sample_audiobook(sample_metadata: dict) -> Audiobook:
    return Audiobook.objects.create(
        provider="openlibrary",
        external_id="OL789012W",
        title="Test Audiobook",
        authors=["Test Author"],
        description="A test audiobook",
        publisher="Test Publisher",
        publication_date=date(2020, 1, 1),
        cover_url="https://example.com/cover.jpg",
        language="en",
        genres=["Fiction"],
        narrators=["Narrator Name"],
        status=MediaStatus.DOWNLOADING,
    )


@pytest.mark.django_db
class TestGetMediaStatus:
    def test_get_status_with_query_params_existing_book(self, client: Client, sample_book: Book):
        url = reverse("media:get_media_status")
        response = client.get(
            url, {"providers": "openlibrary", "external_ids": "OL123456W"}
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data["statuses"]) == 1
        assert data["statuses"][0]["provider"] == "openlibrary"
        assert data["statuses"][0]["external_id"] == "OL123456W"
        assert data["statuses"][0]["exists"] is True
        assert data["statuses"][0]["media_type"] == "book"
        assert data["statuses"][0]["status"] == "wanted"
        assert data["statuses"][0]["status_display"] == "Wanted"

    def test_get_status_with_query_params_existing_audiobook(
        self, client: Client, sample_audiobook: Audiobook
    ):
        url = reverse("media:get_media_status")
        response = client.get(
            url, {"providers": "openlibrary", "external_ids": "OL789012W"}
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data["statuses"]) == 1
        assert data["statuses"][0]["provider"] == "openlibrary"
        assert data["statuses"][0]["external_id"] == "OL789012W"
        assert data["statuses"][0]["exists"] is True
        assert data["statuses"][0]["media_type"] == "audiobook"
        assert data["statuses"][0]["status"] == "downloading"
        assert data["statuses"][0]["status_display"] == "Downloading"

    def test_get_status_with_query_params_non_existing(self, client: Client):
        url = reverse("media:get_media_status")
        response = client.get(
            url, {"providers": "openlibrary", "external_ids": "OL999999W"}
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data["statuses"]) == 1
        assert data["statuses"][0]["provider"] == "openlibrary"
        assert data["statuses"][0]["external_id"] == "OL999999W"
        assert data["statuses"][0]["exists"] is False
        assert data["statuses"][0]["media_type"] is None
        assert data["statuses"][0]["status"] is None
        assert data["statuses"][0]["status_display"] is None

    def test_get_status_with_query_params_multiple_items(
        self, client: Client, sample_book: Book, sample_audiobook: Audiobook
    ):
        url = reverse("media:get_media_status")
        response = client.get(
            url,
            {
                "providers": "openlibrary,openlibrary",
                "external_ids": "OL123456W,OL789012W",
            },
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data["statuses"]) == 2
        assert data["statuses"][0]["exists"] is True
        assert data["statuses"][0]["media_type"] == "book"
        assert data["statuses"][1]["exists"] is True
        assert data["statuses"][1]["media_type"] == "audiobook"

    def test_get_status_with_query_params_missing_providers(self, client: Client):
        url = reverse("media:get_media_status")
        response = client.get(url, {"external_ids": "OL123456W"})

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data
        assert "providers" in data["error"].lower()

    def test_get_status_with_query_params_missing_external_ids(self, client: Client):
        url = reverse("media:get_media_status")
        response = client.get(url, {"providers": "openlibrary"})

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data
        assert "external_ids" in data["error"].lower()

    def test_get_status_with_query_params_mismatched_lengths(self, client: Client):
        url = reverse("media:get_media_status")
        response = client.get(
            url,
            {
                "providers": "openlibrary,openlibrary",
                "external_ids": "OL123456W",
            },
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data
        assert "length" in data["error"].lower()

    def test_get_status_with_post_existing_book(self, client: Client, sample_book: Book):
        url = reverse("media:get_media_status")
        payload = {
            "items": [
                {"provider": "openlibrary", "external_id": "OL123456W"},
            ]
        }
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data["statuses"]) == 1
        assert data["statuses"][0]["exists"] is True
        assert data["statuses"][0]["media_type"] == "book"

    def test_get_status_with_post_multiple_items(
        self, client: Client, sample_book: Book, sample_audiobook: Audiobook
    ):
        url = reverse("media:get_media_status")
        payload = {
            "items": [
                {"provider": "openlibrary", "external_id": "OL123456W"},
                {"provider": "openlibrary", "external_id": "OL789012W"},
                {"provider": "openlibrary", "external_id": "OL999999W"},
            ]
        }
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data["statuses"]) == 3
        assert data["statuses"][0]["exists"] is True
        assert data["statuses"][1]["exists"] is True
        assert data["statuses"][2]["exists"] is False

    def test_get_status_with_post_invalid_json(self, client: Client):
        url = reverse("media:get_media_status")
        response = client.post(url, "invalid json", content_type="application/json")

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data

    def test_get_status_with_post_missing_items(self, client: Client):
        url = reverse("media:get_media_status")
        payload = {}
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data

    def test_get_status_with_post_invalid_item_structure(self, client: Client):
        url = reverse("media:get_media_status")
        payload = {"items": [{"provider": "openlibrary"}]}
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data

    def test_get_status_invalid_provider(self, client: Client):
        url = reverse("media:get_media_status")
        response = client.get(
            url, {"providers": "invalid_provider", "external_ids": "OL123456W"}
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data["statuses"]) == 1
        assert data["statuses"][0]["exists"] is False
        assert "error" in data["statuses"][0]
        assert "invalid" in data["statuses"][0]["error"].lower()

    def test_get_status_book_takes_precedence_over_audiobook(
        self, client: Client, sample_book: Book
    ):
        Audiobook.objects.create(
            provider="openlibrary",
            external_id="OL123456W",
            title="Same ID Audiobook",
            authors=["Author"],
            status=MediaStatus.DOWNLOADING,
        )

        url = reverse("media:get_media_status")
        response = client.get(
            url, {"providers": "openlibrary", "external_ids": "OL123456W"}
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["statuses"][0]["media_type"] == "book"
        assert data["statuses"][0]["status"] == "wanted"


@pytest.mark.django_db
class TestAddWantedMedia:
    def test_add_wanted_book_success(self, client: Client, sample_metadata: dict):
        url = reverse("media:add_wanted_media")
        payload = {
            "provider": "openlibrary",
            "external_id": "OL123456W",
            "media_type": "book",
            "metadata": sample_metadata,
        }
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["success"] is True
        assert "media_id" in data
        assert data["status"] == "wanted"
        assert data["status_display"] == "Wanted"

        book = Book.objects.get(provider="openlibrary", external_id="OL123456W")
        assert book.title == sample_metadata["title"]
        assert book.authors == sample_metadata["authors"]
        assert book.status == MediaStatus.WANTED

    def test_add_wanted_audiobook_success(self, client: Client, sample_metadata: dict):
        url = reverse("media:add_wanted_media")
        audiobook_metadata = sample_metadata.copy()
        audiobook_metadata.update(
            {
                "narrators": ["Narrator Name"],
                "duration_seconds": 3600,
                "chapters": 10,
            }
        )
        payload = {
            "provider": "openlibrary",
            "external_id": "OL789012W",
            "media_type": "audiobook",
            "metadata": audiobook_metadata,
        }
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["success"] is True
        assert "media_id" in data
        assert data["status"] == "wanted"

        audiobook = Audiobook.objects.get(
            provider="openlibrary", external_id="OL789012W"
        )
        assert audiobook.title == audiobook_metadata["title"]
        assert audiobook.narrators == audiobook_metadata["narrators"]
        assert audiobook.status == MediaStatus.WANTED

    def test_add_wanted_book_already_exists(
        self, client: Client, sample_book: Book, sample_metadata: dict
    ):
        url = reverse("media:add_wanted_media")
        payload = {
            "provider": "openlibrary",
            "external_id": "OL123456W",
            "media_type": "book",
            "metadata": sample_metadata,
        }
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["success"] is False
        assert data["error"] == "already_exists"
        assert data["status"] == "wanted"
        assert data["status_display"] == "Wanted"

        books_count = Book.objects.filter(
            provider="openlibrary", external_id="OL123456W"
        ).count()
        assert books_count == 1

    def test_add_wanted_audiobook_already_exists(
        self, client: Client, sample_audiobook: Audiobook, sample_metadata: dict
    ):
        url = reverse("media:add_wanted_media")
        audiobook_metadata = sample_metadata.copy()
        audiobook_metadata["provider_id"] = "OL789012W"
        payload = {
            "provider": "openlibrary",
            "external_id": "OL789012W",
            "media_type": "audiobook",
            "metadata": audiobook_metadata,
        }
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["success"] is False
        assert data["error"] == "already_exists"
        assert data["status"] == "downloading"

    def test_add_wanted_missing_provider(self, client: Client, sample_metadata: dict):
        url = reverse("media:add_wanted_media")
        payload = {
            "external_id": "OL123456W",
            "media_type": "book",
            "metadata": sample_metadata,
        }
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data
        assert "provider" in data["error"].lower()

    def test_add_wanted_missing_external_id(self, client: Client, sample_metadata: dict):
        url = reverse("media:add_wanted_media")
        payload = {
            "provider": "openlibrary",
            "media_type": "book",
            "metadata": sample_metadata,
        }
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data
        assert "external_id" in data["error"].lower()

    def test_add_wanted_missing_media_type(self, client: Client, sample_metadata: dict):
        url = reverse("media:add_wanted_media")
        payload = {
            "provider": "openlibrary",
            "external_id": "OL123456W",
            "metadata": sample_metadata,
        }
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data
        assert "media_type" in data["error"].lower()

    def test_add_wanted_invalid_media_type(self, client: Client, sample_metadata: dict):
        url = reverse("media:add_wanted_media")
        payload = {
            "provider": "openlibrary",
            "external_id": "OL123456W",
            "media_type": "invalid",
            "metadata": sample_metadata,
        }
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert data["error"] == "invalid_media_type"
        assert "book" in data["message"].lower()
        assert "audiobook" in data["message"].lower()

    def test_add_wanted_invalid_json(self, client: Client):
        url = reverse("media:add_wanted_media")
        response = client.post(url, "invalid json", content_type="application/json")

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data

    def test_add_wanted_minimal_metadata(self, client: Client):
        url = reverse("media:add_wanted_media")
        payload = {
            "provider": "openlibrary",
            "external_id": "OL123456W",
            "media_type": "book",
            "metadata": {
                "provider": "openlibrary",
                "provider_id": "OL123456W",
                "title": "Minimal Book",
            },
        }
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["success"] is True

        book = Book.objects.get(provider="openlibrary", external_id="OL123456W")
        assert book.title == "Minimal Book"

    def test_add_wanted_invalid_provider(self, client: Client, sample_metadata: dict):
        url = reverse("media:add_wanted_media")
        payload = {
            "provider": "invalid_provider",
            "external_id": "OL123456W",
            "media_type": "book",
            "metadata": sample_metadata,
        }
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert data["error"] == "invalid_provider"
        assert "provider" in data["message"].lower()

    def test_add_wanted_book_and_audiobook_same_external_id(
        self, client: Client, sample_metadata: dict
    ):
        url = reverse("media:add_wanted_media")

        book_payload = {
            "provider": "openlibrary",
            "external_id": "OL123456W",
            "media_type": "book",
            "metadata": sample_metadata,
        }
        response = client.post(
            url, json.dumps(book_payload), content_type="application/json"
        )
        assert response.status_code == 200
        assert json.loads(response.content)["success"] is True

        audiobook_metadata = sample_metadata.copy()
        audiobook_metadata["provider_id"] = "OL123456W"
        audiobook_payload = {
            "provider": "openlibrary",
            "external_id": "OL123456W",
            "media_type": "audiobook",
            "metadata": audiobook_metadata,
        }
        response = client.post(
            url, json.dumps(audiobook_payload), content_type="application/json"
        )
        assert response.status_code == 200
        assert json.loads(response.content)["success"] is True

        assert Book.objects.filter(
            provider="openlibrary", external_id="OL123456W"
        ).exists()
        assert Audiobook.objects.filter(
            provider="openlibrary", external_id="OL123456W"
        ).exists()

