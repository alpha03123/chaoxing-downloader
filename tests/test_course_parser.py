from pathlib import Path

from chaoxing_downloader.course_parser import parse_course_page


def test_parse_course_page_extracts_chapters() -> None:
    html = Path("tests/fixtures/studentstudy_sample.html").read_text(encoding="utf-8")
    course = parse_course_page(html)
    assert course.title
    assert len(course.chapters) >= 1
    assert any(task.kind == "video" for chapter in course.chapters for task in chapter.tasks)
