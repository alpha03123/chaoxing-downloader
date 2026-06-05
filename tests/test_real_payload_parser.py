from pathlib import Path

from chaoxing_downloader.course_parser import parse_course_page


def test_parse_real_payload_extracts_object_id() -> None:
    html = Path("tests/fixtures/studentstudy_sample.html").read_text(encoding="utf-8")
    course = parse_course_page(html)
    task = course.chapters[0].tasks[0]
    assert course.title == "示例课程"
    assert task.object_id == "object-1"
    assert task.job_id == "job-1"
    assert task.mid == "mid-1"
