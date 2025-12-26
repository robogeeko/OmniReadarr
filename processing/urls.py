from django.urls import path

from processing import api

app_name = "processing"

urlpatterns = [
    path(
        "api/processing/convert/<uuid:attempt_id>/",
        api.convert_to_epub,
        name="convert_to_epub",
    ),
    path(
        "api/processing/organize/<uuid:attempt_id>/",
        api.organize_to_library,
        name="organize_to_library",
    ),
]
