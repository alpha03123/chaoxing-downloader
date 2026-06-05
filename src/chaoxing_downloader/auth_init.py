from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Mapping

from .cache_store import make_course_key, save_cache
from .course_catalog_parser import parse_course_list
from .models import CacheState, CourseRecord


DEFAULT_BASE_URL = "https://i.chaoxing.com/base"
DEFAULT_LOGIN_URL = "https://i.chaoxing.com/"
DEFAULT_REFERER = "https://mooc1.chaoxing.com/"
DEFAULT_USER_DATA_DIR = ".chaoxing-browser"


class InitError(ValueError):
    pass


ProgressCallback = Callable[[str, str], None]


def run_browser_init(
    *,
    config_path: str,
    user_data_dir: str = DEFAULT_USER_DATA_DIR,
    login_url: str = DEFAULT_LOGIN_URL,
    timeout_seconds: int = 300,
    progress: ProgressCallback | None = None,
) -> None:
    _emit(progress, "start", "启动浏览器，等待超星授权")
    cookie, warmed_courses = collect_cookie_header_with_browser(
        user_data_dir=user_data_dir,
        login_url=login_url,
        timeout_seconds=timeout_seconds,
        progress=progress,
    )
    save_init_config(config_path, cookie=cookie, warmed_courses=warmed_courses)
    _emit(progress, "config", f"配置已写入 {config_path}")


def collect_cookie_header_with_browser(
    *,
    user_data_dir: str,
    login_url: str,
    timeout_seconds: int,
    progress: ProgressCallback | None = None,
) -> tuple[str, list[CourseRecord]]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise InitError("错误：缺少 Playwright，请先安装依赖并运行 python -m playwright install chromium") from exc

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(login_url, wait_until="domcontentloaded")
            deadline = time.monotonic() + timeout_seconds
            while time.monotonic() < deadline:
                _emit(progress, "waiting", "等待网站授权，请在浏览器中完成登录")
                cookies = context.cookies()
                cookie_header = format_cookie_header(cookies)
                if _has_login_cookie(cookie_header):
                    _emit(progress, "checking", "检测到登录 Cookie，验证课程主页")
                    page.goto(_base_url_with_dynamic_params(), wait_until="domcontentloaded")
                    if is_logged_in_home_page(page.url, page.content()):
                        warmed_courses = warm_course_cookies(page, progress=progress)
                        _emit(progress, "cookies", "导出最终 Cookie")
                        return format_cookie_header(context.cookies()), warmed_courses
                page.wait_for_timeout(1000)
            raise InitError("错误：等待登录超时，请重新运行 init")
        except PlaywrightTimeoutError as exc:
            raise InitError("错误：浏览器页面加载超时，请检查网络后重试") from exc
        finally:
            context.close()


def format_cookie_header(cookies: list[Mapping[str, object]]) -> str:
    pairs: list[str] = []
    seen: set[tuple[str, str]] = set()
    for cookie in cookies:
        domain = str(cookie.get("domain", "")).lower()
        if "chaoxing.com" not in domain:
            continue
        name = str(cookie.get("name", "")).strip()
        value = str(cookie.get("value", "")).strip()
        if not name:
            continue
        key = (domain, name)
        if key in seen:
            continue
        seen.add(key)
        pairs.append(f"{name}={value}")
    if not pairs:
        raise InitError("错误：未采集到超星 Cookie，请确认已登录")
    return "; ".join(pairs)


def save_init_config(
    path: str,
    *,
    cookie: str,
    warmed_courses: list[CourseRecord] | list[Mapping[str, object]] | None = None,
    cache_path: str = ".chaoxing-cache.json",
) -> None:
    config_path = Path(path)
    config_path.write_text(
        "\n".join(
            [
                "[session]",
                f'cookie = "{_toml_escape(cookie)}"',
                f'referer = "{DEFAULT_REFERER}"',
                "",
                "[entry]",
                f'base_url = "{DEFAULT_BASE_URL}"',
                "",
                "[download]",
                'output_dir = "downloads"',
                "",
                "[cache]",
                'path = ".chaoxing-cache.json"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    if warmed_courses:
        save_cache(cache_path, CacheState(courses=[_to_course_record(item) for item in warmed_courses]))


def is_logged_in_home_page(url: str, html: str) -> bool:
    if "passport2.chaoxing.com/login" in url:
        return False
    if "用户登录" in html:
        return False
    return "visit/interaction" in html


def warm_course_cookies(page, *, progress: ProgressCallback | None = None) -> list[CourseRecord]:
    interaction_url = _extract_interaction_url(page.content())
    _emit(progress, "courses", "进入课程列表")
    page.goto(interaction_url, wait_until="domcontentloaded")
    response = page.request.post(
        "https://mooc1-1.chaoxing.com/mooc-ans/visit/courselistdata",
        form={
            "courseType": "1",
            "courseFolderId": "0",
            "baseEducation": "0",
            "superstarClass": "",
            "courseFolderSize": "0",
        },
    )
    records = parse_course_list(response.text())
    if not records:
        raise InitError("错误：登录成功，但未解析到课程列表，无法预热课程 Cookie")
    _emit(progress, "courses", f"解析到 {len(records)} 门课程，开始采集课程 Cookie")
    warmed_records: list[CourseRecord] = []
    for index, record in enumerate(records, start=1):
        _emit(progress, "course", f"[{index}/{len(records)}] 进入课程：{record.title}")
        page.goto(record.course_url, wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        course_study_url = page.url if _is_course_study_url(page.url) else ""
        warmed_records.append(_with_course_study_url(record, course_study_url))
        if _has_course_cookie(page.context.cookies(), record.course_id):
            _emit(progress, "course_cookie", f"已采集课程 Cookie：{record.title}")
        elif course_study_url:
            _emit(progress, "course_cookie", f"已采集课程入口参数：{record.title}")
        else:
            _emit(progress, "course_cookie_missing", f"未发现课程入口参数：{record.title}")
    return warmed_records


def _extract_interaction_url(html: str) -> str:
    marker = 'dataurl="https://mooc1-1.chaoxing.com/visit/interaction'
    start = html.find(marker)
    if start == -1:
        raise InitError("错误：登录成功，但课程入口结构无法识别")
    start += len('dataurl="')
    end = html.find('"', start)
    return html[start:end]


def _has_login_cookie(cookie_header: str) -> bool:
    names = {part.split("=", 1)[0].strip() for part in cookie_header.split(";") if "=" in part}
    return "UID" in names and ("vc3" in names or "p_auth_token" in names)


def _has_course_cookie(cookies: list[Mapping[str, object]], course_id: str) -> bool:
    names = {str(cookie.get("name", "")).strip() for cookie in cookies}
    return f"{course_id}enc" in names and f"{course_id}t" in names


def _is_course_study_url(url: str) -> bool:
    return "mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu" in url and "enc=" in url and "t=" in url


def _with_course_study_url(record: CourseRecord, course_study_url: str) -> CourseRecord:
    return CourseRecord(
        course_key=record.course_key,
        course_id=record.course_id,
        clazz_id=record.clazz_id,
        cpi=record.cpi,
        enc=record.enc,
        title=record.title,
        teacher=record.teacher,
        open_time=record.open_time,
        course_url=record.course_url,
        course_study_url=course_study_url,
    )


def _to_course_record(item: CourseRecord | Mapping[str, object]) -> CourseRecord:
    if isinstance(item, CourseRecord):
        return item
    return CourseRecord(
        course_key=str(item.get("course_key") or make_course_key(str(item.get("course_id", "")), str(item.get("clazz_id", "")))),
        course_id=str(item.get("course_id", "")),
        clazz_id=str(item.get("clazz_id", "")),
        cpi=str(item.get("cpi", "")),
        enc=str(item.get("enc", "")),
        title=str(item.get("title", "")),
        teacher=str(item.get("teacher", "")),
        open_time=str(item.get("open_time", "")),
        course_url=str(item.get("course_url", "")),
        course_study_url=str(item.get("course_study_url", "")),
    )


def _emit(progress: ProgressCallback | None, kind: str, message: str) -> None:
    if progress is not None:
        progress(kind, message)


def _base_url_with_dynamic_params() -> str:
    return f"{DEFAULT_BASE_URL}?ws=1&t={int(time.time() * 1000)}"


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
