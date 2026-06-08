from __future__ import annotations

from http.cookies import SimpleCookie
import time
from pathlib import Path
from typing import Callable, Mapping

import httpx

from .cache_store import make_course_key, save_cache
from .course_catalog_parser import parse_course_list
from .models import CacheState, CourseRecord


DEFAULT_BASE_URL = "https://i.chaoxing.com/base"
DEFAULT_LOGIN_URL = "https://i.chaoxing.com/"
DEFAULT_REFERER = "https://mooc1.chaoxing.com/"
DEFAULT_USER_DATA_DIR = ".chaoxing-browser"


class InitError(ValueError):
    pass


class InitCancelled(InitError):
    pass


ProgressCallback = Callable[[str, str], None]
CancelCheck = Callable[[], bool]
BrowserPageFactory = Callable[[str], object]
HttpClientFactory = Callable[[str], httpx.Client]
CourseWarmImpl = Callable[..., tuple[str, list[CourseRecord]]]
Sleep = Callable[[float], None]


def run_browser_init(
    *,
    config_path: str,
    user_data_dir: str = DEFAULT_USER_DATA_DIR,
    login_url: str = DEFAULT_LOGIN_URL,
    timeout_seconds: int = 300,
    progress: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
    course_delay: float = 0.0,
) -> None:
    _validate_delay(course_delay, name="course_delay")
    _raise_if_cancelled(cancel_check)
    _emit(progress, "start", "启动浏览器，等待超星授权")
    cookie, warmed_courses = collect_cookie_header_with_browser(
        user_data_dir=user_data_dir,
        login_url=login_url,
        timeout_seconds=timeout_seconds,
        progress=progress,
        cancel_check=cancel_check,
        course_delay=course_delay,
    )
    save_init_config(config_path, cookie=cookie, warmed_courses=warmed_courses)
    _emit(progress, "config", f"配置已写入 {config_path}")


def collect_cookie_header_with_browser(
    *,
    user_data_dir: str,
    login_url: str,
    timeout_seconds: int,
    progress: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
    course_delay: float = 0.0,
    page_factory: BrowserPageFactory | None = None,
    warm_impl: CourseWarmImpl | None = None,
    sleep: Sleep = time.sleep,
) -> tuple[str, list[CourseRecord]]:
    _validate_delay(course_delay, name="course_delay")
    _raise_if_cancelled(cancel_check)
    factory = page_factory or _create_drission_page
    warmer = warm_impl or warm_course_cookies
    page = factory(user_data_dir)
    try:
        _page_get(page, login_url)
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            _raise_if_cancelled(cancel_check)
            _emit(progress, "waiting", "等待网站授权，请在浏览器中完成登录")
            cookie_header = format_cookie_header(_page_cookies(page))
            if _has_login_cookie(cookie_header):
                _emit(progress, "checking", "检测到登录 Cookie，验证课程主页")
                cookie_header, warmed_courses = warmer(
                    cookie_header,
                    progress=progress,
                    cancel_check=cancel_check,
                    course_delay=course_delay,
                )
                _emit(progress, "cookies", "导出最终 Cookie")
                return cookie_header, warmed_courses
            sleep(1.0)
        raise InitError("错误：等待登录超时，请重新运行 init")
    finally:
        _close_page(page)


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


def warm_course_cookies(
    cookie_header: str,
    *,
    progress: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
    course_delay: float = 0.0,
    client_factory: HttpClientFactory | None = None,
    sleep: Sleep = time.sleep,
) -> tuple[str, list[CourseRecord]]:
    _validate_delay(course_delay, name="course_delay")
    _raise_if_cancelled(cancel_check)
    factory = client_factory or _create_chaoxing_client
    with factory(cookie_header) as client:
        home = client.get(_base_url_with_dynamic_params())
        if not is_logged_in_home_page(str(home.url), home.text):
            raise InitError("错误：Cookie 无效，请确认已登录")
        interaction_url = _extract_interaction_url(home.text)
        _emit(progress, "courses", "进入课程列表")
        client.get(interaction_url)
        _raise_if_cancelled(cancel_check)
        response = client.post(
            "https://mooc1-1.chaoxing.com/mooc-ans/visit/courselistdata",
            data={
                "courseType": "1",
                "courseFolderId": "0",
                "baseEducation": "0",
                "superstarClass": "",
                "courseFolderSize": "0",
            },
        )
        records = parse_course_list(response.text)
        if not records:
            raise InitError("错误：登录成功，但未解析到课程列表，无法预热课程入口参数")
        _emit(progress, "courses", f"解析到 {len(records)} 门课程，开始采集课程入口参数")
        warmed_records: list[CourseRecord] = []
        for index, record in enumerate(records, start=1):
            _raise_if_cancelled(cancel_check)
            _emit(progress, "course", f"[{index}/{len(records)}] 进入课程：{record.title}")
            _wait_for_course_delay(course_delay, sleep)
            entry = client.get(record.course_url)
            course_study_url = str(entry.url) if _is_course_study_url(str(entry.url)) else ""
            warmed_records.append(_with_course_study_url(record, course_study_url))
            if _has_course_cookie_from_jar(client.cookies.jar, record.course_id):
                _emit(progress, "course_cookie", f"已采集课程入口参数：{record.title}")
            elif course_study_url:
                _emit(progress, "course_cookie", f"已采集课程入口参数：{record.title}")
            else:
                _emit(progress, "course_cookie_missing", f"未发现课程入口参数：{record.title}")
        return _merge_cookie_header(cookie_header, client.cookies.jar), warmed_records


def _create_chaoxing_client(cookie_header: str) -> httpx.Client:
    return httpx.Client(
        cookies=_cookie_header_to_dict(cookie_header),
        headers={"Referer": DEFAULT_REFERER},
        follow_redirects=True,
        timeout=30.0,
    )


def _create_drission_page(user_data_dir: str) -> object:
    try:
        from DrissionPage import Chromium, ChromiumOptions
    except ImportError as exc:
        raise InitError("错误：缺少 DrissionPage，请先安装依赖") from exc
    options = ChromiumOptions(read_file=False).auto_port().set_user_data_path(user_data_dir)
    browser = Chromium(addr_or_opts=options)
    return _DrissionPageSession(browser, browser.latest_tab)


class _DrissionPageSession:
    def __init__(self, browser: object, page: object) -> None:
        self._browser = browser
        self._page = page

    def get(self, url: str) -> None:
        self._page.get(url)

    def cookies(self, *, as_dict: bool = False, all_domains: bool = True) -> list[Mapping[str, object]]:
        return self._page.cookies(as_dict=as_dict, all_domains=all_domains)

    def quit(self) -> None:
        self._browser.quit()


def _page_get(page: object, url: str) -> None:
    get = getattr(page, "get", None)
    if get is None:
        raise InitError("错误：浏览器页面对象不支持打开网址")
    get(url)


def _page_cookies(page: object) -> list[Mapping[str, object]]:
    cookies = getattr(page, "cookies", None)
    if cookies is not None:
        try:
            return cookies(as_dict=False, all_domains=True)
        except TypeError:
            return cookies(as_dict=False)
    get_cookies = getattr(page, "get_cookies", None)
    if get_cookies is not None:
        return get_cookies(as_dict=False)
    raise InitError("错误：浏览器页面对象不支持导出 Cookie")


def _close_page(page: object) -> None:
    for name in ("quit", "close"):
        method = getattr(page, name, None)
        if method is not None:
            method()
            return


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


def _has_course_cookie_from_jar(jar, course_id: str) -> bool:
    names = {cookie.name for cookie in jar}
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


def _raise_if_cancelled(cancel_check: CancelCheck | None) -> None:
    if cancel_check is not None and cancel_check():
        raise InitCancelled("初始化已取消")


def _validate_delay(value: float, *, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be greater than or equal to 0")


def _wait_for_course_delay(course_delay: float, sleep: Sleep) -> None:
    if course_delay > 0:
        sleep(course_delay)


def _base_url_with_dynamic_params() -> str:
    return f"{DEFAULT_BASE_URL}?ws=1&t={int(time.time() * 1000)}"


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _cookie_header_to_dict(cookie_header: str) -> dict[str, str]:
    jar = SimpleCookie()
    jar.load(cookie_header)
    return {key: morsel.value for key, morsel in jar.items()}


def _merge_cookie_header(cookie_header: str, jar) -> str:
    values = _cookie_header_to_dict(cookie_header)
    for cookie in jar:
        domain = str(cookie.domain or "").lower()
        if domain and "chaoxing.com" not in domain:
            continue
        values[cookie.name] = cookie.value
    return "; ".join(f"{name}={value}" for name, value in values.items())
