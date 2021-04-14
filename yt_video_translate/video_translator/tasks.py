from __future__ import unicode_literals

import glob
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
def download_yt_video(my_id, link):
    my_user = User(id=my_id)
    video = Video(user=my_user)

    credential_path = (
        "yt_video_translate/video_translator/env/translate-af9005978349.json"
    )
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credential_path
    # os.environ['STORAGE_BUCKET'] = "translate-001"

    yt = YouTube(f"{link}")
    yt_id = extract.video_id(f"{link}")

    temp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_silent_video = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)

    if os.path.exists(os.path.join(settings.MEDIA_ROOT, "temp")):
        shutil.rmtree(os.path.join(settings.MEDIA_ROOT, "temp"), ignore_errors=True)

    file_path = os.path.join(settings.MEDIA_ROOT, "temp")
    # storageBucket = "translate-001"
    # storage_client = storage.Client()
    # bucket = storage_client.bucket(storageBucket)

    video.youtube_url = f"{link}"
    video.youtube_title = yt.title

    """Download Video and save it into a model"""
    file_content_video = downloadVideo(file_path, yt, yt_id)  # file_path
    video.video_clip.save(f"{yt.title}.mp4", file_content_video)

    """Extract Audio from the Downloaded Video File"""
    file_content_only_audio_save = audioFromVideo(
        f"{file_path}/{yt_id}.mp4", temp_audio
    )
    video.audio_clip.save("audio.wav", file_content_only_audio_save)

    """Remove Audio from the Downloaded Video File"""
    file_content_silent_video_save = removeAudioFromVideo(
        f"{file_path}/{yt_id}.mp4", temp_silent_video
    )
    video.silent_video_clip.save(f"silent_{yt_id}.mp4", file_content_silent_video_save)

    """Translate Audio from One Language to another"""
    """EDIT AFTER DRAFT"""
    srcLang = "en"
    targetLang = "bn"
    speakerCount = 2
    # bn - IN - Wavenet - A

    # hi - IN - Wavenet - C
    # "bn": "bn-IN-Wavenet-B"
    # "hi": "hi-IN-Wavenet-C"
    outFile = translation_to_target_language(
        video,
        temp_audio,
        temp_silent_video,
        yt_id,
        srcLang,
        file_path,
        targetLang,
        {"hi": "hi-IN-Wavenet-C"},
        [],
        speakerCount,
    )

    video.translated_video_clip.save("translated_video.mp4", outFile)

    """END OF EDIT AFTER DRAFT"""

    """Add the Translated Audio to the Silent Video"""

    # USE IT AFTER TEST
    shutil.rmtree(file_path, ignore_errors=True)


def downloadVideo(file_path, yt, yt_id):
    """Download Video and save it into a model"""
    yt.streams.filter(progressive=True, file_extension="mp4").order_by(
        "resolution"
    ).desc().first().download(output_path=f"{file_path}", filename=f"{yt_id}")
    with open(f"{file_path}/{yt_id}.mp4", "rb") as fp:
        fp.seek(0)
        file_content_video = fp.read()
        fp.close()
    return ContentFile(file_content_video)


def audioFromVideo(video_file, temp_audio):
    """Extract Audio from the Downloaded Video File"""
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


def get_transcripts_json(
    gcsPath, langCode, phraseHints=[], speakerCount=1, enhancedModel=None
):
    """Transcribes audio files.
    Args:
        gcsPath (String): path to file in cloud storage (i.e. "gs://audio/clip.mp4")
        langCode (String): language code (i.e. "en-US", see https://cloud.google.com/speech-to-text/docs/languages)
        phraseHints (String[]): list of words that are unusual but likely to appear in the audio file.
        speakerCount (int, optional): Number of speakers in the audio. Only works on English. Defaults to None.
        enhancedModel (String, optional): Option to use an enhanced speech model, i.e. "video"
    Returns:
        list | Operation.error
    """

    def _jsonify(result):
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
            json.append(data)
        return json

    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(uri=gcsPath)

    # diarize = speakerCount if speakerCount > 1 else False
    # print(f"Diarizing: {diarize}")
    # diarizationConfig = speech.SpeakerDiarizationConfig(
    #     enable_speaker_diarization=speakerCount if speakerCount > 1 else False,
    # )

    # In English only, we can use the optimized video model
    if langCode == "en":
        enhancedModel = "video"

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code="en-US" if langCode == "en" else langCode,
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

    _first_words = []
    for _result in res.results:
        for _word in _result.alternatives[0].words:
            _first_words.append(_word)
            break
    # first_words_reversed = first_words[::-1]
    print("first_words", _first_words[::-1], len(_first_words) - 1)
    return _jsonify(res)


def parse_sentence_2nd_try(json, lang):
    """Takes json from get_transcripts_json and breaks it into sentences
    spoken by a single person. Sentences deliniated by a >= 1 second pause/
    Args:
        json (string[]): [{"transcript": "lalala",
            "words": [{"word": "la", "start_time": 20,
                "end_time": 21, "speaker_tag: 2}]}]
        lang (string): language code, i.e. "en"
    Returns:
        string[]: [{"sentence": "lalala", "speaker": 1, "start_time": 20, "end_time": 21}]
    """

    sentences = []
    sentence = {}
    for result in json:
        for i, word in enumerate(result["words"]):
            wordText = word["word"]  # get_word(word['word'], lang)
            if not sentence:
                sentence = {
                    lang: [wordText],
                    "speaker": word["speaker_tag"],
                    "start_time": word["start_time"],
                    "end_time": word["end_time"],
                }
            elif word["speaker_tag"] != sentence["speaker"]:
                sentence[lang] = " ".join(sentence[lang])
                sentences.append(sentence)
                sentence = {
                    lang: [wordText],
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
                sentence[lang].append(word["word"])
                sentence[lang].pop(0)
                sentence[lang] = " ".join(sentence[lang])
                sentences.append(sentence)

                sentence = {
                    lang: [wordText],
                    "speaker": word["speaker_tag"],
                    "start_time": word["start_time"],
                    "end_time": word["end_time"],
                }
            else:
                sentence[lang].append(wordText)
                sentence["end_time"] = word["end_time"]
        if sentence:
            sentence[lang].pop(0)
            sentence[lang] = " ".join(sentence[lang])
            sentences.append(sentence)
            sentence = {}

    return_sentences = []
    for sentence in sentences:
        if sentence[lang] != "":
            return_sentences.append(sentence)
    return return_sentences


def translate_text(input, targetLang, sourceLang=None):
    """Translates from sourceLang to targetLang. If sourceLang is empty,
    it will be auto-detected.
    Args:
        sentence (String): Sentence to translate
        targetLang (String): i.e. "en"
        sourceLang (String, optional): i.e. "es" Defaults to None.
    Returns:
        String: translated text
    """

    translate_client = translate.Client()
    result = translate_client.translate(
        input, target_language=targetLang, source_language=sourceLang
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
        ratio = ratio - 0.05
    elif ratio > 1.05:
        ratio = ratio + 0.09
    else:
        return baseAudio
    return speak(text, languageCode, voiceName=voiceName, speakingRate=ratio)
    # return speak(text, languageCode, voiceName=voiceName)


def translation_to_target_language(
    video,
    temp_audio,
    temp_silent_video,
    yt_id,
    srcLang,
    file_path,
    targetLang,
    voices={},
    phraseHints=[],
    speakerCount=1,
):
    # storageBucket = storageBucket if storageBucket else os.environ['STORAGE_BUCKET']
    storageBucket = "translate-001"
    storage_client = storage.Client()
    bucket = storage_client.bucket(storageBucket)
    tmpFile = os.path.join("tmp", str(uuid.uuid4()) + ".wav")
    blob = bucket.blob(tmpFile)

    blob.upload_from_file(temp_audio)

    transcripts = get_transcripts_json(
        os.path.join("gs://", storageBucket, tmpFile),
        srcLang,
        phraseHints=phraseHints,
        speakerCount=speakerCount,
    )
    # transcripts = parse_sentence_2nd_try(os.path.join(
    #     "gs://", storageBucket, tmpFile), srcLang,
    #     phraseHints=phraseHints,
    #     speakerCount=speakerCount, )
    json.dump(transcripts, open(os.path.join(file_path, "transcript.json"), "w"))

    # sentences = parse_sentence_with_speaker(transcripts, srcLang)
    sentences = parse_sentence_2nd_try(transcripts, srcLang)

    fn = os.path.join(file_path, f"{yt_id}" + ".json")
    with open(fn, "w") as f:
        json.dump(sentences, f)

    blob.delete()

    sentences = json.load(open(fn))

    for sentence in sentences:
        sentence[targetLang] = translate_text(sentence[srcLang], targetLang, srcLang)

    with open(fn, "w") as f:
        json.dump(sentences, f)

    audioDir = os.path.join(file_path, "audioClips")
    os.mkdir(audioDir)
    languageDir = os.path.join(audioDir, targetLang)
    os.mkdir(languageDir)

    for i, sentence in enumerate(sentences):
        voiceName = voices[targetLang] if targetLang in voices else None
        audio = speakUnderDuration(
            sentence[targetLang],
            targetLang,
            file_path,
            (sentence["end_time"] - sentence["start_time"]),
            voiceName=voiceName,
        )
        with open(os.path.join(languageDir, f"{i}.mp3"), "wb") as f:
            f.write(audio)

    translatedDir = os.path.join(file_path, "translatedVideos")
    os.mkdir(translatedDir)
    outFile = os.path.join(translatedDir, targetLang + ".mp4")

    audioFiles = os.listdir(languageDir)
    audioFiles.sort(key=lambda x: int(x.split(".")[0]))

    segments = []

    for i, sentence in enumerate(sentences):
        audio_file = os.path.join(languageDir, f"{i}.mp3")
        segments.append(AudioFileClip(audio_file).set_start(sentence["start_time"]))

    dubbed = CompositeAudioClip(segments)

    clip = VideoFileClip(f"{temp_silent_video.name}")
    clip = clip.set_audio(dubbed)

    clip.write_videofile(outFile, codec="libx264", audio_codec="aac")
    with open(f"{outFile}", "rb") as fp:
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


def upload_local_directory_to_gcs(local_path, bucket, gcs_path):
    # assert os.path.isdir(local_path)
    for local_file in glob.glob(local_path + "/**"):
        if not os.path.isfile(local_file):
            upload_local_directory_to_gcs(
                local_file, bucket, gcs_path + "/" + os.path.basename(local_file)
            )
        else:
            my_local_file_len = 1 + len(local_path)
            my_local_file = local_file[my_local_file_len:]
            remote_path = os.path.join(gcs_path, my_local_file)
            blob = bucket.blob(remote_path)
            blob.upload_from_filename(local_file)


# upload_local_directory_to_gcs(local_path, bucket, BUCKET_FOLDER_DIR)
