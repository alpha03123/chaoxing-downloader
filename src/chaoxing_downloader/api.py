from __future__ import annotations

from pathlib import Path
import time
from typing import Callable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .auth_init import DEFAULT_LOGIN_URL, CancelCheck, InitCancelled, collect_cookie_header_with_browser, is_logged_in_home_page
from .http_client import ChaoxingClient
from .models import AppConfig, ChapterRecord, CourseRecord, VideoRecord
from .session import SessionConfig
from .state import StatePaths, load_config_from_state, make_config_from_state, save_state
from .workflow import DownloadProgress, download_video, list_chapters, list_courses, list_videos


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
    def init(
        cls,
        *,
        state_dir: str = ".chaoxing",
        timeout_seconds: int = 300,
        login_url: str = DEFAULT_LOGIN_URL,
        cancel_check: CancelCheck | None = None,
        collect_impl: Callable[..., tuple[str, list[CourseRecord]]] = collect_cookie_header_with_browser,
    ) -> "ChaoxingDownloader":
        if cancel_check is not None and cancel_check():
            raise InitCancelled("初始化已取消")
        paths = StatePaths.from_dir(state_dir)
        paths.root.mkdir(parents=True, exist_ok=True)
        cookie, warmed_courses = collect_impl(
            user_data_dir=str(paths.browser),
            login_url=login_url,
            timeout_seconds=timeout_seconds,
            progress=None,
            cancel_check=cancel_check,
        )
        config = make_config_from_state(cookie, paths)
        save_state(paths, config, warmed_courses)
        return cls(config)

    @classmethod
    def load(cls, *, state_dir: str = ".chaoxing") -> "ChaoxingDownloader":
        return cls(load_config_from_state(StatePaths.from_dir(state_dir)))

    @classmethod
    def is_initialized(cls, *, state_dir: str = ".chaoxing") -> bool:
        try:
            config = load_config_from_state(StatePaths.from_dir(state_dir))
            client = ChaoxingClient(SessionConfig(cookie=config.cookie, referer=config.referer))
            url = _entry_url_with_dynamic_params(config.base_url)
            return is_logged_in_home_page(url, client.get_text(url))
        except Exception:
            return False

    def list_courses(self, *, url: str = "") -> list[CourseRecord]:
        return self._list_courses(self.client, self.config, url_override=url)

    def list_chapters(self, course_key: str) -> list[ChapterRecord]:
        return self._list_chapters(self.client, self.config, course_key=course_key)

    def list_videos(self, chapter_key: str) -> list[VideoRecord]:
        return self._list_videos(self.client, self.config, chapter_key=chapter_key)

    def download_video(
        self,
        video_key: str,
        *,
        output_dir: str | Path | None = None,
        filename: str | None = None,
        progress: DownloadProgress | None = None,
    ) -> Path:
        return self._download_video(
            self.client,
            self.config,
            video_key=video_key,
            output_dir=output_dir,
            filename=filename,
            progress=progress,
        )


def _entry_url_with_dynamic_params(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc != "i.chaoxing.com" or parsed.path != "/base":
        return url
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params.setdefault("ws", "1")
    params["t"] = str(int(time.time() * 1000))
    return urlunparse(parsed._replace(query=urlencode(params)))
