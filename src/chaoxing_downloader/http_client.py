from __future__ import annotations

from collections.abc import Iterator

import httpx

from .session import SessionConfig, build_headers


class ChaoxingClient:
    def __init__(self, config: SessionConfig, *, transport: httpx.BaseTransport | None = None) -> None:
        self._client = httpx.Client(headers=build_headers(config), timeout=20, follow_redirects=True, transport=transport)

    def get_text(self, url: str) -> str:
        response = self._client.get(url)
        response.raise_for_status()
        return response.text

    def get_text_with_url(self, url: str) -> tuple[str, str]:
        response = self._client.get(url)
        response.raise_for_status()
        return response.text, str(response.url)

    def get_json(self, url: str, *, params: dict[str, str] | None = None) -> object:
        response = self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def post_text(
        self,
        url: str,
        *,
        data: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> str:
        response = self._client.post(url, data=data, params=params)
        response.raise_for_status()
        return response.text

    def get_bytes(self, url: str) -> bytes:
        response = self._client.get(url)
        response.raise_for_status()
        return response.content

    def iter_bytes(self, url: str, *, chunk_size: int = 1024 * 1024) -> Iterator[tuple[bytes, int | None]]:
        with self._client.stream("GET", url) as response:
            response.raise_for_status()
            total = _content_length(response.headers.get("Content-Length"))
            for chunk in response.iter_bytes(chunk_size=chunk_size):
                if chunk:
                    yield chunk, total


def _content_length(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
