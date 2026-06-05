from __future__ import annotations

import tomllib
from pathlib import Path

from .models import AppConfig


class ConfigError(ValueError):
    pass


def load_config(path: str | None = None) -> AppConfig:
    config_path = Path(path or "config.toml")
    if not config_path.exists():
        raise ConfigError(f"错误：找不到配置文件 {config_path.name}，请先创建配置文件")
    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"错误：配置文件格式不合法：{exc}") from exc

    session = payload.get("session")
    if not isinstance(session, dict):
        raise ConfigError("错误：config.toml 缺少 session.cookie")
    cookie = _required_text(session.get("cookie"), "错误：config.toml 缺少 session.cookie")
    referer = _required_text(session.get("referer"), "错误：config.toml 缺少 session.referer")

    entry = payload.get("entry")
    base_url = entry.get("base_url", "") if isinstance(entry, dict) else ""

    download = payload.get("download")
    output_dir = download.get("output_dir", "downloads") if isinstance(download, dict) else "downloads"

    cache = payload.get("cache")
    cache_path = cache.get("path", ".chaoxing-cache.json") if isinstance(cache, dict) else ".chaoxing-cache.json"

    return AppConfig(
        cookie=cookie,
        referer=referer,
        base_url=str(base_url).strip(),
        output_dir=str(output_dir).strip() or "downloads",
        cache_path=str(cache_path).strip() or ".chaoxing-cache.json",
    )


def _required_text(value: object, message: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(message)
    return value.strip()
