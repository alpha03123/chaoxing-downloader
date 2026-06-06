from pathlib import Path

from chaoxing_downloader.course_parser import UnsupportedChapterError, parse_course_page


def test_parse_course_page_extracts_chapters() -> None:
    html = Path("tests/fixtures/studentstudy_sample.html").read_text(encoding="utf-8")
    course = parse_course_page(html)
    assert course.title
    assert len(course.chapters) >= 1
    assert any(task.kind == "video" for chapter in course.chapters for task in chapter.tasks)


def test_parse_course_page_reports_unsupported_chapter() -> None:
    html = """
        <html>
          <head><title>学习目标</title></head>
          <body>
            <script>mArg = {"attachments":[],"knowledgename":"职业世界地图"};</script>
            <p>通过本章学习，你需要掌握和了解以下问题</p>
          </body>
        </html>
    """

    try:
        parse_course_page(html)
    except UnsupportedChapterError as exc:
        assert "暂不支持解析视频任务点" in str(exc)
        assert "学习目标" in str(exc)
        return

    raise AssertionError("expected UnsupportedChapterError")
