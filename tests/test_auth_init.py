from pathlib import Path

import httpx

from chaoxing_downloader.auth_init import (
    InitCancelled,
    collect_cookie_header_with_browser,
    format_cookie_header,
    is_logged_in_home_page,
    save_init_config,
    warm_course_cookies,
)
from chaoxing_downloader.cache_store import load_cache
from chaoxing_downloader.config import load_config


def test_format_cookie_header_keeps_chaoxing_cookies() -> None:
    cookies = [
        {"name": "UID", "value": "1", "domain": ".chaoxing.com"},
        {"name": "jrose", "value": "abc", "domain": "mooc1.chaoxing.com"},
        {"name": "other", "value": "x", "domain": "example.com"},
    ]

    assert format_cookie_header(cookies) == "UID=1; jrose=abc"


def test_save_init_config_writes_loadable_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"

    save_init_config(str(config_path), cookie="UID=1; vc3=abc")
    config = load_config(str(config_path))

    assert config.cookie == "UID=1; vc3=abc"
    assert config.referer == "https://mooc1.chaoxing.com/"
    assert config.base_url == "https://i.chaoxing.com/base"
    assert config.output_dir == "downloads"
    assert config.cache_path == ".chaoxing-cache.json"


def test_save_init_config_writes_warmed_courses(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    cache_path = tmp_path / ".chaoxing-cache.json"
    warmed_courses = [
        {
            "course_id": "261641822",
            "clazz_id": "142332957",
            "cpi": "407073562",
            "title": "大学生职业发展与就业指导",
            "course_url": "https://mooc1-1.chaoxing.com/mooc-ans/visit/stucoursemiddle?courseid=261641822",
            "course_study_url": "https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu?courseid=261641822&enc=abc&t=123",
        }
    ]

    save_init_config(str(config_path), cookie="UID=1; vc3=abc", warmed_courses=warmed_courses, cache_path=str(cache_path))
    state = load_cache(str(cache_path))

    assert len(state.courses) == 1
    assert state.courses[0].course_id == "261641822"
    assert state.courses[0].course_study_url.endswith("enc=abc&t=123")


def test_is_logged_in_home_page_requires_course_entry() -> None:
    assert is_logged_in_home_page("https://i.chaoxing.com/base?ws=1", 'dataurl="https://mooc1-1.chaoxing.com/visit/interaction?s=abc"')
    assert not is_logged_in_home_page("https://passport2.chaoxing.com/login", "<title>用户登录</title>")
    assert not is_logged_in_home_page("https://i.chaoxing.com/base?ws=1", "<title>空间</title>")


def test_warm_course_cookies_visits_course_entries() -> None:
    requested_urls: list[str] = []

    records_cookie, records = warm_course_cookies("UID=1; vc3=abc", client_factory=_make_course_client_factory(requested_urls))

    assert len(records) == 1
    assert records_cookie == "UID=1; vc3=abc; 261641822enc=enc; 261641822t=178065"
    assert "https://mooc1-1.chaoxing.com/mooc-ans/visit/stucoursemiddle?courseid=261641822&clazzid=142332957&cpi=407073562" in requested_urls
    assert records[0].course_study_url.endswith("enc=enc&t=178065")


def test_warm_course_cookies_waits_before_each_course_entry() -> None:
    sleeps: list[float] = []

    warm_course_cookies("UID=1; vc3=abc", course_delay=1.5, client_factory=_make_course_client_factory([]), sleep=sleeps.append)

    assert sleeps == [1.5]


def test_warm_course_cookies_rejects_negative_course_delay() -> None:
    try:
        warm_course_cookies("UID=1; vc3=abc", course_delay=-0.1)
    except ValueError as exc:
        assert "course_delay" in str(exc)
        return

    raise AssertionError("expected ValueError")


def test_warm_course_cookies_can_be_cancelled_before_request() -> None:
    try:
        warm_course_cookies("UID=1; vc3=abc", cancel_check=lambda: True)
    except InitCancelled:
        return

    raise AssertionError("expected InitCancelled")


def test_warm_course_cookies_can_be_cancelled_between_courses() -> None:
    requested_urls: list[str] = []
    calls = 0

    def cancel_check() -> bool:
        nonlocal calls
        calls += 1
        return calls >= 2

    try:
        warm_course_cookies("UID=1; vc3=abc", cancel_check=cancel_check, client_factory=_make_course_client_factory(requested_urls))
    except InitCancelled:
        assert len(requested_urls) == 2
        assert requested_urls[0].startswith("https://i.chaoxing.com/base?ws=1&t=")
        assert requested_urls[1] == "https://mooc1-1.chaoxing.com/visit/interaction?s=abc"
        return

    raise AssertionError("expected InitCancelled")


def test_warm_course_cookies_reports_course_cookie_status() -> None:
    events: list[tuple[str, str]] = []

    warm_course_cookies("UID=1; vc3=abc", client_factory=_make_course_client_factory([]), progress=lambda kind, message: events.append((kind, message)))

    assert ("course_cookie", "已采集课程入口参数：大学生职业发展与就业指导") in events


def test_collect_cookie_header_with_browser_uses_page_then_http_warmer() -> None:
    page = FakePage(
        cookies=[
            {"name": "UID", "value": "1", "domain": ".chaoxing.com"},
            {"name": "vc3", "value": "abc", "domain": ".chaoxing.com"},
        ]
    )

    cookie, warmed_courses = collect_cookie_header_with_browser(
        user_data_dir=".browser",
        login_url="https://i.chaoxing.com/",
        timeout_seconds=3,
        page_factory=lambda user_data_dir: page,
        warm_impl=lambda cookie_header, **kwargs: (cookie_header + "; warmed=1", []),
        sleep=lambda seconds: None,
    )

    assert page.visited == ["https://i.chaoxing.com/"]
    assert page.closed
    assert cookie == "UID=1; vc3=abc; warmed=1"
    assert warmed_courses == []


def _make_course_client_factory(requested_urls: list[str]):
    course_list_html = """
        <ul id="courseList">
          <li class="course" courseid="261641822" clazzid="142332957" personid="407073562">
            <div class="course-name">大学生职业发展与就业指导</div>
            <div class="course-info">
              <a href="https://mooc1-1.chaoxing.com/mooc-ans/visit/stucoursemiddle?courseid=261641822&clazzid=142332957&cpi=407073562">进入</a>
              <p></p><p>谢伟</p>
            </div>
          </li>
        </ul>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if request.url.host == "i.chaoxing.com":
            return httpx.Response(200, text='dataurl="https://mooc1-1.chaoxing.com/visit/interaction?s=abc"')
        if str(request.url) == "https://mooc1-1.chaoxing.com/visit/interaction?s=abc":
            return httpx.Response(200, text="")
        if str(request.url) == "https://mooc1-1.chaoxing.com/mooc-ans/visit/courselistdata":
            assert request.method == "POST"
            return httpx.Response(200, text=course_list_html)
        if request.url.path.endswith("/mooc-ans/visit/stucoursemiddle"):
            return httpx.Response(
                302,
                headers=[
                    ("Location", "https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu?courseid=261641822&enc=enc&t=178065"),
                    ("Set-Cookie", "261641822enc=enc; Domain=.chaoxing.com; Path=/"),
                    ("Set-Cookie", "261641822t=178065; Domain=.chaoxing.com; Path=/"),
                ],
            )
        if request.url.path.endswith("/mooc2-ans/mycourse/stu"):
            return httpx.Response(200, text="")
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    def factory(cookie_header: str) -> httpx.Client:
        return httpx.Client(
            transport=httpx.MockTransport(handler),
            cookies={"UID": "1", "vc3": "abc"},
            follow_redirects=True,
        )

    return factory


class FakePage:
    def __init__(self, *, cookies: list[dict[str, str]]) -> None:
        self._cookies = cookies
        self.visited: list[str] = []
        self.closed = False

    def get(self, url: str) -> None:
        self.visited.append(url)

    def get_cookies(self, as_dict: bool = False) -> list[dict[str, str]]:
        return self._cookies

    def quit(self) -> None:
        self.closed = True
