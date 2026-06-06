from __future__ import annotations

from http.cookies import SimpleCookie
from pathlib import Path
import re
import time
from typing import Callable
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
import httpx

from .cache_store import (
    CacheError,
    CacheState,
    clear_cache,
    load_cache,
    save_cache,
    upsert_chapters,
    upsert_courses,
    upsert_videos,
)
from .config import AppConfig
from .course_catalog_parser import build_video_records, parse_course_list, parse_student_course
from .course_parser import UnsupportedChapterError, parse_course_page
from .http_client import ChaoxingClient
from .media_resolver import resolve_media_status
from .models import ChapterRecord, CourseRecord, VideoRecord


class WorkflowError(ValueError):
    pass


DownloadProgress = Callable[[int, int | None], None]


def list_courses(client: ChaoxingClient, config: AppConfig, *, url_override: str = "") -> list[CourseRecord]:
    base_url = url_override.strip() or config.base_url.strip()
    if not base_url:
        raise WorkflowError("错误：缺少入口 URL，请在 config.toml 中配置 entry.base_url 或使用 --url 传入")
    home_html = client.get_text(_entry_url_with_dynamic_params(base_url))
    interaction_url = _extract_interaction_url(home_html)
    interaction_html = client.get_text(interaction_url)
    course_list_html = client.post_text(
        "https://mooc1-1.chaoxing.com/mooc-ans/visit/courselistdata",
        data={
            "courseType": "1",
            "courseFolderId": "0",
            "baseEducation": "0",
            "superstarClass": "",
            "courseFolderSize": "0",
        },
    )
    records = parse_course_list(course_list_html)
    state = _safe_load_cache(config.cache_path)
    save_cache(config.cache_path, upsert_courses(state, records))
    return records


def list_chapters(client: ChaoxingClient, config: AppConfig, *, course_key: str) -> list[ChapterRecord]:
    state = load_cache(config.cache_path)
    course = next((item for item in state.courses if item.course_key == course_key), None)
    if course is None:
        raise WorkflowError(f"错误：找不到课程 {course_key}，请先运行 list-courses")
    course_html, course_page_url = client.get_text_with_url(course.course_url)
    if _is_login_page(course_html):
        fallback_url = course.course_study_url or _build_course_stu_url_from_cookie(config.cookie, course)
        course_html, course_page_url = client.get_text_with_url(fallback_url)
    studentcourse_url = _resolve_studentcourse_url(course_html, course_page_url)
    html = client.get_text(studentcourse_url)
    records = parse_student_course(html, course_key=course_key)
    save_cache(config.cache_path, upsert_chapters(state, records))
    return records


def list_videos(client: ChaoxingClient, config: AppConfig, *, chapter_key: str) -> list[VideoRecord]:
    state = load_cache(config.cache_path)
    chapter = next((item for item in state.chapters if item.chapter_key == chapter_key), None)
    if chapter is None:
        raise WorkflowError(f"错误：找不到章节 {chapter_key}，请先运行 list-chapters")
    html, page_url = client.get_text_with_url(chapter.studentstudy_url)
    try:
        course = parse_course_page(html)
    except UnsupportedChapterError:
        cards_url = _build_knowledge_cards_url(html, page_url)
        try:
            course = parse_course_page(client.get_text(cards_url))
        except UnsupportedChapterError as exc:
            raise UnsupportedChapterError(f"当前章节没有可解析的视频任务点：{chapter.title}（{chapter.order}）。{exc}") from exc
    first_video_status = None
    task_payloads: list[dict[str, object]] = []
    for chapter_item in course.chapters:
        for task in chapter_item.tasks:
            payload = {
                "title": task.title,
                "object_id": task.object_id,
                "job_id": task.job_id,
                "mid": task.mid,
            }
            task_payloads.append(payload)
            if first_video_status is None and task.object_id:
                try:
                    first_video_status = resolve_media_status(client, task.object_id)
                except ValueError:
                    first_video_status = None
    records = build_video_records(chapter_key, task_payloads, first_video_status)
    save_cache(config.cache_path, upsert_videos(state, records))
    return records


def download_video(
    client: ChaoxingClient,
    config: AppConfig,
    *,
    video_key: str,
    output_dir: str | Path | None = None,
    filename: str | None = None,
    progress: DownloadProgress | None = None,
) -> Path:
    state = load_cache(config.cache_path)
    video = next((item for item in state.videos if item.video_key == video_key), None)
    if video is None:
        raise WorkflowError(f"错误：找不到视频 {video_key}，请先运行 list-videos")
    media_url = video.media_url
    target_filename = filename.strip() if filename is not None else ""
    if not target_filename:
        target_filename = video.filename or f"{video.object_id}.mp4"
    if not media_url:
        status_payload = resolve_media_status(client, video.object_id)
        media_url = _pick_media_url(status_payload)
        if not media_url:
            raise WorkflowError(f"错误：视频状态接口返回异常（status={status_payload.get('status')}），object_id={video.object_id}")
        if filename is None:
            target_filename = str(status_payload.get("filename") or target_filename)
    target_dir = Path(output_dir) if output_dir is not None else Path(config.output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / target_filename
    downloaded = 0
    with target.open("wb") as file:
        for chunk, total in client.iter_bytes(media_url):
            file.write(chunk)
            downloaded += len(chunk)
            if progress is not None:
                progress(downloaded, total)
    return target


def remove_cache(config: AppConfig) -> None:
    clear_cache(config.cache_path)


def map_http_error(exc: Exception) -> WorkflowError:
    if isinstance(exc, httpx.TimeoutException):
        return WorkflowError("错误：请求超时，请检查网络连接")
    if isinstance(exc, httpx.ConnectError):
        return WorkflowError("错误：无法连接到学习通服务器，请检查网络连接")
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code in {401, 403}:
            return WorkflowError(f"错误：请求失败（HTTP {status_code}），Cookie 可能已过期，请更新 config.toml 中的 session.cookie")
        if 500 <= status_code < 600:
            return WorkflowError(f"错误：学习通服务器异常（HTTP {status_code}），请稍后重试")
        return WorkflowError(f"错误：请求失败（HTTP {status_code}）")
    return WorkflowError(str(exc))


def _safe_load_cache(path: str) -> CacheState:
    try:
        return load_cache(path)
    except CacheError:
        return CacheState()


def _entry_url_with_dynamic_params(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc != "i.chaoxing.com" or parsed.path != "/base":
        return url
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params.setdefault("ws", "1")
    params["t"] = str(int(time.time() * 1000))
    return urlunparse(parsed._replace(query=urlencode(params)))


def _extract_interaction_url(html: str) -> str:
    marker = 'dataurl="https://mooc1-1.chaoxing.com/visit/interaction'
    start = html.find(marker)
    if start == -1:
        raise WorkflowError("错误：课程页面结构无法识别，学习通可能已更新页面，请反馈")
    start += len('dataurl="')
    end = html.find('"', start)
    return html[start:end]


def _resolve_studentcourse_url(html: str, current_url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    chapter_link = soup.select_one('a[data-url*="/mycourse/studentcourse"]')
    if chapter_link is None:
        if soup.select_one(".chapter_item[id^='cur']") is not None:
            return current_url
        raise WorkflowError("错误：课程章节入口无法识别，学习通可能已更新页面，请反馈")
    data_url = chapter_link.get("data-url")
    if not isinstance(data_url, str) or not data_url.strip():
        raise WorkflowError("错误：课程章节入口缺少 data-url，学习通可能已更新页面，请反馈")

    params = _studentcourse_params(soup)
    return f"{urljoin(current_url, data_url.strip())}?{urlencode(params)}"


def _is_login_page(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one("title")
    return title is not None and "用户登录" in title.get_text("", strip=True)


def _build_course_stu_url_from_cookie(cookie: str, course: CourseRecord) -> str:
    jar = SimpleCookie()
    jar.load(cookie)
    prefix = course.course_id
    values = {
        "courseid": course.course_id,
        "clazzid": course.clazz_id,
        "cpi": _cookie_value(jar, f"{prefix}cpi") or course.cpi,
        "enc": _cookie_value(jar, f"{prefix}enc"),
        "t": _cookie_value(jar, f"{prefix}t"),
        "pageHeader": "1",
        "v": "2",
        "hideHead": "0",
    }
    missing = [key for key in ("cpi", "enc", "t") if not values[key]]
    if missing:
        raise WorkflowError(f"错误：课程入口缺少参数：{', '.join(prefix + key for key in missing)}")
    return f"https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu?{urlencode(values)}"


def _cookie_value(jar: SimpleCookie, name: str) -> str:
    morsel = jar.get(name)
    return morsel.value.strip() if morsel is not None and morsel.value.strip() else ""


def _studentcourse_params(soup: BeautifulSoup) -> dict[str, str]:
    required = {
        "courseid": _value_of_any(soup, "courseid", "courseId"),
        "clazzid": _value_of_any(soup, "clazzid", "clazzId"),
        "cpi": _value_of_any(soup, "cpi"),
        "enc": _value_of_any(soup, "enc"),
        "openc": _value_of_any(soup, "openc"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise WorkflowError(f"错误：课程页面缺少章节参数：{', '.join(missing)}")

    optional = {
        "t": _value_of_any(soup, "t"),
        "v": _value_of_any(soup, "v") or "2",
    }
    return {key: value for key, value in {**required, **optional}.items() if value}


def _build_knowledge_cards_url(html: str, page_url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    values = {
        "clazzid": _value_of_any(soup, "curClazzId", "clazzId", "clazzid"),
        "courseid": _value_of_any(soup, "curCourseId", "courseId", "courseid"),
        "knowledgeid": _value_of_any(soup, "curChapterId", "chapterIdid", "chapterId"),
        "num": "0",
        "ut": _extract_script_value(html, r"var\s+ut_value\s*=\s*['\"]([^'\"]+)['\"]") or _value_of_any(soup, "ut") or "s",
        "cpi": _value_of_any(soup, "curCpi", "cpi"),
        "mooc2": "1",
        "isMicroCourse": _value_of_any(soup, "isMicroCourse") or "false",
        "editorPreview": "0",
        "crossId": _extract_script_value(html, r"var\s+crossId\s*=\s*['\"]([^'\"]*)['\"]") or "0",
    }
    version = _extract_script_value(html, r"&v=([^&\"']+)&mooc2")
    if version:
        values["v"] = version
    missing = [key for key in ("clazzid", "courseid", "knowledgeid", "cpi") if not values[key]]
    if missing:
        raise WorkflowError(f"错误：章节外壳缺少 cards 参数：{', '.join(missing)}")
    return f"{urljoin(page_url, '/mooc-ans/knowledge/cards')}?{urlencode(values)}"


def _extract_script_value(html: str, pattern: str) -> str:
    match = re.search(pattern, html)
    return match.group(1).strip() if match else ""


def _value_of_any(soup: BeautifulSoup, *element_ids: str) -> str:
    for element_id in element_ids:
        node = soup.select_one(f"#{element_id}")
        if node is None:
            continue
        value = node.get("value")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _pick_media_url(status_payload: dict[str, object]) -> str:
    for key in ("http", "download"):
        value = status_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""
