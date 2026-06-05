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
