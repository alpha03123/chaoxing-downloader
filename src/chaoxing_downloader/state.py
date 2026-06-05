from __future__ import annotations

import json
from pathlib import Path

from .auth_init import DEFAULT_BASE_URL, DEFAULT_REFERER
from .cache_store import save_cache
from .models import AppConfig, CacheState, CourseRecord


class StatePaths:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.browser = root / "browser"
        self.session = root / "session.json"
        self.cache = root / "cache.json"
        self.downloads = root / "downloads"

    @classmethod
    def from_dir(cls, state_dir: str) -> "StatePaths":
        return cls(Path(state_dir))


def make_config_from_state(cookie: str, paths: StatePaths) -> AppConfig:
    return AppConfig(
        cookie=cookie,
        referer=DEFAULT_REFERER,
        base_url=DEFAULT_BASE_URL,
        output_dir=str(paths.downloads),
        cache_path=str(paths.cache),
    )


def save_state(paths: StatePaths, config: AppConfig, warmed_courses: list[CourseRecord]) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    save_session(paths.session, config)
    save_cache(str(paths.cache), CacheState(courses=warmed_courses))


def save_session(path: Path, config: AppConfig) -> None:
    path.write_text(
        json.dumps(
            {
                "cookie": config.cookie,
                "referer": config.referer,
                "base_url": config.base_url,
                "output_dir": Path(config.output_dir).name,
                "cache_path": Path(config.cache_path).name,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def load_config_from_state(paths: StatePaths) -> AppConfig:
    if not paths.session.exists():
        raise FileNotFoundError(f"找不到会话文件 {paths.session}，请先调用 ChaoxingDownloader.init()")
    payload = json.loads(paths.session.read_text(encoding="utf-8"))
    cache_path = str(payload.get("cache_path") or "cache.json")
    output_dir = str(payload.get("output_dir") or "downloads")
    return AppConfig(
        cookie=str(payload.get("cookie", "")),
        referer=str(payload.get("referer") or DEFAULT_REFERER),
        base_url=str(payload.get("base_url") or DEFAULT_BASE_URL),
        output_dir=str(paths.root / output_dir) if not Path(output_dir).is_absolute() else output_dir,
        cache_path=str(paths.root / cache_path) if not Path(cache_path).is_absolute() else cache_path,
    )
