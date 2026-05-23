from typing import assert_never

from app.config import Settings
from app.db.models.enums import SourceType
from app.db.models.job import Job
from app.services.source.base import SourceProvider
from app.services.source.local_upload import LocalUploadProvider
from app.services.source.ytdlp_downloader import YtDlpDownloader


def get_source_provider(job: Job, settings: Settings) -> SourceProvider:
    match job.source_type:
        case SourceType.upload:
            return LocalUploadProvider(settings)
        case SourceType.url:
            return YtDlpDownloader(settings)
        case _:
            assert_never(job.source_type)
