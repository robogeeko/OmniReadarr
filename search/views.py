from __future__ import annotations

import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render

from search.models import SearchProvider
from search.providers.registry import get_provider_instance


def search_view(request):
    providers = []
    results = []
    selected_media_type = ""
    selected_provider_id = ""

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        author = request.POST.get("author", "").strip()
        media_type = request.POST.get("media_type", "").strip()
        provider_id = request.POST.get("provider_id", "").strip()

        if not title and not author:
            messages.error(request, "Please enter a title or author")
        elif not media_type:
            messages.error(request, "Please select a media type")
        elif not provider_id:
            messages.error(request, "Please select a search provider")
        else:
            try:
                provider = SearchProvider.objects.get(id=provider_id, enabled=True)
                if media_type not in provider.supports_media_types:
                    messages.error(
                        request,
                        f"Provider {provider.name} does not support {media_type}",
                    )
                else:
                    provider_instance = get_provider_instance(provider)
                    search_results = provider_instance.search(
                        "",
                        media_type,
                        language=None,
                        title=title if title else None,
                        author=author if author else None,
                    )

                    results = []
                    for r in search_results:
                        metadata_dict = r.to_dict()
                        results.append(
                            {
                                "title": r.title,
                                "authors": (
                                    ", ".join(r.authors) if r.authors else "Unknown"
                                ),
                                "publisher": r.publisher or "-",
                                "publication_date": (
                                    r.publication_date.isoformat()
                                    if r.publication_date
                                    else "-"
                                ),
                                "isbn": r.isbn or "-",
                                "isbn13": r.isbn13 or "-",
                                "language": r.language or "-",
                                "description": (
                                    r.description[:200] + "..."
                                    if r.description and len(r.description) > 200
                                    else r.description or "-"
                                ),
                                "cover_url": r.cover_url or "",
                                "provider": r.provider,
                                "provider_id": r.provider_id,
                                "metadata": metadata_dict,
                                "metadata_json": json.dumps(metadata_dict),
                            }
                        )

                    if results:
                        messages.success(
                            request,
                            f"Found {len(results)} results from {provider.name}",
                        )
                    else:
                        messages.warning(
                            request,
                            f"No results found from {provider.name}",
                        )

                    selected_media_type = media_type
                    selected_provider_id = str(provider_id)

                    providers = SearchProvider.objects.filter(
                        enabled=True, supports_media_types__contains=[media_type]
                    ).order_by("priority", "name")

            except SearchProvider.DoesNotExist:
                messages.error(request, "Provider not found")
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
    else:
        media_type = request.GET.get("media_type", "").strip()
        if media_type:
            providers = SearchProvider.objects.filter(
                enabled=True, supports_media_types__contains=[media_type]
            ).order_by("priority", "name")
            selected_media_type = media_type

    context = {
        "providers": providers,
        "results": results,
        "selected_media_type": selected_media_type,
        "selected_provider_id": selected_provider_id,
    }

    return render(request, "search/search.html", context)


def get_providers_json(request):
    media_type = request.GET.get("media_type", "").strip()
    if not media_type:
        return JsonResponse({"providers": []})

    providers = SearchProvider.objects.filter(
        enabled=True, supports_media_types__contains=[media_type]
    ).order_by("priority", "name")

    providers_data = [
        {
            "id": str(provider.id),
            "name": provider.name,
            "provider_type": provider.get_provider_type_display(),
        }
        for provider in providers
    ]

    return JsonResponse({"providers": providers_data})
