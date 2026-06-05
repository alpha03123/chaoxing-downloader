from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from .cache_store import make_chapter_key, make_course_key, make_video_key
from .models import ChapterRecord, CourseRecord, VideoRecord


def parse_course_list(html: str) -> list[CourseRecord]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[CourseRecord] = []
    for item in soup.select("#courseList > li.course"):
        course_id = _attr_text(item, "courseid")
        clazz_id = _attr_text(item, "clazzid")
        cpi = _attr_text(item, "personid")
        link = item.select_one(".course-info a[href]")
        if not course_id or not clazz_id or not cpi or link is None:
            continue
        course_url = _attr_text(link, "href")
        title = _text_of(item.select_one(".course-name"))
        info_lines = item.select(".course-info p")
        teacher = _text_of(info_lines[1]) if len(info_lines) > 1 else ""
        open_time = _text_of(info_lines[2]) if len(info_lines) > 2 else ""
        query = parse_qs(urlparse(course_url).query)
        enc = _first_query(query, "enc")
        records.append(
            CourseRecord(
                course_key=make_course_key(course_id, clazz_id),
                course_id=course_id,
                clazz_id=clazz_id,
                cpi=cpi,
                enc=enc,
                title=title,
                teacher=teacher,
                open_time=open_time,
                course_url=course_url,
            )
        )
    return records


def parse_student_course(html: str, *, course_key: str) -> list[ChapterRecord]:
    soup = BeautifulSoup(html, "html.parser")
    course_id = _value_of(soup, "courseId")
    clazz_id = _value_of(soup, "clazzId")
    cpi = _value_of(soup, "cpi")
    enc = _value_of(soup, "enc")
    openc = _value_of(soup, "openc")
    t_value = _value_of(soup, "t")
    mooc_domain = _value_of(soup, "moocDomainName") or "https://mooc1.chaoxing.com"
    records: list[ChapterRecord] = []
    for item in soup.select(".chapter_item[id^='cur']"):
        chapter_id = _extract_chapter_id(item)
        if not chapter_id:
            continue
        order = _text_of(item.select_one(".catalog_sbar"))
        title = _strip_order_prefix(_text_of(item.select_one(".catalog_name")), order)
        studentstudy_url = (
            f"{mooc_domain}/mycourse/studentstudy?chapterId={chapter_id}&courseId={course_id}"
            f"&clazzid={clazz_id}&cpi={cpi}&enc={enc}&mooc2=1&hidetype=0&openc={openc}&t={t_value}"
        )
        records.append(
            ChapterRecord(
                chapter_key=make_chapter_key(course_key, chapter_id),
                chapter_id=chapter_id,
                course_key=course_key,
                title=title,
                order=order,
                studentstudy_url=studentstudy_url,
            )
        )
    return records


def build_video_records(chapter_key: str, tasks: list[dict[str, object]], media_status: dict[str, object] | None = None) -> list[VideoRecord]:
    records: list[VideoRecord] = []
    for task in tasks:
        object_id = _as_text(task.get("object_id"))
        if not object_id:
            continue
        status_payload = media_status if media_status and media_status.get("objectid") == object_id else None
        records.append(
            VideoRecord(
                video_key=make_video_key(chapter_key, object_id),
                chapter_key=chapter_key,
                title=_as_text(task.get("title")) or "未命名视频",
                object_id=object_id,
                job_id=_as_text(task.get("job_id")),
                mid=_as_text(task.get("mid")),
                duration=_as_int(status_payload.get("duration") if status_payload else 0),
                size=_as_int(status_payload.get("length") if status_payload else 0),
                media_url=_as_text(status_payload.get("http") if status_payload else ""),
                download_url=_as_text(status_payload.get("download") if status_payload else ""),
                filename=_as_text(status_payload.get("filename") if status_payload else ""),
            )
        )
    return records


def _extract_chapter_id(node) -> str:
    identifier = _attr_text(node, "id")
    match = re.search(r"cur(\d+)", identifier)
    return match.group(1) if match else ""


def _value_of(soup: BeautifulSoup, element_id: str) -> str:
    node = soup.select_one(f"#{element_id}")
    if node is None:
        return ""
    value = node.get("value")
    return value.strip() if isinstance(value, str) else ""


def _attr_text(node, name: str) -> str:
    value = node.get(name)
    return value.strip() if isinstance(value, str) else ""


def _text_of(node) -> str:
    if node is None:
        return ""
    return node.get_text(" ", strip=True)


def _first_query(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key, [])
    return values[0].strip() if values and values[0].strip() else ""


def _strip_order_prefix(title: str, order: str) -> str:
    if order and title.startswith(order):
        return title[len(order) :].strip()
    return title


def _as_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    return 0
