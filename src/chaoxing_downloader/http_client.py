from __future__ import annotations

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
