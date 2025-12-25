from django.urls import path

from media import api, views

app_name = "media"

urlpatterns = [
    path("library/", views.library_view, name="library"),
    path("api/media/status/", api.get_media_status, name="get_media_status"),
    path("api/media/wanted/", api.add_wanted_media, name="add_wanted_media"),
]
