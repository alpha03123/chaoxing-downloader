from __future__ import annotations

from dataclasses import dataclass


DEFAULT_USER_AGENT = "Mozilla/5.0"


@dataclass(frozen=True)
class SessionConfig:
    cookie: str
    user_agent: str = DEFAULT_USER_AGENT
    referer: str = ""


def build_headers(config: SessionConfig) -> dict[str, str]:
    headers = {
        "Cookie": config.cookie.strip(),
        "User-Agent": config.user_agent.strip() or DEFAULT_USER_AGENT,
    }
    referer = config.referer.strip()
    if referer:
        headers["Referer"] = referer
    return headers
