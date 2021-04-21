from __future__ import unicode_literals

import html
import json
import os
import shutil
import tempfile
import uuid

import moviepy.editor as mp
from celery.signals import task_failure, task_postrun, task_prerun, task_success
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage, texttospeech
from google.cloud import translate_v2 as translate
from moviepy.editor import AudioFileClip, CompositeAudioClip, VideoFileClip
from pytube import YouTube, extract

from config import celery_app

from .models import Video

User = get_user_model()


@celery_app.task(soft_time_limit=10000)
def download_yt_video(my_id, link, targetLanguage, speakingVoice):
    my_user = User(id=my_id)
    video = Video(user=my_user, id=download_yt_video.request.id)

    credential_path = (
        "yt_video_translate/video_translator/env/translate-af9005978349.json"
    )
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credential_path

    yt = YouTube(f"{link}")
    yt_id = extract.video_id(f"{link}")

    temp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_silent_video = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)

    if os.path.exists(os.path.join(settings.MEDIA_ROOT, "temp")):
        shutil.rmtree(os.path.join(settings.MEDIA_ROOT, "temp"), ignore_errors=True)

    file_path = os.path.join(settings.MEDIA_ROOT, "temp")

    video.youtube_url = f"{link}"
    video.youtube_title = yt.title

    """Download Video and save it into a model"""
    file_content_video = downloadVideo(file_path, yt, yt_id)
    video.video_clip.save(f"{yt.title}.mp4", file_content_video)

    """Extract Audio from the Downloaded Video File"""
    # file_content_only_audio_save =
    audioFromVideo(f"{file_path}/{yt_id}.mp4", temp_audio)
    # video.audio_clip.save("audio.wav", file_content_only_audio_save)

    """Remove Audio from the Downloaded Video File"""
    # file_content_silent_video_save =
    removeAudioFromVideo(f"{file_path}/{yt_id}.mp4", temp_silent_video)
    # video.silent_video_clip.save(f"silent_{yt_id}.mp4", file_content_silent_video_save)

    """Translate Audio from One Language to another"""
    """EDIT AFTER DRAFT"""
    sourceLanguage = "en"
    targetLanguage = targetLanguage
    speakerCount = 2

    outputFile = translation_to_target_language(
        video,
        temp_audio,
        temp_silent_video,
        yt_id,
        sourceLanguage,
        file_path,
        targetLanguage,
        speakingVoice,
        [],
        speakerCount,
    )
    if outputFile:
        video.is_translated = True
        video.translated_video_clip.save("translated_video.mp4", outputFile)

    """Add the Translated Audio to the Silent Video"""
    # shutil.rmtree(file_path, ignore_errors=True)


def downloadVideo(file_path, yt, yt_id):
    """Download Video from a given YouTube Link and convert it into ContentFile.

    Args:
        file_path: Path to save the output file.
        yt: YouTube object we are working with.
        yt_id: YouTube ID of the object we are working with.

    Returns:
        ContentFile: Returns the file downloaded.
    """

    yt.streams.filter(progressive=True, file_extension="mp4").order_by(
        "resolution"
    ).desc().first().download(output_path=f"{file_path}", filename=f"{yt_id}")
    with open(f"{file_path}/{yt_id}.mp4", "rb") as fp:
        fp.seek(0)
        file_content_video = fp.read()
        fp.close()
    return ContentFile(file_content_video)


def audioFromVideo(video_file, temp_audio):
    """Extract Audio from the Downloaded Video File and convert it into ContentFile.

    Args:
        video_file: Video File to process and extract the audio from.
        temp_audio: Temporary location to store the audio after extracting from the video file.

    Returns:
        ContentFile: Returns the audio of the after extracting from the file downloaded.
    """
    mp.VideoFileClip(video_file).audio.write_audiofile(
        f"{temp_audio.name}", ffmpeg_params=["-ac", "1"]
    )
    with open(f"{temp_audio.name}", "rb") as fp1:
        fp1.seek(0)
        file_content_only_audio = fp1.read()
        fp1.close()
    return ContentFile(file_content_only_audio)


def removeAudioFromVideo(video_file, temp_silent_video):
    """Remove Audio from the Downloaded Video File"""
    mp.VideoFileClip(video_file).without_audio().write_videofile(
        f"{temp_silent_video.name}"
    )
    with open(f"{temp_silent_video.name}", "rb") as fp2:
        fp2.seek(0)
        file_content_silent_video = fp2.read()
        fp2.close()
    return ContentFile(file_content_silent_video)


def getTranscriptsInJSON(
    googleCloudStoragePath,
    languageCode,
    phraseHints=[],
    speakerCount=1,
    enhancedModel=None,
):
    """Transcribes audio files.
    Args:
        googleCloudStoragePath (String): path to file in cloud storage (i.e. "gs://audio/clip.mp4")
        languageCode (String): language code (i.e. "en-US", see https://cloud.google.com/speech-to-text/docs/languages)
        phraseHints (String[]): list of words that are unusual but likely to appear in the audio file.
        speakerCount (int, optional): Number of speakers in the audio. Only works on English. Defaults to None.
        enhancedModel (String, optional): Option to use an enhanced speech model, i.e. "video"
    Returns:
        list | Operation.error
    """

    def convertToJSON(result):
        json = []

        for section in result.results:
            data = {"transcript": section.alternatives[0].transcript, "words": []}
            for word in section.alternatives[0].words:
                data["words"].append(
                    {
                        "word": word.word,
                        "start_time": word.start_time.total_seconds(),
                        "end_time": word.end_time.total_seconds(),
                        "speaker_tag": word.speaker_tag,
                    }
                )
            if len(data["words"]) > 0:
                try:
                    data["words"].insert(0, data["words"][0])
                except IndexError:
                    pass
            json.append(data)
        return json

    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(uri=googleCloudStoragePath)

    # diarize = speakerCount if speakerCount > 1 else False
    # print(f"Diarizing: {diarize}")
    # diarizationConfig = speech.SpeakerDiarizationConfig(
    #     enable_speaker_diarization=speakerCount if speakerCount > 1 else False,
    # )

    # In English only, we can use the optimized video model
    if languageCode == "en":
        enhancedModel = "video"

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code="en-US" if languageCode == "en" else languageCode,
        enable_automatic_punctuation=True,
        enable_word_time_offsets=True,
        speech_contexts=[{"phrases": phraseHints, "boost": 15}],
        # diarization_config=diarizationConfig,
        profanity_filter=True,
        use_enhanced=True if enhancedModel else False,
        model="video" if enhancedModel else None,
        # enable_speaker_diarization=True,
        # audio_channel_count=2,
        # diarization_speaker_count=2,
        # enable_separate_recognition_per_channel=True,
        # max_alternatives=2
    )
    res = client.long_running_recognize(config=config, audio=audio).result()
    return convertToJSON(res)


def breakIntoSentences(json, language):
    """Takes json from getTranscriptsInJSON and breaks it into sentences
    spoken by a single person. Sentences deliniated by a >= 1 second pause/
    Args:
        json (string[]): [{"transcript": "lalala",
            "words": [{"word": "la", "start_time": 20,
                "end_time": 21, "speaker_tag: 2}]}]
        language (string): language code, i.e. "en"
    Returns:
        string[]: [{"sentence": "lalala", "speaker": 1, "start_time": 20, "end_time": 21}]
    """

    sentences = []
    sentence = {}
    for result in json:
        for i, word in enumerate(result["words"]):
            wordText = word["word"]
            if not sentence:
                sentence = {
                    language: [wordText],
                    "speaker": word["speaker_tag"],
                    "start_time": word["start_time"],
                    "end_time": word["end_time"],
                }
            elif word["speaker_tag"] != sentence["speaker"]:
                sentence[language] = " ".join(sentence[language])
                sentences.append(sentence)
                sentence = {
                    language: [wordText],
                    "speaker": word["speaker_tag"],
                    "start_time": word["start_time"],
                    "end_time": word["end_time"],
                }
            elif (
                ("." in word["word"])
                or (" ." in word["word"])
                or (". " in word["word"])
                or ("?" in word["word"])
                or (" ?" in word["word"])
                or ("? " in word["word"])
                or ("!" in word["word"])
                or (" !" in word["word"])
                or ("! " in word["word"])
            ):
                sentence[language].append(word["word"])
                sentence[language].pop(0)
                sentence[language] = " ".join(sentence[language])
                sentences.append(sentence)

                sentence = {
                    language: [wordText],
                    "speaker": word["speaker_tag"],
                    "start_time": word["start_time"],
                    "end_time": word["end_time"],
                }
            else:
                sentence[language].append(wordText)
                sentence["end_time"] = word["end_time"]
        if sentence:
            sentence[language].pop(0)
            sentence[language] = " ".join(sentence[language])
            sentences.append(sentence)
            sentence = {}

    return_sentences = []
    for sentence in sentences:
        if sentence[language] != "":
            return_sentences.append(sentence)
    return return_sentences


def translate_text(input, targetLanguage, sourceLang=None):
    """Translates from sourceLang to targetLanguage. If sourceLang is empty,
    it will be auto-detected.
    Args:
        sentence (String): Sentence to translate
        targetLanguage (String): i.e. "en"
        sourceLang (String, optional): i.e. "es" Defaults to None.
    Returns:
        String: translated text
    """

    translate_client = translate.Client()
    result = translate_client.translate(
        input, target_language=targetLanguage, source_language=sourceLang
    )

    return html.unescape(result["translatedText"])


def speak(text, languageCode, voiceName=None, speakingRate=1):
    """Converts text to audio
    Args:
        text (String): Text to be spoken
        languageCode (String): Language (i.e. "en")
        voiceName: (String, optional): See https://cloud.google.com/text-to-speech/docs/voices
        speakingRate: (int, optional): speed up or slow down speaking
    Returns:
        bytes : Audio in wav format
    """

    # Instantiates a client
    client = texttospeech.TextToSpeechClient()

    # Set the text input to be synthesized
    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Build the voice request, select the language code ("en-US") and the ssml
    # voice gender ("neutral")
    if not voiceName:
        voice = texttospeech.VoiceSelectionParams(
            language_code=languageCode, ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
    else:
        voice = texttospeech.VoiceSelectionParams(
            language_code=languageCode, name=voiceName
        )

    # Select the type of audio file you want returned
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=speakingRate
    )

    # Perform the text-to-speech request on the text input with the selected
    # voice parameters and audio file type
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    return response.audio_content


def speakUnderDuration(text, languageCode, file_path, durationSecs, voiceName=None):
    """Speak text within a certain time limit.
    If audio already fits within duratinSecs, no changes will be made.
    Args:
        text (String): Text to be spoken
        languageCode (String): language code, i.e. "en"
        durationSecs (int): Time limit in seconds
        voiceName (String, optional): See https://cloud.google.com/text-to-speech/docs/voices
    Returns:
        bytes : Audio in wav format
        :param voiceName:
        :param text:
        :param languageCode:
        :param durationSecs:
        :param file_path:
    """
    baseAudio = speak(text, languageCode, voiceName=voiceName)

    temporary_file_path = os.path.join(file_path, "output" + ".mp3")
    with open(temporary_file_path, "wb") as out:
        out.write(baseAudio)
    baseDuration = AudioFileClip(f"{temporary_file_path}").duration
    os.remove(temporary_file_path)

    try:
        ratio = baseDuration / durationSecs
    except ZeroDivisionError:
        ratio = 1

    if ratio < 0.95:
        ratio = 0.95
    elif ratio > 1.05 and ratio <= 1.21:
        ratio = ratio + 0.09
    elif ratio > 1.3 and ratio <= 1.4:
        ratio = 1.35
    elif ratio > 1.4:
        ratio = 1.4
    else:
        return baseAudio
    return speak(text, languageCode, voiceName=voiceName, speakingRate=ratio)


def translation_to_target_language(
    video,
    temp_audio,
    temp_silent_video,
    yt_id,
    sourceLanguage,
    file_path,
    targetLanguage,
    voices={},
    phraseHints=[],
    speakerCount=1,
):
    storageBucket = "translate-001"
    storage_client = storage.Client()
    bucket = storage_client.bucket(storageBucket)
    temp_file = os.path.join("tmp", str(uuid.uuid4()) + ".wav")
    blob = bucket.blob(temp_file)

    blob.upload_from_file(temp_audio)

    transcripts = getTranscriptsInJSON(
        os.path.join("gs://", storageBucket, temp_file),
        sourceLanguage,
        phraseHints=phraseHints,
        speakerCount=speakerCount,
    )
    json.dump(transcripts, open(os.path.join(file_path, "transcript.json"), "w"))

    sentences = breakIntoSentences(transcripts, sourceLanguage)

    fn = os.path.join(file_path, f"{yt_id}" + ".json")
    with open(fn, "w") as f:
        json.dump(sentences, f)

    blob.delete()

    sentences = json.load(open(fn))

    for sentence in sentences:
        sentence[targetLanguage] = translate_text(
            sentence[sourceLanguage], targetLanguage, sourceLanguage
        )

    with open(fn, "w") as f:
        json.dump(sentences, f)

    audioDirectory = os.path.join(file_path, "audioDirectory")
    os.mkdir(audioDirectory)
    languageDirectory = os.path.join(audioDirectory, targetLanguage)
    os.mkdir(languageDirectory)

    for i, sentence in enumerate(sentences):
        voiceName = voices[targetLanguage] if targetLanguage in voices else None
        audio = speakUnderDuration(
            sentence[targetLanguage],
            targetLanguage,
            file_path,
            (sentence["end_time"] - sentence["start_time"]),
            voiceName=voiceName,
        )
        with open(os.path.join(languageDirectory, f"{i}.mp3"), "wb") as f:
            f.write(audio)

    translatedDirectory = os.path.join(file_path, "translatedVideos")
    os.mkdir(translatedDirectory)
    outputFile = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)

    audioFiles = os.listdir(languageDirectory)
    audioFiles.sort(key=lambda x: int(x.split(".")[0]))

    segments = []

    for i, sentence in enumerate(sentences):
        audio_file = os.path.join(languageDirectory, f"{i}.mp3")
        segments.append(AudioFileClip(audio_file).set_start(sentence["start_time"]))

    dubbed = CompositeAudioClip(segments)

    clip = VideoFileClip(f"{temp_silent_video.name}")
    clip = clip.set_audio(dubbed)

    clip.write_videofile(f"{outputFile.name}", codec="libx264", audio_codec="aac")
    with open(f"{outputFile.name}", "rb") as fp:
        fp.seek(0)
        output = fp.read()
        fp.close()
    return ContentFile(output)


@task_prerun.connect(sender=download_yt_video)
def task_prerun_notifier(sender=None, **kwargs):
    print(
        "From task_prerun_notifier ==> Running just before download_yt_video() executes"
    )


@task_postrun.connect(sender=download_yt_video)
def task_postrun_notifier(sender=None, **kwargs):
    print("From task_postrun_notifier ==> Ok, done!")


@task_failure.connect(sender=download_yt_video)
def task_failure_notifier(sender=None, **kwargs):
    print("From task_failure_notifier ==> Task failed!")


@task_success.connect(sender=download_yt_video)
def task_success_notifier(sender=None, **kwargs):
    sender.request.id
    print("From task_success_notifier ==> Task run successfully!")
