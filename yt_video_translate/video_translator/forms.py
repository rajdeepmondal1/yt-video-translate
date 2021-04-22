from django import forms

from .choices import LANGUAGE_CHOICES, VOICE_CHOICES
from .models import Video
from .validators import validate_youtube_url


class Video_form(forms.ModelForm):
    youtube_url = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Enter YouTube Link..."}),
        label=False,
        validators=[validate_youtube_url],
    )
    language = forms.ChoiceField(required=True, label=False, choices=LANGUAGE_CHOICES)
    voice = forms.ChoiceField(required=True, label=False, choices=VOICE_CHOICES)

    class Meta:
        model = Video
        fields = ("youtube_url",)
