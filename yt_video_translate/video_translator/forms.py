from django import forms

from .models import Video


class Video_form(forms.ModelForm):
    youtube_url = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Enter YouTube Link..."}),
        label=False,
    )

    class Meta:
        model = Video
        fields = ("youtube_url",)
