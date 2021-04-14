import os
import shutil
import subprocess

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .forms import Video_form
from .models import Video
from .tasks import download_yt_video

User = get_user_model()


@login_required
def video_index(request):
    if request.method == "POST":
        form = Video_form(data=request.POST or None, files=request.FILES or None)
        if form.is_valid():
            link = form.cleaned_data.get("youtube_url")
            download_yt_video.delay(request.user.id, link)

            # while task.state not in ("SUCCESS", "FAILURE"):
            #     time.sleep(0.1)
            # if task.failed():
            #     return render(
            #         request,
            #         "video_translator/video_index.html",
            #         {
            #             "form": form,
            #         },
            #     )
            my_user = User(id=request.user.id)
            current_file = (
                Video.objects.filter(user=my_user).order_by("-created").first()
            )
            flag = 0 if current_file is None else 1
            return render(
                request,
                "video_translator/task_processing.html",
                {"flag": flag},
            )
        return HttpResponseRedirect(reverse("video_translator:current_processed_file"))

    else:
        form = Video_form()

        return render(
            request,
            "video_translator/video_index.html",
            {"form": form},
        )


def download(request, id):
    obj = Video.objects.get(id=id)
    # credential_path = (
    #     "yt_video_translate/video_translator/env/translate-af9005978349.json"
    # )
    # os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credential_path
    storageBucket = "translate-001"
    # filename = obj.translated_video_clip.name
    # # gcs_path = os.path.join("gs://", storageBucket, "media", filename)
    # finalTranslatedFile = os.path.join("tmp", "finalTranslatedFile" + ".mp4")
    # # print("download")
    # # print("filename", filename)
    # # print("gcs_path", gcs_path)
    # # print("finalTranslatedFile", finalTranslatedFile)
    final_path = os.path.join(settings.MEDIA_ROOT, "temp", "final.mp4")

    # storage_client = storage.Client()
    # bucket = storage_client.bucket(storageBucket)
    # blob = bucket.blob(finalTranslatedFile)
    # blob.download_to_filename(f"{final_path}")
    # print("final_path", final_path)

    filename = obj.translated_video_clip.name
    subprocess.call(
        f"gsutil cp gs://{storageBucket}/media/{filename} {final_path}", shell=True
    )

    # response = FileResponse(open(f"{final_path}", "rb"))
    response = FileResponse(open(f"{final_path}", "rb"))
    shutil.rmtree(final_path, ignore_errors=True)
    # blob.delete()
    return response

    # bucket = storage_client.bucket(storageBucket)
    # blob = bucket.blob(gcs_path)
    # blob.download_to_filename(destination_file_name)
    # response = FileResponse(open(gcs_path, "rb"))
    # return response


def my_uploads(request):
    my_user = User(id=request.user.id)
    queryset = Video.objects.filter(user=my_user).order_by("-created")
    return render(
        request,
        "video_translator/my_uploads.html",
        {
            "qs": queryset,
        },
    )


def current_processed_file(request):
    my_user = User(id=request.user.id)
    current_file = Video.objects.filter(user=my_user).order_by("-created").first()
    return render(
        request,
        "video_translator/current_processed_file.html",
        {
            "current_file": current_file,
        },
    )
