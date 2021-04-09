from django.urls import path

from .views import current_processed_file, download, my_uploads, video_index

app_name = "video_translator"
urlpatterns = [
    path("", video_index, name="video_index"),
    path("my_uploads/", my_uploads, name="my_uploads"),
    path(
        "file-processed/current-processed-file",
        current_processed_file,
        name="current_processed_file",
    ),
    path("download/<uuid:id>", download, name="download"),
]
