from pathlib import Path

from chaoxing_downloader.auth_init import (
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
    page = FakePage(
        home_html='dataurl="https://mooc1-1.chaoxing.com/visit/interaction?s=abc"',
        course_list_html="""
            <ul id="courseList">
              <li class="course" courseid="261641822" clazzid="142332957" personid="407073562">
                <div class="course-name">大学生职业发展与就业指导</div>
                <div class="course-info">
                  <a href="https://mooc1-1.chaoxing.com/mooc-ans/visit/stucoursemiddle?courseid=261641822&clazzid=142332957&cpi=407073562">进入</a>
                  <p></p><p>谢伟</p>
                </div>
              </li>
            </ul>
        """,
    )

    records = warm_course_cookies(page)

    assert len(records) == 1
    assert page.visited[-1] == "https://mooc1-1.chaoxing.com/mooc-ans/visit/stucoursemiddle?courseid=261641822&clazzid=142332957&cpi=407073562"


def test_warm_course_cookies_reports_course_cookie_status() -> None:
    events: list[tuple[str, str]] = []
    page = FakePage(
        home_html='dataurl="https://mooc1-1.chaoxing.com/visit/interaction?s=abc"',
        course_list_html="""
            <ul id="courseList">
              <li class="course" courseid="261641822" clazzid="142332957" personid="407073562">
                <div class="course-name">大学生职业发展与就业指导</div>
                <div class="course-info">
                  <a href="https://mooc1-1.chaoxing.com/mooc-ans/visit/stucoursemiddle?courseid=261641822&clazzid=142332957&cpi=407073562">进入</a>
                  <p></p><p>谢伟</p>
                </div>
              </li>
            </ul>
        """,
        cookies=[
            {"name": "261641822enc", "value": "enc", "domain": ".chaoxing.com"},
            {"name": "261641822t", "value": "178065", "domain": ".chaoxing.com"},
        ],
    )

    warm_course_cookies(page, progress=lambda kind, message: events.append((kind, message)))

    assert ("course_cookie", "已采集课程入口参数：大学生职业发展与就业指导") in events


class FakePage:
    def __init__(self, *, home_html: str, course_list_html: str, cookies: list[dict[str, str]] | None = None) -> None:
        self.home_html = home_html
        self.course_list_html = course_list_html
        self._cookies = cookies or []
        self.visited: list[str] = []
        self.request = FakeRequest(course_list_html)
        self.context = self
        self.url = ""

    def goto(self, url: str, wait_until: str = "") -> None:
        self.visited.append(url)
        self.url = url

    def content(self) -> str:
        return self.home_html

    def wait_for_timeout(self, timeout: int) -> None:
        return None

    def cookies(self) -> list[dict[str, str]]:
        return self._cookies


class FakeRequest:
    def __init__(self, course_list_html: str) -> None:
        self.course_list_html = course_list_html

    def post(self, url: str, form: dict[str, str]):
        assert url == "https://mooc1-1.chaoxing.com/mooc-ans/visit/courselistdata"
        assert form["courseType"] == "1"
        return FakeResponse(self.course_list_html)


class FakeResponse:
    def __init__(self, text: str) -> None:
        self._text = text

    def text(self) -> str:
        return self._text
