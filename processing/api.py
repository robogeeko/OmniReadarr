from __future__ import annotations

from uuid import UUID

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from processing.services.post_process import (
    PostProcessingError,
    convert_to_epub_for_attempt,
    organize_to_library_for_attempt,
)


@require_http_methods(["POST"])
def convert_to_epub(request, attempt_id: UUID):
    try:
        result = convert_to_epub_for_attempt(attempt_id)
        if result.get("success"):
            return JsonResponse(
                {"success": True, "message": result.get("message", "Conversion successful")}
            )
        else:
            return JsonResponse(
                {"success": False, "error": result.get("error", "Unknown error")},
                status=400,
            )
    except PostProcessingError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Conversion failed: {str(e)}"}, status=500
        )


@require_http_methods(["POST"])
def organize_to_library(request, attempt_id: UUID):
    try:
        result = organize_to_library_for_attempt(attempt_id)
        if result.get("success"):
            return JsonResponse(
                {"success": True, "message": result.get("message", "Organization successful")}
            )
        else:
            return JsonResponse(
                {"success": False, "error": result.get("error", "Unknown error")},
                status=400,
            )
    except PostProcessingError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Organization failed: {str(e)}"}, status=500
        )

