from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from core.models import MediaStatus
from media.models import Audiobook, Book
from search.providers.results import BookMetadata


@require_http_methods(["GET", "POST"])
def get_media_status(request):
    if request.method == "GET":
        providers_param = request.GET.get("providers", "").strip()
        external_ids_param = request.GET.get("external_ids", "").strip()

        if not providers_param or not external_ids_param:
            return JsonResponse(
                {"error": "Missing required parameters: providers and external_ids"},
                status=400,
            )

        providers = [p.strip() for p in providers_param.split(",") if p.strip()]
        external_ids = [e.strip() for e in external_ids_param.split(",") if e.strip()]

        if len(providers) != len(external_ids):
            return JsonResponse(
                {"error": "providers and external_ids must have the same length"},
                status=400,
            )

        items = [
            {"provider": provider, "external_id": external_id}
            for provider, external_id in zip(providers, external_ids)
        ]

    else:
        try:
            data = json.loads(request.body)
            items = data.get("items", [])
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        if not items or not isinstance(items, list):
            return JsonResponse({"error": "items must be a non-empty list"}, status=400)

        for item in items:
            if (
                not isinstance(item, dict)
                or "provider" not in item
                or "external_id" not in item
            ):
                return JsonResponse(
                    {"error": "Each item must have 'provider' and 'external_id'"},
                    status=400,
                )

    statuses = []
    for item in items:
        provider = item["provider"]
        external_id = item["external_id"]

        book_match = Book.objects.filter(
            provider=provider, external_id=external_id
        ).first()
        audiobook_match = Audiobook.objects.filter(
            provider=provider, external_id=external_id
        ).first()

        if book_match:
            statuses.append(
                {
                    "provider": provider,
                    "external_id": external_id,
                    "exists": True,
                    "media_type": "book",
                    "status": book_match.status,
                    "status_display": book_match.get_status_display(),
                }
            )
        elif audiobook_match:
            statuses.append(
                {
                    "provider": provider,
                    "external_id": external_id,
                    "exists": True,
                    "media_type": "audiobook",
                    "status": audiobook_match.status,
                    "status_display": audiobook_match.get_status_display(),
                }
            )
        else:
            statuses.append(
                {
                    "provider": provider,
                    "external_id": external_id,
                    "exists": False,
                    "media_type": None,
                    "status": None,
                    "status_display": None,
                }
            )

    return JsonResponse({"statuses": statuses})


@require_http_methods(["POST"])
def add_wanted_media(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    provider = data.get("provider", "").strip()
    external_id = data.get("external_id", "").strip()
    media_type = data.get("media_type", "").strip()
    metadata_dict = data.get("metadata", {})

    if not provider:
        return JsonResponse({"error": "Missing required field: provider"}, status=400)
    if not external_id:
        return JsonResponse(
            {"error": "Missing required field: external_id"}, status=400
        )
    if not media_type:
        return JsonResponse({"error": "Missing required field: media_type"}, status=400)
    if media_type not in ["book", "audiobook"]:
        return JsonResponse(
            {
                "error": "invalid_media_type",
                "message": "Media type must be 'book' or 'audiobook'",
            },
            status=400,
        )

    try:
        metadata = BookMetadata.from_dict(metadata_dict)
    except Exception as e:
        return JsonResponse(
            {"error": "invalid_metadata", "message": str(e)},
            status=400,
        )

    if media_type == "book":
        existing = Book.objects.filter(
            provider=provider, external_id=external_id
        ).first()
        if existing:
            return JsonResponse(
                {
                    "success": False,
                    "error": "already_exists",
                    "media_id": str(existing.id),
                    "status": existing.status,
                    "status_display": existing.get_status_display(),
                },
                status=200,
            )

        book = Book(
            provider=provider,
            external_id=external_id,
            title=metadata.title,
            authors=metadata.authors,
            description=metadata.description,
            publisher=metadata.publisher,
            publication_date=metadata.publication_date,
            cover_url=metadata.cover_url,
            language=metadata.language,
            genres=metadata.genres,
            tags=metadata.tags,
            isbn=metadata.isbn,
            isbn13=metadata.isbn13,
            page_count=metadata.page_count,
            edition=metadata.edition,
            status=MediaStatus.WANTED,
        )
        book.identifiers = {
            "provider": metadata.provider,
            "provider_id": metadata.provider_id,
        }
        book.save()

        return JsonResponse(
            {
                "success": True,
                "media_id": str(book.id),
                "status": book.status,
                "status_display": book.get_status_display(),
            }
        )

    elif media_type == "audiobook":
        existing = Audiobook.objects.filter(
            provider=provider, external_id=external_id
        ).first()
        if existing:
            return JsonResponse(
                {
                    "success": False,
                    "error": "already_exists",
                    "media_id": str(existing.id),
                    "status": existing.status,
                    "status_display": existing.get_status_display(),
                },
                status=200,
            )

        audiobook = Audiobook(
            provider=provider,
            external_id=external_id,
            title=metadata.title,
            authors=metadata.authors,
            description=metadata.description,
            publisher=metadata.publisher,
            publication_date=metadata.publication_date,
            cover_url=metadata.cover_url,
            language=metadata.language,
            genres=metadata.genres,
            tags=metadata.tags,
            narrators=metadata.narrators,
            duration_seconds=metadata.duration_seconds,
            bitrate=metadata.bitrate,
            chapters=metadata.chapters,
            status=MediaStatus.WANTED,
        )
        audiobook.identifiers = {
            "provider": metadata.provider,
            "provider_id": metadata.provider_id,
        }
        audiobook.save()

        return JsonResponse(
            {
                "success": True,
                "media_id": str(audiobook.id),
                "status": audiobook.status,
                "status_display": audiobook.get_status_display(),
            }
        )

    return JsonResponse({"error": "Invalid media type"}, status=400)
