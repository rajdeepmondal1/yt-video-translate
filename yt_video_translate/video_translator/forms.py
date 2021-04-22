from django import forms
from django.core.validators import RegexValidator

from .choices import LANGUAGE_CHOICES, VOICE_CHOICES
from .models import Video


class Video_form(forms.ModelForm):
    regex = (
        (
            r"^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))"
            r"(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$"
        ),
    )
    valid_regex = RegexValidator(
        regex=regex,
        message="Please Enter a valid Youtube Link.",
    )
    youtube_url = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Enter YouTube Link..."}),
        label=False,
        validators=[valid_regex],
    )
    language = forms.ChoiceField(required=True, label=False, choices=LANGUAGE_CHOICES)
    voice = forms.ChoiceField(required=True, label=False, choices=VOICE_CHOICES)

    class Meta:
        model = Video
        fields = ("youtube_url",)
