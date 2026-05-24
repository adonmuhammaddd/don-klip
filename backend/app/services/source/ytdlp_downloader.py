import asyncio
from pathlib import Path
from typing import Any

import yt_dlp

from app.config import Settings
from app.db.models.job import Job
from app.services.errors import SourceError
from app.services.source.base import AcquiredSource, SourceProvider


class YtDlpDownloader(SourceProvider):
    """Download video dari YouTube/Twitch VOD via yt-dlp (best quality <=1080p)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def acquire(self, job: Job) -> AcquiredSource:
        if job.source_url is None:
            raise SourceError("url job tidak punya source_url")

        out_dir = Path(self._settings.uploads_dir) / str(job.id)
        # yt-dlp + mkdir blocking → jalankan di thread biar tidak block event loop.
        return await asyncio.to_thread(self._download, job.source_url, out_dir)

    def _download(self, url: str, out_dir: Path) -> AcquiredSource:
        out_dir.mkdir(parents=True, exist_ok=True)
        # Prioritaskan H.264 (avc1) + AAC supaya bisa di-preview di browser (Safari
        # tidak bisa decode AV1/Opus). Fallback bertahap kalau tidak tersedia.
        opts: dict[str, Any] = {
            "format": (
                "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
                "best[height<=1080][ext=mp4][vcodec^=avc1]/"
                "bestvideo[height<=1080]+bestaudio/"
                "best[height<=1080]/best"
            ),
            "outtmpl": str(out_dir / "source.%(ext)s"),
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
        }
        if self._settings.yt_dlp_cookies:
            opts["cookiefile"] = self._settings.yt_dlp_cookies

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                source_path = Path(ydl.prepare_filename(info))
        except yt_dlp.utils.DownloadError as exc:
            raise SourceError(f"yt-dlp gagal download: {exc}") from exc

        # merge_output_format bisa mengubah ekstensi final jadi .mp4.
        if not source_path.is_file():
            merged = source_path.with_suffix(".mp4")
            if merged.is_file():
                source_path = merged

        extractor = str(info.get("extractor", ""))
        twitch_video_id = str(info["id"]) if extractor.startswith("twitch") else None

        return AcquiredSource(
            source_path=str(source_path),
            original_filename=str(info.get("title") or source_path.name),
            twitch_video_id=twitch_video_id,
        )
