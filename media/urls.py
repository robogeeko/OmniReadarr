from django.urls import path

from media import api

app_name = "media"

urlpatterns = [
    path("api/media/status/", api.get_media_status, name="get_media_status"),
    path("api/media/wanted/", api.add_wanted_media, name="add_wanted_media"),
]
