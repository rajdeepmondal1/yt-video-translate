import os
import shutil
import subprocess

from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

# from django.shortcuts import redirect
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
            task = download_yt_video.delay(request.user.id, link)
            task_id = task.task_id
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
            res = AsyncResult(task_id).get(timeout=10)  # ready()
            if res.successful():  # .successful()
                my_user = User(id=request.user.id)
                current_file = (
                    Video.objects.filter(user=my_user).order_by("-created").first()
                )
                return HttpResponseRedirect(
                    reverse(
                        "video_translator:current_processed_file",
                        args={
                            # "app_name": video_translator,
                            "task_id": task_id,
                            "current_file": current_file,
                        },
                    )
                )
                # return render_to_response('ajax_fragment.html', {'results': results.get()})
            else:
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
            # if res.state == state(SUCCESS):
            # if res.state in ("SUCCESS"):
            #     my_user = User(id=request.user.id)
            #     current_file = (
            #         Video.objects.filter(user=my_user).order_by("-created").first()
            #     )
            #     return HttpResponseRedirect(
            #         reverse(
            #             "video_translator:current_processed_file",
            #             args={
            #                 # "app_name": video_translator,
            #                 "task_id": task_id,
            #                 "current_file": current_file,
            #             },
            #         )
            #     )
            # return redirect(
            #     reverse(
            #         current_processed_file,
            #         kwargs={
            #             "app_name": video_translator,
            #             "task_id": task_id,
            #             "current_file": current_file,
            #         },
            #     )
            # )
            # else:
            #     my_user = User(id=request.user.id)
            #     current_file = (
            #         Video.objects.filter(user=my_user).order_by("-created").first()
            #     )
            #     flag = 0 if current_file is None else 1
            #     return render(
            #         request,
            #         "video_translator/task_processing.html",
            #         {"flag": flag},
            #     )
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
    if os.path.exists(os.path.join(settings.MEDIA_ROOT, "temporary-translated")):
        shutil.rmtree(
            os.path.join(settings.MEDIA_ROOT, "temporary-translated"),
            ignore_errors=True,
        )
    final_path = os.path.join(
        settings.MEDIA_ROOT, "temporary-translated", "translated.mp4"
    )
    filename = obj.translated_video_clip.name
    subprocess.call(
        f"gsutil cp gs://{storageBucket}/media/{filename} {final_path}", shell=True
    )
    response = FileResponse(open(f"{final_path}", "rb"))
    shutil.rmtree(final_path, ignore_errors=True)
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
