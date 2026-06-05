from pathlib import Path

from chaoxing_downloader import ChaoxingDownloader, CourseRecord, load_downloader
from chaoxing_downloader.models import AppConfig


def test_load_downloader_from_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[session]
cookie = "UID=1"
referer = "https://mooc1.chaoxing.com/"

[entry]
base_url = "https://i.chaoxing.com/base"
""".strip(),
        encoding="utf-8",
    )

    downloader = load_downloader(str(config_path))

    assert isinstance(downloader, ChaoxingDownloader)


def test_downloader_list_courses_delegates_workflow() -> None:
    calls: list[str] = []

    def list_courses_impl(client, config, *, url_override=""):
        calls.append(url_override)
        return [
            CourseRecord(
                course_key="course-demo",
                course_id="1",
                clazz_id="2",
                cpi="3",
                enc="",
                title="demo",
                teacher="",
                open_time="",
                course_url="https://example.test/course",
            )
        ]

    downloader = ChaoxingDownloader(
        AppConfig(cookie="UID=1", referer="", base_url="https://i.chaoxing.com/base"),
        client=object(),
        list_courses_impl=list_courses_impl,
    )

    records = downloader.list_courses(url="https://i.chaoxing.com/base")

    assert records[0].course_key == "course-demo"
    assert calls == ["https://i.chaoxing.com/base"]
