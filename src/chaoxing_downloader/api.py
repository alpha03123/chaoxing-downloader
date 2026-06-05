from __future__ import annotations

from pathlib import Path
from typing import Callable

from .config import load_config
from .http_client import ChaoxingClient
from .models import AppConfig, ChapterRecord, CourseRecord, VideoRecord
from .session import SessionConfig
from .workflow import download_video, list_chapters, list_courses, list_videos


class ChaoxingDownloader:
    """Stable public API for using chaoxing-downloader as a library."""

    def __init__(
        self,
        config: AppConfig,
        *,
        client: object | None = None,
        list_courses_impl: Callable[..., list[CourseRecord]] = list_courses,
        list_chapters_impl: Callable[..., list[ChapterRecord]] = list_chapters,
        list_videos_impl: Callable[..., list[VideoRecord]] = list_videos,
        download_video_impl: Callable[..., Path] = download_video,
    ) -> None:
        self.config = config
        self.client = client or ChaoxingClient(SessionConfig(cookie=config.cookie, referer=config.referer))
        self._list_courses = list_courses_impl
        self._list_chapters = list_chapters_impl
        self._list_videos = list_videos_impl
        self._download_video = download_video_impl

    @classmethod
    def from_config(cls, path: str | None = None) -> "ChaoxingDownloader":
        return cls(load_config(path))

    def list_courses(self, *, url: str = "") -> list[CourseRecord]:
        return self._list_courses(self.client, self.config, url_override=url)

    def list_chapters(self, course_key: str) -> list[ChapterRecord]:
        return self._list_chapters(self.client, self.config, course_key=course_key)

    def list_videos(self, chapter_key: str) -> list[VideoRecord]:
        return self._list_videos(self.client, self.config, chapter_key=chapter_key)

    def download_video(self, video_key: str) -> Path:
        return self._download_video(self.client, self.config, video_key=video_key)


def load_downloader(path: str | None = None) -> ChaoxingDownloader:
    return ChaoxingDownloader.from_config(path)
