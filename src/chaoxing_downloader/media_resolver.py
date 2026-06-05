from __future__ import annotations

import json
import re

from .http_client import ChaoxingClient


def resolve_media_url(html: str) -> str:
    match = re.search(r'https://[^"]+\.m3u8', html)
    if match:
        return match.group(0)

    json_match = re.search(r'window\.__DATA__\s*=\s*(\{.*?\})\s*;', html, re.S)
    if json_match:
        payload = json.loads(json_match.group(1))
        video = payload.get("video")
        if isinstance(video, str) and video:
            return video

    raise ValueError("未找到可下载媒体地址")


def resolve_media_status(client: ChaoxingClient, object_id: str) -> dict[str, object]:
    if not object_id.strip():
        raise ValueError("缺少 object_id")
    payload = client.get_json(f"https://mooc1.chaoxing.com/ananas/status/{object_id.strip()}")
    if not isinstance(payload, dict):
        raise ValueError("视频状态接口未返回对象")
    status = payload.get("status")
    if status != "success":
        raise ValueError(f"视频状态接口返回异常: {status}")
    return payload
