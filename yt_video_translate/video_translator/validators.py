import requests
import validators
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from pytube import YouTube, extract


def validate_youtube_url(value):
    yt = YouTube(f"{value}")
    if validators.url(f"{value}"):
        yt_id = extract.video_id(f"{value}")
        if not check_video_url(yt_id) or not yt_id:
            raise ValidationError(
                _("%(value)s is not an valid youtube link."),
                params={"value": value},
            )
        else:
            if yt.length > 420:
                raise ValidationError(
                    _(
                        "%(value)s is longer than 7 minutes."
                        "Currently we are translating videos less than 7 minutes. Sorry!"
                    ),
                    params={"value": value},
                )
    else:
        raise ValidationError(
            _("%(value)s is not an valid link."),
            params={"value": value},
        )


def check_video_url(video_id):
    checker_url = "https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v="
    video_url = checker_url + video_id

    request = requests.get(video_url)

    if request.status_code == 200:
        return True
    return False
