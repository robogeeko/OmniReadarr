from __future__ import annotations

import json
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from downloaders.models import BlacklistReason, DownloadAttempt
from downloaders.services.download import DownloadService, DownloadServiceError
from downloaders.services.search import SearchService, SearchServiceError
from media.models import Audiobook, Book


@require_http_methods(["POST"])
def search_for_media(request, media_id: UUID):
    book = Book.objects.filter(id=media_id).first()
    audiobook = Audiobook.objects.filter(id=media_id).first()
    media = book or audiobook

    if not media:
        return JsonResponse({"error": "Media not found"}, status=404)

    try:
        search_service = SearchService()
        results = search_service.search_for_media(media)

        results_data = [
            {
                "guid": r.guid,
                "title": r.title,
                "indexer": r.indexer,
                "indexer_id": r.indexer_id,
                "size": r.size,
                "publish_date": (
                    r.publish_date.isoformat() if r.publish_date else None
                ),
                "seeders": r.seeders,
                "peers": r.peers,
                "protocol": r.protocol,
                "download_url": r.download_url,
                "info_url": r.info_url,
            }
            for r in results
        ]

        return JsonResponse({"results": results_data, "total": len(results_data)})
    except SearchServiceError as e:
        return JsonResponse({"error": str(e)}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"Search failed: {str(e)}"}, status=500)


@require_http_methods(["POST"])
def initiate_download(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    media_id = data.get("media_id")
    indexer_id = data.get("indexer_id")
    guid = data.get("guid")

    if not media_id:
        return JsonResponse({"error": "Missing required field: media_id"}, status=400)
    if indexer_id is None:
        return JsonResponse({"error": "Missing required field: indexer_id"}, status=400)
    if not guid:
        return JsonResponse({"error": "Missing required field: guid"}, status=400)

    try:
        media_uuid = UUID(str(media_id))
    except ValueError:
        return JsonResponse({"error": "Invalid media_id format"}, status=400)

    book = Book.objects.filter(id=media_uuid).first()
    audiobook = Audiobook.objects.filter(id=media_uuid).first()
    media = book or audiobook

    if not media:
        return JsonResponse({"error": "Media not found"}, status=404)

    try:
        import logging

        api_logger = logging.getLogger(__name__)
        api_logger.info("=== API INITIATE DOWNLOAD DEBUG ===")
        api_logger.info(f"media_id: {media_id}, indexer_id: {indexer_id}, guid: {guid}")

        result_data = data.get("result")
        if result_data:
            from indexers.prowlarr.results import SearchResult
            from datetime import datetime

            publish_date = None
            if result_data.get("publish_date"):
                try:
                    publish_date = datetime.fromisoformat(
                        result_data["publish_date"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            matching_result = SearchResult(
                guid=result_data.get("guid", guid),
                title=result_data.get("title", ""),
                indexer=result_data.get("indexer", ""),
                indexer_id=result_data.get("indexer_id", indexer_id),
                size=result_data.get("size"),
                publish_date=publish_date,
                seeders=result_data.get("seeders"),
                peers=result_data.get("peers"),
                protocol=result_data.get("protocol", "usenet"),
                download_url=result_data.get("download_url", ""),
                info_url=result_data.get("info_url"),
            )
            api_logger.info(
                f"Constructed SearchResult from request data: {matching_result.title}"
            )
        else:
            api_logger.warning(
                "No result data in request, falling back to search (slow). "
                "Consider updating frontend to pass full result data."
            )
            search_service = SearchService()
            search_results = search_service.search_for_media(media)

            matching_result = None
            for result in search_results:
                if result.guid == guid and result.indexer_id == indexer_id:
                    matching_result = result
                    break

            if not matching_result:
                api_logger.warning(
                    f"No matching result found. guid={guid}, indexer_id={indexer_id}"
                )
                return JsonResponse({"error": "Search result not found"}, status=404)

        download_service = DownloadService()
        attempt = download_service.initiate_download(media, matching_result)

        return JsonResponse(
            {
                "success": True,
                "attempt_id": str(attempt.id),
                "status": attempt.status,
                "status_display": attempt.get_status_display(),  # type: ignore[attr-defined]
            }
        )
    except DownloadServiceError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Download initiation failed: {str(e)}"},
            status=500,
        )


@require_http_methods(["GET"])
def get_download_attempts(request, media_id: UUID):
    book = Book.objects.filter(id=media_id).first()
    audiobook = Audiobook.objects.filter(id=media_id).first()
    media = book or audiobook

    if not media:
        return JsonResponse({"error": "Media not found"}, status=404)

    content_type = ContentType.objects.get_for_model(media)
    attempts = DownloadAttempt.objects.filter(
        content_type=content_type, object_id=media_id
    ).order_by("-attempted_at")

    attempts_data = [
        {
            "id": str(a.id),
            "indexer": a.indexer,
            "release_title": a.release_title,
            "status": a.status,
            "status_display": a.get_status_display(),
            "attempted_at": a.attempted_at.isoformat(),
            "file_size": a.file_size,
            "error_type": a.error_type,
            "error_reason": a.error_reason,
            "raw_file_path": a.raw_file_path,
            "post_processed_file_path": a.post_processed_file_path,
        }
        for a in attempts
    ]

    return JsonResponse({"attempts": attempts_data})


@require_http_methods(["GET"])
def get_download_status(request, attempt_id: UUID):
    try:
        download_service = DownloadService()
        attempt = download_service.get_download_status(attempt_id)

        progress = 0.0
        if attempt.download_client and attempt.download_client_download_id:
            try:
                from downloaders.clients.sabnzbd import SABnzbdClient

                sabnzbd_client = SABnzbdClient(attempt.download_client)
                job_status = sabnzbd_client.get_job_status(
                    attempt.download_client_download_id
                )
                if job_status:
                    progress = job_status.progress
            except Exception:
                pass

        return JsonResponse(
            {
                "status": attempt.status,
                "status_display": attempt.get_status_display(),  # type: ignore[attr-defined]
                "progress": progress,
                "error": attempt.error_reason if attempt.error_type else None,
            }
        )
    except DownloadServiceError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            return JsonResponse({"error": error_msg}, status=404)
        return JsonResponse({"error": error_msg}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"Status check failed: {str(e)}"}, status=500)


@require_http_methods(["POST"])
def blacklist_release(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    attempt_id = data.get("attempt_id")
    reason = data.get("reason", BlacklistReason.MANUAL)
    reason_details = data.get("reason_details", "")

    if not attempt_id:
        return JsonResponse({"error": "Missing required field: attempt_id"}, status=400)

    try:
        attempt_uuid = UUID(attempt_id)
    except ValueError:
        return JsonResponse({"error": "Invalid attempt_id format"}, status=400)

    valid_reasons = [choice[0] for choice in BlacklistReason.choices]
    if reason not in valid_reasons:
        return JsonResponse(
            {"error": f"Invalid reason. Must be one of: {', '.join(valid_reasons)}"},
            status=400,
        )

    try:
        download_service = DownloadService()
        download_service.mark_as_blacklisted(
            attempt_uuid, reason=reason, reason_details=reason_details
        )

        return JsonResponse({"success": True})
    except DownloadServiceError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=404)
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Blacklist failed: {str(e)}"}, status=500
        )


@require_http_methods(["DELETE"])
def delete_download_attempt(request, attempt_id: UUID):
    try:
        download_service = DownloadService()
        result = download_service.delete_download_attempt(attempt_id)

        return JsonResponse(
            {
                "success": result["success"],
                "message": (
                    "; ".join(result["messages"])
                    if result["messages"]
                    else "Download attempt deleted"
                ),
            }
        )
    except DownloadServiceError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            return JsonResponse({"success": False, "error": error_msg}, status=404)
        return JsonResponse({"success": False, "error": error_msg}, status=500)
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Deletion failed: {str(e)}"}, status=500
        )
