from chaoxing_downloader.cli import build_parser


def test_help_includes_inspect_course() -> None:
    parser = build_parser()
    help_text = parser.format_help()
    assert "inspect-course" in help_text
    assert "list-courses" in help_text
    assert "list-chapters" in help_text
    assert "list-videos" in help_text
    assert "download-video" in help_text
    assert "clear-cache" in help_text
    assert "init" in help_text


def test_parser_accepts_request_delay() -> None:
    parser = build_parser()

    args = parser.parse_args(["list-videos", "--chapter", "chapter-demo", "--delay", "1.5"])

    assert args.delay == 1.5


def test_parser_accepts_course_delay_for_init() -> None:
    parser = build_parser()

    args = parser.parse_args(["init", "--course-delay", "2.5"])

    assert args.course_delay == 2.5
