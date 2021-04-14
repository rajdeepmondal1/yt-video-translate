import os

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
    storageBucket = "translate-001"
    filename = obj.translated_video_clip.name
    gcs_path = os.path.join("gs://", storageBucket, filename)
    print("download")
    print("filename", filename)
    print("gcs_path", gcs_path)
    response = FileResponse(open(gcs_path, "rb"))
    return response


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
