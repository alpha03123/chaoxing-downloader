from pathlib import Path

from chaoxing_downloader.course_parser import parse_course_page
from chaoxing_downloader.media_resolver import resolve_media_url


def test_fixture_smoke_flow() -> None:
    html = Path("tests/fixtures/studentstudy_sample.html").read_text(encoding="utf-8")
    course = parse_course_page(html)
    assert course.title
    assert course.chapters
    media = resolve_media_url(html)
    assert media.startswith("http")
