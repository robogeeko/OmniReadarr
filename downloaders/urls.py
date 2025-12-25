from django.urls import path

from downloaders import api

app_name = "downloaders"

urlpatterns = [
    path(
        "api/downloads/search/<uuid:media_id>/",
        api.search_for_media,
        name="search_for_media",
    ),
    path("api/downloads/initiate/", api.initiate_download, name="initiate_download"),
    path(
        "api/downloads/attempts/<uuid:media_id>/",
        api.get_download_attempts,
        name="get_download_attempts",
    ),
    path(
        "api/downloads/attempt/<uuid:attempt_id>/status/",
        api.get_download_status,
        name="get_download_status",
    ),
    path("api/downloads/blacklist/", api.blacklist_release, name="blacklist_release"),
    path(
        "api/downloads/attempt/<uuid:attempt_id>/",
        api.delete_download_attempt,
        name="delete_download_attempt",
    ),
]
