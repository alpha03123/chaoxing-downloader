from pathlib import Path

from chaoxing_downloader.course_catalog_parser import parse_course_list, parse_student_course


def test_parse_course_list_extracts_course_records() -> None:
    html = Path("tests/fixtures/courselist_sample.html").read_text(encoding="utf-8")

    records = parse_course_list(html)

    assert len(records) == 1
    course = records[0]
    assert course.course_id == "261641822"
    assert course.clazz_id == "142332957"
    assert course.cpi == "407073562"
    assert course.enc == "abc123"
    assert course.title == "大学生职业发展与就业指导"
    assert course.teacher == "谢伟"


def test_parse_student_course_extracts_studentstudy_url() -> None:
    html = Path("tests/fixtures/studentcourse_sample.html").read_text(encoding="utf-8")

    records = parse_student_course(html, course_key="course-demo")

    assert len(records) == 1
    chapter = records[0]
    assert chapter.chapter_id == "705029508"
    assert chapter.course_key == "course-demo"
    assert chapter.order == "1.1"
    assert chapter.title == "符号的作用"
    assert "chapterId=705029508" in chapter.studentstudy_url
    assert "courseId=261641755" in chapter.studentstudy_url
