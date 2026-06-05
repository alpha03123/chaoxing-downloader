from __future__ import annotations

import argparse
import itertools
import json
import sys

from .auth_init import DEFAULT_LOGIN_URL, DEFAULT_USER_DATA_DIR, InitError, run_browser_init
from .config import ConfigError, load_config
from .course_parser import parse_course_page
from .http_client import ChaoxingClient
from .media_resolver import resolve_media_status, resolve_media_url
from .session import SessionConfig
from .workflow import (
    WorkflowError,
    download_video,
    list_chapters,
    list_courses,
    list_videos,
    map_http_error,
    remove_cache,
)
from .models import AppConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chaoxing-downloader")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect-course", help="Inspect a Chaoxing course page")
    inspect_parser.add_argument("url")
    inspect_parser.add_argument("--cookie", required=True)
    inspect_parser.add_argument("--user-agent", required=False)
    inspect_parser.add_argument("--referer", required=False)

    list_courses_parser = subparsers.add_parser("list-courses", help="List courses from Chaoxing")
    list_courses_parser.add_argument("--url", required=False)
    list_courses_parser.add_argument("--config", required=False)

    list_chapters_parser = subparsers.add_parser("list-chapters", help="List chapters for a cached course")
    list_chapters_parser.add_argument("--course", required=True)
    list_chapters_parser.add_argument("--config", required=False)

    list_videos_parser = subparsers.add_parser("list-videos", help="List videos for a cached chapter")
    list_videos_parser.add_argument("--chapter", required=True)
    list_videos_parser.add_argument("--config", required=False)

    download_parser = subparsers.add_parser("download-video", help="Download a cached video")
    download_parser.add_argument("--video", required=True)
    download_parser.add_argument("--config", required=False)

    clear_cache_parser = subparsers.add_parser("clear-cache", help="Clear local cache")
    clear_cache_parser.add_argument("--config", required=False)

    init_parser = subparsers.add_parser("init", help="Login with browser and write config.toml")
    init_parser.add_argument("--config", required=False, default="config.toml")
    init_parser.add_argument("--user-data-dir", required=False, default=DEFAULT_USER_DATA_DIR)
    init_parser.add_argument("--login-url", required=False, default=DEFAULT_LOGIN_URL)
    init_parser.add_argument("--timeout", required=False, type=int, default=300)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "inspect-course":
            return _run_inspect_course(args)
        if args.command == "init":
            progress = _InitProgress()
            run_browser_init(
                config_path=args.config,
                user_data_dir=args.user_data_dir,
                login_url=args.login_url,
                timeout_seconds=args.timeout,
                progress=progress,
            )
            return 0
        if args.command == "clear-cache":
            config = _load_config_for_cache(getattr(args, "config", None))
            remove_cache(config)
            return 0
        config = load_config(getattr(args, "config", None))
        client = ChaoxingClient(SessionConfig(cookie=config.cookie, referer=config.referer))
        if args.command == "list-courses":
            records = list_courses(client, config, url_override=args.url or "")
            for item in records:
                print(f"[{item.course_key}] {item.title}")
            return 0
        if args.command == "list-chapters":
            records = list_chapters(client, config, course_key=args.course)
            for item in records:
                print(f"[{item.chapter_key}] {item.order} {item.title}".strip())
            return 0
        if args.command == "list-videos":
            records = list_videos(client, config, chapter_key=args.chapter)
            for item in records:
                print(f"[{item.video_key}] {item.title}")
            return 0
        if args.command == "download-video":
            progress = _DownloadProgress()
            path = download_video(client, config, video_key=args.video, progress=progress)
            progress.finish()
            print(path)
            return 0
    except (ConfigError, InitError, WorkflowError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(str(map_http_error(exc)), file=sys.stderr)
        return 1
    return 0


def _run_inspect_course(args: argparse.Namespace) -> int:
    config = SessionConfig(
        cookie=args.cookie,
        user_agent=args.user_agent or "",
        referer=args.referer or "",
    )
    client = ChaoxingClient(config)
    html = client.get_text(args.url)
    course = parse_course_page(html)
    media_url = ""
    media_status = None
    first_video = next((task for chapter in course.chapters for task in chapter.tasks if task.kind == "video"), None)
    if first_video and first_video.object_id:
        try:
            media_status = resolve_media_status(client, first_video.object_id)
            media_url = _pick_media_url(media_status)
        except ValueError:
            media_status = None
    if not media_url:
        try:
            media_url = resolve_media_url(html)
        except ValueError:
            pass
    payload = {
        "url": args.url,
        "course": {
            "title": course.title,
            "chapters": [
                {
                    "title": chapter.title,
                    "tasks": [
                        {
                            "title": task.title,
                            "kind": task.kind,
                            "status": task.status,
                            "media_url": task.media_url,
                            "object_id": task.object_id,
                            "job_id": task.job_id,
                            "mid": task.mid,
                        }
                        for task in chapter.tasks
                    ],
                }
                for chapter in course.chapters
            ],
        },
        "media_url": media_url,
        "media_status": media_status,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def _pick_media_url(status_payload: dict[str, object]) -> str:
    for key in ("http", "download"):
        value = status_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _load_config_for_cache(path: str | None) -> AppConfig:
    try:
        return load_config(path)
    except ConfigError:
        return AppConfig(cookie="", referer="", cache_path=".chaoxing-cache.json")


class _InitProgress:
    def __init__(self) -> None:
        self._spinner = itertools.cycle("|/-\\")
        self._last_inline = False

    def __call__(self, kind: str, message: str) -> None:
        if kind == "waiting":
            print(f"\r{next(self._spinner)} {message}", end="", flush=True)
            self._last_inline = True
            return
        if self._last_inline:
            print()
            self._last_inline = False
        prefix = {
            "start": "[init]",
            "checking": "[auth]",
            "courses": "[courses]",
            "course": "[course]",
            "course_cookie": "[entry]",
            "course_cookie_missing": "[entry]",
            "cookies": "[cookie]",
            "config": "[config]",
        }.get(kind, "[init]")
        print(f"{prefix} {message}", flush=True)


class _DownloadProgress:
    def __init__(self) -> None:
        self._last_inline = False

    def __call__(self, downloaded: int, total: int | None) -> None:
        if total:
            percent = downloaded / total * 100
            message = f"[download] {percent:6.2f}% {_format_size(downloaded)} / {_format_size(total)}"
        else:
            message = f"[download] {_format_size(downloaded)}"
        print(f"\r{message}", end="", flush=True)
        self._last_inline = True

    def finish(self) -> None:
        if self._last_inline:
            print()
            self._last_inline = False


def _format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}GB"
