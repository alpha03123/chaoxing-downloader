from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from .models import Chapter, CoursePage, TaskPoint


class UnsupportedChapterError(ValueError):
    pass


def parse_course_page(html: str) -> CoursePage:
    soup = BeautifulSoup(html, "html.parser")
    embedded_payload = _extract_marg_payload(html)
    title = _extract_title(soup, embedded_payload)
    if embedded_payload:
        chapters = _extract_chapters_from_payload(embedded_payload)
        if chapters:
            return CoursePage(title=title, chapters=chapters)
    chapters = _extract_chapters(soup)
    if not chapters:
        raise UnsupportedChapterError(_unsupported_chapter_message(html, soup))
    return CoursePage(title=title, chapters=chapters)


def _extract_title(soup: BeautifulSoup, payload: dict[str, object] | None = None) -> str:
    if payload:
        course_name = payload.get("coursename")
        if isinstance(course_name, str) and course_name.strip():
            return course_name.strip()
    heading = soup.find(["h1", "h2"])
    return heading.get_text(strip=True) if heading else "未命名课程"


def _extract_marg_payload(html: str) -> dict[str, object] | None:
    match = re.search(r"mArg\s*=\s*(\{.*?\});", html, re.S)
    if not match:
        return None
    return json.loads(match.group(1))


def _extract_chapters_from_payload(payload: dict[str, object]) -> list[Chapter]:
    attachments = payload.get("attachments")
    if not isinstance(attachments, list) or not attachments:
        return []

    tasks: list[TaskPoint] = []
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        task_type = attachment.get("type")
        if task_type != "video":
            continue
        prop = attachment.get("property")
        prop_dict = prop if isinstance(prop, dict) else {}
        title = ""
        for key in ("name",):
            value = prop_dict.get(key)
            if isinstance(value, str) and value.strip():
                title = value.strip()
                break
        if not title:
            topic_list = attachment.get("topicList")
            if isinstance(topic_list, list) and topic_list:
                first = topic_list[0]
                if isinstance(first, dict):
                    topic_name = first.get("name")
                    if isinstance(topic_name, str) and topic_name.strip():
                        title = topic_name.strip()
        if not title:
            title = "未命名视频"
        object_id = _as_text(attachment.get("objectId")) or _as_text(prop_dict.get("objectid"))
        job_id = _as_text(attachment.get("jobid")) or _as_text(prop_dict.get("jobid")) or _as_text(prop_dict.get("_jobid"))
        mid = _as_text(attachment.get("mid")) or _as_text(prop_dict.get("mid"))
        tasks.append(
            TaskPoint(
                title=title,
                kind="video",
                status="unresolved",
                object_id=object_id,
                job_id=job_id,
                mid=mid,
            )
        )

    if not tasks:
        return []
    knowledge_name = payload.get("knowledgename")
    chapter_title = knowledge_name.strip() if isinstance(knowledge_name, str) and knowledge_name.strip() else "未命名章节"
    return [Chapter(title=chapter_title, tasks=tasks)]


def _extract_chapters(soup: BeautifulSoup) -> list[Chapter]:
    chapters: list[Chapter] = []
    for chapter_node in soup.select("[data-chapter], .chapter"):
        chapter_title = chapter_node.get_text(" ", strip=True)
        tasks: list[TaskPoint] = []
        for task_node in chapter_node.select("[data-task], .task, li"):
            text = task_node.get_text(" ", strip=True)
            if not text:
                continue
            kind = "video" if "视频" in text or "video" in text.lower() else "unknown"
            tasks.append(TaskPoint(title=text, kind=kind, status="unresolved"))
        if tasks:
            chapters.append(Chapter(title=chapter_title or "未命名章节", tasks=tasks))
    return chapters


def _as_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _unsupported_chapter_message(html: str, soup: BeautifulSoup) -> str:
    title = soup.select_one("title")
    title_text = title.get_text("", strip=True) if title else ""
    if "用户登录" in html or "passport2.chaoxing.com/login" in html:
        return "当前章节返回登录页，请重新初始化登录状态"
    if title_text:
        return f"当前章节暂不支持解析视频任务点（页面标题：{title_text}）"
    return "当前章节暂不支持解析视频任务点"
