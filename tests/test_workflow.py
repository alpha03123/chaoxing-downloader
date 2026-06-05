from pathlib import Path

import httpx

from chaoxing_downloader.cache_store import save_cache
from chaoxing_downloader.http_client import ChaoxingClient
from chaoxing_downloader.models import AppConfig, CacheState, ChapterRecord, CourseRecord, VideoRecord
from chaoxing_downloader.session import SessionConfig
from chaoxing_downloader.workflow import download_video, list_chapters, list_courses, list_videos


def test_list_chapters_resolves_studentcourse_from_course_shell(tmp_path) -> None:
    cache_path = tmp_path / "cache.json"
    save_cache(
        str(cache_path),
        CacheState(
            courses=[
                CourseRecord(
                    course_key="course-demo",
                    course_id="261641755",
                    clazz_id="142332962",
                    cpi="407073562",
                    enc="",
                    title="demo",
                    teacher="",
                    open_time="",
                    course_url="https://mooc1-1.chaoxing.com/mooc-ans/visit/stucoursemiddle?courseid=261641755&clazzid=142332962&cpi=407073562",
                )
            ]
        ),
    )
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        if request.url.path.endswith("/stucoursemiddle"):
            return httpx.Response(302, headers={"Location": "https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu?courseid=261641755&clazzid=142332962&cpi=407073562&enc=main-enc&t=1780576965087&pageHeader=-1&v=2&hideHead=0"})
        if request.url.path.endswith("/mycourse/stu"):
            return httpx.Response(200, text="""
                <input type="hidden" id="courseid" value="261641755"/>
                <input type="hidden" id="clazzid" value="142332962"/>
                <input type="hidden" id="cpi" value="407073562"/>
                <input type="hidden" id="enc" value="main-enc"/>
                <input type="hidden" id="openc" value="open-enc"/>
                <input type="hidden" id="t" value="1780576965087"/>
                <input type="hidden" id="v" value="2"/>
                <a data-url="/mooc2-ans/mycourse/studentcourse" title="章节"></a>
            """)
        if request.url.path.endswith("/mycourse/studentcourse"):
            assert request.url.host == "mooc2-ans.chaoxing.com"
            assert request.url.params["courseid"] == "261641755"
            assert request.url.params["clazzid"] == "142332962"
            assert request.url.params["cpi"] == "407073562"
            assert request.url.params["enc"] == "main-enc"
            assert request.url.params["openc"] == "open-enc"
            return httpx.Response(200, text="""
                <input type="hidden" id="cpi" value="407073562"/>
                <input type="hidden" id="courseId" value="261641755"/>
                <input type="hidden" id="clazzId" value="142332962"/>
                <input type="hidden" id="enc" value="chapter-enc"/>
                <input type="hidden" id="openc" value="open-enc"/>
                <input type="hidden" id="t" value="1780576965087"/>
                <input type="hidden" id="moocDomainName" value="https://mooc1.chaoxing.com"/>
                <div class="chapter_item" id="cur705029508">
                    <div class="catalog_name"><span class="catalog_sbar">1.1</span> 符号的作用</div>
                </div>
            """)
        return httpx.Response(404)

    client = ChaoxingClient(
        SessionConfig(cookie="UID=1"),
        transport=httpx.MockTransport(handler),
    )
    config = AppConfig(cookie="UID=1", referer="", cache_path=str(cache_path))

    records = list_chapters(client, config, course_key="course-demo")

    assert [item.chapter_id for item in records] == ["705029508"]
    assert "/mooc2-ans/mycourse/studentcourse" in seen_paths


def test_list_courses_adds_dynamic_params_for_base_entry(tmp_path) -> None:
    cache_path = tmp_path / "cache.json"
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if request.url.path == "/base":
            assert request.url.params["ws"] == "1"
            assert request.url.params["t"]
            return httpx.Response(200, text='dataurl="https://mooc1-1.chaoxing.com/visit/interaction?s=abc"')
        if request.url.path == "/visit/interaction":
            return httpx.Response(200, text="")
        if request.url.path == "/mooc-ans/visit/courselistdata":
            return httpx.Response(200, text="")
        return httpx.Response(404)

    client = ChaoxingClient(
        SessionConfig(cookie="UID=1"),
        transport=httpx.MockTransport(handler),
    )
    config = AppConfig(cookie="UID=1", referer="", base_url="https://i.chaoxing.com/base", cache_path=str(cache_path))

    assert list_courses(client, config) == []
    assert requested_urls[0].startswith("https://i.chaoxing.com/base?ws=1&t=")


def test_list_chapters_uses_course_cookie_when_redirect_requires_login(tmp_path) -> None:
    cache_path = tmp_path / "cache.json"
    save_cache(
        str(cache_path),
        CacheState(
            courses=[
                CourseRecord(
                    course_key="course-demo",
                    course_id="261641755",
                    clazz_id="142332962",
                    cpi="407073562",
                    enc="",
                    title="demo",
                    teacher="",
                    open_time="",
                    course_url="https://mooc1-1.chaoxing.com/mooc-ans/visit/stucoursemiddle?courseid=261641755&clazzid=142332962&cpi=407073562",
                )
            ]
        ),
    )
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if request.url.path.endswith("/stucoursemiddle"):
            return httpx.Response(302, headers={"Location": "https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu?courseid=261641755&clazzid=142332962&cpi=407073562&enc=redirect-enc&t=1780651156163&pageHeader=-1&v=2&hideHead=0"})
        if request.url.host == "mooc2-ans.chaoxing.com" and request.url.params.get("enc") == "redirect-enc":
            return httpx.Response(302, headers={"Location": "https://passport2.chaoxing.com/login"})
        if request.url.host == "passport2.chaoxing.com":
            return httpx.Response(200, text="<title>用户登录</title>")
        if request.url.path.endswith("/mycourse/stu"):
            assert request.url.params["enc"] == "cookie-enc"
            assert request.url.params["t"] == "1780576245352"
            return httpx.Response(200, text="""
                <input type="hidden" id="courseid" value="261641755"/>
                <input type="hidden" id="clazzid" value="142332962"/>
                <input type="hidden" id="cpi" value="407073562"/>
                <input type="hidden" id="enc" value="cookie-enc"/>
                <input type="hidden" id="openc" value="open-enc"/>
                <input type="hidden" id="t" value="1780576245352"/>
                <input type="hidden" id="v" value="2"/>
                <a data-url="/mooc2-ans/mycourse/studentcourse" title="章节"></a>
            """)
        if request.url.path.endswith("/mycourse/studentcourse"):
            assert request.url.host == "mooc2-ans.chaoxing.com"
            return httpx.Response(200, text="""
                <input type="hidden" id="cpi" value="407073562"/>
                <input type="hidden" id="courseId" value="261641755"/>
                <input type="hidden" id="clazzId" value="142332962"/>
                <input type="hidden" id="enc" value="chapter-enc"/>
                <input type="hidden" id="openc" value="open-enc"/>
                <input type="hidden" id="t" value="1780576245352"/>
                <input type="hidden" id="moocDomainName" value="https://mooc1.chaoxing.com"/>
                <div class="chapter_item" id="cur705029508">
                    <div class="catalog_name"><span class="catalog_sbar">1.1</span> 符号的作用</div>
                </div>
            """)
        return httpx.Response(404)

    client = ChaoxingClient(
        SessionConfig(cookie="UID=1"),
        transport=httpx.MockTransport(handler),
    )
    config = AppConfig(
        cookie="261641755cpi=407073562; 261641755enc=cookie-enc; 261641755t=1780576245352; 261641755ut=s",
        referer="",
        cache_path=str(cache_path),
    )

    records = list_chapters(client, config, course_key="course-demo")

    assert [item.chapter_id for item in records] == ["705029508"]
    assert any("enc=cookie-enc" in url for url in requested_urls)


def test_list_chapters_uses_cached_course_study_url_before_course_cookie(tmp_path) -> None:
    cache_path = tmp_path / "cache.json"
    save_cache(
        str(cache_path),
        CacheState(
            courses=[
                CourseRecord(
                    course_key="course-demo",
                    course_id="261641822",
                    clazz_id="142332957",
                    cpi="407073562",
                    enc="",
                    title="demo",
                    teacher="",
                    open_time="",
                    course_url="https://mooc1-1.chaoxing.com/mooc-ans/visit/stucoursemiddle?courseid=261641822&clazzid=142332957&cpi=407073562",
                    course_study_url="https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu?courseid=261641822&clazzid=142332957&cpi=407073562&enc=cached-enc&t=1780654276465&pageHeader=1&v=2&hideHead=0",
                )
            ]
        ),
    )
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if request.url.path.endswith("/stucoursemiddle"):
            return httpx.Response(302, headers={"Location": "https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu?courseid=261641822&clazzid=142332957&cpi=407073562&enc=redirect-enc&t=1780651156163&pageHeader=-1&v=2&hideHead=0"})
        if request.url.host == "mooc2-ans.chaoxing.com" and request.url.params.get("enc") == "redirect-enc":
            return httpx.Response(302, headers={"Location": "https://passport2.chaoxing.com/login"})
        if request.url.host == "passport2.chaoxing.com":
            return httpx.Response(200, text="<title>用户登录</title>")
        if request.url.path.endswith("/mycourse/stu"):
            assert request.url.params["enc"] == "cached-enc"
            return httpx.Response(200, text="""
                <input type="hidden" id="courseid" value="261641822"/>
                <input type="hidden" id="clazzid" value="142332957"/>
                <input type="hidden" id="cpi" value="407073562"/>
                <input type="hidden" id="enc" value="cached-enc"/>
                <input type="hidden" id="openc" value="open-enc"/>
                <input type="hidden" id="t" value="1780654276465"/>
                <input type="hidden" id="v" value="2"/>
                <a data-url="/mooc2-ans/mycourse/studentcourse" title="章节"></a>
            """)
        if request.url.path.endswith("/mycourse/studentcourse"):
            return httpx.Response(200, text="""
                <input type="hidden" id="cpi" value="407073562"/>
                <input type="hidden" id="courseId" value="261641822"/>
                <input type="hidden" id="clazzId" value="142332957"/>
                <input type="hidden" id="enc" value="chapter-enc"/>
                <input type="hidden" id="openc" value="open-enc"/>
                <input type="hidden" id="t" value="1780654276465"/>
                <input type="hidden" id="moocDomainName" value="https://mooc1.chaoxing.com"/>
                <div class="chapter_item" id="cur705061572">
                    <div class="catalog_name"><span class="catalog_sbar">1.1</span> 测试章节</div>
                </div>
            """)
        return httpx.Response(404)

    client = ChaoxingClient(
        SessionConfig(cookie="UID=1"),
        transport=httpx.MockTransport(handler),
    )
    config = AppConfig(cookie="UID=1", referer="", cache_path=str(cache_path))

    records = list_chapters(client, config, course_key="course-demo")

    assert [item.chapter_id for item in records] == ["705061572"]
    assert any("enc=cached-enc" in url for url in requested_urls)


def test_list_videos_loads_knowledge_cards_when_studentstudy_is_shell(tmp_path) -> None:
    cache_path = tmp_path / "cache.json"
    save_cache(
        str(cache_path),
        CacheState(
            chapters=[
                ChapterRecord(
                    chapter_key="chapter-demo",
                    chapter_id="705029508",
                    course_key="course-demo",
                    title="符号的作用",
                    order="1.1",
                    studentstudy_url="https://mooc1.chaoxing.com/mycourse/studentstudy?chapterId=705029508&courseId=261641755&clazzid=142332962&cpi=407073562",
                )
            ]
        ),
    )
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path.endswith("/mycourse/studentstudy"):
            return httpx.Response(200, text="""
                <input type="hidden" id="curCourseId" value="261641755"/>
                <input type="hidden" id="curChapterId" value="705029508"/>
                <input type="hidden" id="curCpi" value="407073562"/>
                <input type="hidden" id="curClazzId" value="142332962"/>
                <input type="hidden" id="isMicroCourse" value="false"/>
            """)
        if request.url.path.endswith("/knowledge/cards"):
            assert request.url.params["courseid"] == "261641755"
            assert request.url.params["knowledgeid"] == "705029508"
            assert request.url.params["clazzid"] == "142332962"
            assert request.url.params["cpi"] == "407073562"
            return httpx.Response(200, text="""
                <script>
                  mArg = {"attachments":[{"type":"video","jobid":"job-1","mid":"mid-1","topicList":[{"name":"符号的作用"}],"property":{"name":"1.1.mp4","objectid":"object-1","jobid":"job-1","mid":"mid-1"},"objectId":"object-1"}],"coursename":"意义生活：符号学导论","knowledgename":"符号的作用"};
                </script>
            """)
        if request.url.path.endswith("/ananas/status/object-1"):
            return httpx.Response(200, json={"status": "success", "objectid": "object-1", "http": "https://cdn.example.test/1.mp4", "duration": 681, "length": 438140166, "filename": "1.1.mp4"})
        return httpx.Response(404)

    client = ChaoxingClient(
        SessionConfig(cookie="UID=1"),
        transport=httpx.MockTransport(handler),
    )
    config = AppConfig(cookie="UID=1", referer="", cache_path=str(cache_path))

    records = list_videos(client, config, chapter_key="chapter-demo")

    assert [item.object_id for item in records] == ["object-1"]
    assert records[0].media_url == "https://cdn.example.test/1.mp4"
    assert "/mooc-ans/knowledge/cards" in requested_paths


def test_download_video_writes_to_explicit_output_dir(tmp_path) -> None:
    cache_path = tmp_path / "cache.json"
    output_dir = tmp_path / "custom-downloads"
    progress_calls: list[tuple[int, int | None]] = []
    save_cache(
        str(cache_path),
        CacheState(
            videos=[
                VideoRecord(
                    video_key="video-demo",
                    chapter_key="chapter-demo",
                    title="demo",
                    object_id="object-1",
                    job_id="job-1",
                    mid="mid-1",
                    media_url="https://cdn.example.test/1.mp4",
                    filename="1.1.mp4",
                )
            ]
        ),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://cdn.example.test/1.mp4":
            return httpx.Response(200, content=b"video-bytes")
        return httpx.Response(404)

    client = ChaoxingClient(
        SessionConfig(cookie="UID=1"),
        transport=httpx.MockTransport(handler),
    )
    config = AppConfig(
        cookie="UID=1",
        referer="",
        output_dir=str(tmp_path / "default-downloads"),
        cache_path=str(cache_path),
    )

    path = download_video(
        client,
        config,
        video_key="video-demo",
        output_dir=output_dir,
        progress=lambda downloaded, total: progress_calls.append((downloaded, total)),
    )

    assert path == output_dir / "1.1.mp4"
    assert path.read_bytes() == b"video-bytes"
    assert progress_calls == [(11, 11)]
