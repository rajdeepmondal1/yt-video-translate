from storages.backends.gcloud import GoogleCloudStorage
from whitenoise.storage import (  # CompressedManifestStaticFilesStorage,; CompressedStaticFilesStorage,
    CompressedManifestStaticFilesStorage,
)


class StaticRootGoogleCloudStorage(GoogleCloudStorage):
    location = "static"
    default_acl = "publicRead"


class MediaRootGoogleCloudStorage(GoogleCloudStorage):
    location = "media"
    file_overwrite = False


class WhiteNoiseStaticFilesStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False


# class WhiteNoiseStaticFilesStorage(CompressedStaticFilesStorage):
#     manifest_strict = False
