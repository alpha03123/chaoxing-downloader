from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import CacheState, ChapterRecord, CourseRecord, VideoRecord


class CacheError(ValueError):
    pass


def load_cache(path: str) -> CacheState:
    cache_path = Path(path)
    if not cache_path.exists():
        raise CacheError("错误：缓存文件不存在，请先运行上一级命令")
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CacheError("错误：缓存文件格式损坏，请运行 clear-cache 后重新解析") from exc
    return CacheState(
        courses=[CourseRecord(**_normalize_course_payload(item)) for item in payload.get("courses", [])],
        chapters=[ChapterRecord(**item) for item in payload.get("chapters", [])],
        videos=[VideoRecord(**item) for item in payload.get("videos", [])],
    )


def save_cache(path: str, state: CacheState) -> None:
    Path(path).write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def clear_cache(path: str) -> None:
    cache_path = Path(path)
    if cache_path.exists():
        cache_path.unlink()


def upsert_courses(state: CacheState, records: list[CourseRecord]) -> CacheState:
    merged = {item.course_key: item for item in state.courses}
    for item in records:
        previous = merged.get(item.course_key)
        if previous is not None and previous.course_study_url and not item.course_study_url:
            item = CourseRecord(
                course_key=item.course_key,
                course_id=item.course_id,
                clazz_id=item.clazz_id,
                cpi=item.cpi,
                enc=item.enc,
                title=item.title,
                teacher=item.teacher,
                open_time=item.open_time,
                course_url=item.course_url,
                course_study_url=previous.course_study_url,
            )
        merged[item.course_key] = item
    return CacheState(courses=list(merged.values()), chapters=state.chapters, videos=state.videos)


def upsert_chapters(state: CacheState, records: list[ChapterRecord]) -> CacheState:
    merged = {item.chapter_key: item for item in state.chapters}
    for item in records:
        merged[item.chapter_key] = item
    return CacheState(courses=state.courses, chapters=list(merged.values()), videos=state.videos)


def upsert_videos(state: CacheState, records: list[VideoRecord]) -> CacheState:
    merged = {item.video_key: item for item in state.videos}
    for item in records:
        merged[item.video_key] = item
    return CacheState(courses=state.courses, chapters=state.chapters, videos=list(merged.values()))


def make_course_key(course_id: str, clazz_id: str) -> str:
    return f"course-{_digest(f'{course_id}:{clazz_id}')}"


def make_chapter_key(course_key: str, chapter_id: str) -> str:
    return f"chapter-{_digest(f'{course_key}:{chapter_id}')}"


def make_video_key(chapter_key: str, object_id: str) -> str:
    return f"video-{_digest(f'{chapter_key}:{object_id}')}"


def _digest(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]


def _normalize_course_payload(item: dict[str, object]) -> dict[str, object]:
    payload = dict(item)
    payload.setdefault("course_study_url", "")
    return payload
