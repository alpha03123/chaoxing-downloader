from pathlib import Path

from chaoxing_downloader import ChaoxingDownloader, CourseRecord
import chaoxing_downloader.api as api_module
from chaoxing_downloader.cache_store import load_cache
from chaoxing_downloader.models import AppConfig


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


def test_downloader_init_writes_state_dir(tmp_path: Path) -> None:
    state_dir = tmp_path / ".chaoxing"

    def collect_impl(**kwargs):
        assert kwargs["user_data_dir"] == str(state_dir / "browser")
        return (
            "UID=1; vc3=abc",
            [
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
                    course_study_url="https://example.test/study?enc=abc&t=123",
                )
            ],
        )

    downloader = ChaoxingDownloader.init(state_dir=str(state_dir), collect_impl=collect_impl)
    state = load_cache(str(state_dir / "cache.json"))

    assert isinstance(downloader, ChaoxingDownloader)
    assert (state_dir / "session.json").exists()
    assert state.courses[0].course_study_url.endswith("enc=abc&t=123")


def test_downloader_load_reads_state_dir(tmp_path: Path) -> None:
    state_dir = tmp_path / ".chaoxing"
    state_dir.mkdir()
    (state_dir / "session.json").write_text(
        """
{
  "cookie": "UID=1; vc3=abc",
  "referer": "https://mooc1.chaoxing.com/",
  "base_url": "https://i.chaoxing.com/base",
  "output_dir": "downloads",
  "cache_path": "cache.json"
}
""".strip(),
        encoding="utf-8",
    )

    downloader = ChaoxingDownloader.load(state_dir=str(state_dir))

    assert downloader.config.cookie == "UID=1; vc3=abc"
    assert downloader.config.cache_path == str(state_dir / "cache.json")


def test_downloader_is_initialized_returns_false_when_state_missing(tmp_path: Path) -> None:
    state_dir = tmp_path / ".chaoxing"

    assert not ChaoxingDownloader.is_initialized(state_dir=str(state_dir))


def test_downloader_is_initialized_validates_cookie_with_home_page(monkeypatch, tmp_path: Path) -> None:
    state_dir = tmp_path / ".chaoxing"
    requested_urls: list[str] = []

    class FakeClient:
        def __init__(self, session_config):
            assert session_config.cookie == "UID=1"

        def get_text(self, url: str) -> str:
            requested_urls.append(url)
            return 'dataurl="https://mooc1-1.chaoxing.com/visit/interaction?s=abc"'

    monkeypatch.setattr(api_module, "load_config_from_state", lambda paths: AppConfig(cookie="UID=1", referer="", base_url="https://i.chaoxing.com/base"))
    monkeypatch.setattr(api_module, "ChaoxingClient", FakeClient)

    assert ChaoxingDownloader.is_initialized(state_dir=str(state_dir))
    assert requested_urls and requested_urls[0].startswith("https://i.chaoxing.com/base?ws=1&t=")


def test_downloader_is_initialized_returns_false_when_cookie_expired(monkeypatch, tmp_path: Path) -> None:
    class FakeClient:
        def __init__(self, session_config):
            pass

        def get_text(self, url: str) -> str:
            return "<title>用户登录</title>"

    monkeypatch.setattr(api_module, "load_config_from_state", lambda paths: AppConfig(cookie="UID=1", referer="", base_url="https://i.chaoxing.com/base"))
    monkeypatch.setattr(api_module, "ChaoxingClient", FakeClient)

    assert not ChaoxingDownloader.is_initialized(state_dir=str(tmp_path / ".chaoxing"))


def test_downloader_download_video_passes_options() -> None:
    progress_calls: list[tuple[int, int | None]] = []
    calls: list[tuple[str, str | Path | None, str | None, object]] = []

    def progress(downloaded: int, total: int | None) -> None:
        progress_calls.append((downloaded, total))

    def download_video_impl(client, config, *, video_key: str, output_dir=None, filename=None, progress=None) -> Path:
        calls.append((video_key, output_dir, filename, progress))
        return Path("custom/video.mp4")

    downloader = ChaoxingDownloader(
        AppConfig(cookie="UID=1", referer="", base_url="https://i.chaoxing.com/base"),
        client=object(),
        download_video_impl=download_video_impl,
    )

    path = downloader.download_video("video-demo", output_dir="my-downloads", filename="custom.mp4", progress=progress)

    assert path == Path("custom/video.mp4")
    assert calls == [("video-demo", "my-downloads", "custom.mp4", progress)]
    assert progress_calls == []
