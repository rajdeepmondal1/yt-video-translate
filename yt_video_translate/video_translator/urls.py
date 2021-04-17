from django.urls import path

from .views import (
    current_processed_file,
    currently_translating,
    download,
    my_uploads,
    translating_status_view,
    video_index,
)

app_name = "video_translator"
urlpatterns = [
    path("", video_index, name="video_index"),
    path("my_uploads/", my_uploads, name="my_uploads"),
    path(
        "currently_translating/<uuid:pk>/translated/",
        current_processed_file,
        name="current_processed_file",
    ),
    path(
        "currently_translating/<uuid:pk>",
        currently_translating,
        name="currently_translating",
    ),
    path("download/<uuid:id>", download, name="download"),
    path(
        "currently_translating/<uuid:pk>/status/",
        translating_status_view,
        name="status",
    ),
]
