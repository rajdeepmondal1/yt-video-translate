import uuid

from django.db import models

from yt_video_translate.users.models import User


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return f"user_{instance.user.id}/video_{instance.id}/{filename}"


# Create your models here.
class Video(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    youtube_url = models.TextField()
    youtube_title = models.CharField(max_length=255, blank=True)
    video_clip = models.FileField(
        upload_to=user_directory_path, null=True, verbose_name=""
    )
    silent_video_clip = models.FileField(
        upload_to=user_directory_path, null=True, verbose_name=""
    )
    audio_clip = models.FileField(
        upload_to=user_directory_path, null=True, verbose_name=""
    )
    translated_audio_clip = models.FileField(
        upload_to=user_directory_path, null=True, verbose_name=""
    )
    translated_video_clip = models.FileField(
        upload_to=user_directory_path, null=True, verbose_name=""
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.youtube_title)
