import os
import shutil
import subprocess

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import redirect, render

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
            language = form.cleaned_data.get("language")
            voice = form.cleaned_data.get("voice")

            # LANGUAGE AND VOICE CONDITIONS
            if language == "Bengali":
                targetLanguage = "bn"
                if voice == "Male":
                    speakingVoice = {"bn": "bn-IN-Wavenet-B"}
                elif voice == "Female":
                    speakingVoice = {"bn": "bn-IN-Wavenet-A"}
            elif language == "Hindi":
                targetLanguage = "hi"
                if voice == "Male":
                    speakingVoice = {"hi": "hi-IN-Wavenet-C"}
                elif voice == "Female":
                    speakingVoice = {"hi": "hi-IN-Wavenet-D"}
            elif language == "Mandarin":
                targetLanguage = "cmn"
                if voice == "Male":
                    speakingVoice = {"cmn": "cmn-CN-Wavenet-C"}
                elif voice == "Female":
                    speakingVoice = {"cmn": "cmn-CN-Wavenet-A"}
            elif language == "Spanish":
                targetLanguage = "es"
                if voice == "Male":
                    speakingVoice = {"es": "es-US-Wavenet-B"}
                elif voice == "Female":
                    speakingVoice = {"es": "es-US-Wavenet-C"}

            task = download_yt_video.delay(
                request.user.id, link, targetLanguage, speakingVoice
            )
            return redirect("video_translator:currently_translating", pk=task.id)
        else:
            return render(
                request,
                "video_translator/video_index.html",
                {"form": form, "message": "Please enter a valid Youtube Link."},
            )

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


def current_processed_file(request, pk):
    my_user = User(id=request.user.id)
    current_file = (
        Video.objects.filter(id=pk, user=my_user).order_by("-created").first()
    )
    return render(
        request,
        "video_translator/current_processed_file.html",
        {
            "current_file": current_file,
        },
    )


@login_required
def translating_status_view(request, pk):
    my_user = User(id=request.user.id)
    try:
        translating = Video.objects.get(id=pk, user=my_user)
    except Video.DoesNotExist:
        raise Http404()

    if translating.is_translated:
        code = 200  # OK
    # elif translating.scraping_failed:
    #     code = 422  # Unprocessable entity.
    else:
        code = 204  # No content - wait

    return HttpResponse("", status=code)


@login_required
def currently_translating(request, pk):
    # my_user = User(id=request.user.id)
    # current_file = Video.objects.filter(user=my_user).order_by("-created").first()
    # flag = 0 if current_file is None else 1
    return render(
        request,
        "video_translator/task_processing.html",
        # {"flag": flag},
    )
