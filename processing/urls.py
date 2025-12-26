from django.urls import path

from processing import api

app_name = "processing"

urlpatterns = [
    path(
        "api/processing/convert/<uuid:attempt_id>/",
        api.convert_to_epub,
        name="convert_to_epub",
    ),
]

