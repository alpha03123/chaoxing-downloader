# API Reference



```python
from chaoxing_downloader import (
    ChaoxingDownloader,
    CourseRecord,
    ChapterRecord,
    VideoRecord,
)
```

## `ChaoxingDownloader.init()`

```python
downloader = ChaoxingDownloader.init(
    state_dir=".chaoxing",
    timeout_seconds=300,
)
```

启动有头 Chromium，等待用户手动登录超星，登录成功后自动采集登录 Cookie、课程列表和课程入口参数，并写入 `state_dir`。

参数：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `state_dir` | `str` | `".chaoxing"` | 库模式状态目录 |
| `timeout_seconds` | `int` | `300` | 等待登录的超时秒数 |

返回：

| 类型 | 说明 |
| --- | --- |
| `ChaoxingDownloader` | 已登录并可直接查询的下载器实例 |

返回示例：

```python
ChaoxingDownloader(...)
```

`ChaoxingDownloader` 不建议直接读取内部属性。后续通常继续调用：

```python
courses = downloader.list_courses()
```

说明：

- 这是阻塞式 API，会弹出浏览器。
- 浏览器用户数据、session、缓存和默认下载目录都在 `state_dir` 下。


## `ChaoxingDownloader.load()`

```python
downloader = ChaoxingDownloader.load(state_dir=".chaoxing")
```

从已存在的 `state_dir` 加载登录状态，不弹浏览器。

参数：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `state_dir` | `str` | `".chaoxing"` | 与 `init()` 相同的状态目录 |

返回：

| 类型 | 说明 |
| --- | --- |
| `ChaoxingDownloader` | 从本地状态恢复的下载器实例 |

返回示例：

```python
ChaoxingDownloader(...)
```

如果 `session.json` 不存在，会抛出错误并提示先调用 `ChaoxingDownloader.init()`。

## `ChaoxingDownloader.is_initialized()`

```python
ready = ChaoxingDownloader.is_initialized(state_dir=".chaoxing")
```

判断指定 `state_dir` 是否已经存在可用登录状态。

参数：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `state_dir` | `str` | `".chaoxing"` | 与 `init()` / `load()` 相同的状态目录 |

返回：

| 类型 | 说明 |
| --- | --- |
| `bool` | 本地状态存在且 Cookie 仍可访问学习通课程主页时为 `True`，否则为 `False` |

示例：

```python
if ChaoxingDownloader.is_initialized(state_dir=".chaoxing"):
    downloader = ChaoxingDownloader.load(state_dir=".chaoxing")
else:
    downloader = ChaoxingDownloader.init(state_dir=".chaoxing")
```

这个方法会联网请求学习通课程主页，用于避免本地 `session.json` 存在但 Cookie 已过期时仍返回 `True`。本地状态不存在、状态文件损坏、Cookie 失效或请求失败都会返回 `False`。

## `list_courses()`

```python
courses = downloader.list_courses()
```

返回当前账号可见的课程列表。

参数：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `url` | `str` | `""` | 可选覆盖课程主页入口；普通使用不需要传 |

返回：

| 类型 | 说明 |
| --- | --- |
| `list[CourseRecord]` | 课程记录列表 |

返回示例：

```python
[
    CourseRecord(
        course_key="course-98***ce",
        course_id="261***822",
        clazz_id="142***957",
        cpi="407***562",
        enc="",
        title="大学生***就业指导",
        teacher="谢*",
        open_time="2026-03-**～2026-07-**",
        course_url="https://mooc1-1.chaoxing.com/mooc-ans/visit/stucoursemiddle?courseid=261***822&clazzid=142***957&cpi=407***562&ismooc2=1&v=2",
        course_study_url="https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu?courseid=261***822&clazzid=142***957&cpi=407***562&enc=7f***8e&t=178***465",
    ),
    CourseRecord(
        course_key="course-54***b5",
        course_id="261***755",
        clazz_id="142***962",
        cpi="407***562",
        enc="",
        title="意义***导论",
        teacher="",
        open_time="",
        course_url="https://mooc1-1.chaoxing.com/mooc-ans/visit/stucoursemiddle?courseid=261***755&clazzid=142***962&cpi=407***562&ismooc2=1&v=2",
        course_study_url="https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu?courseid=261***755&clazzid=142***962&cpi=407***562&enc=c7***e1&t=178***352",
    ),
]
```

`CourseRecord` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `course_key` | `str` | 本地稳定 key，如 `course-54***b5` |
| `course_id` | `str` | 超星课程 ID |
| `clazz_id` | `str` | 班级 ID |
| `cpi` | `str` | 个人课程 ID |
| `enc` | `str` | 课程入口签名参数，可能为空 |
| `title` | `str` | 课程名称 |
| `teacher` | `str` | 教师名称 |
| `open_time` | `str` | 开课时间 |
| `course_url` | `str` | 课程入口 URL |
| `course_study_url` | `str` | 预热后得到的课程学习页 URL |

## `list_chapters()`

```python
chapters = downloader.list_chapters(course_key)
```

根据课程 key 返回章节列表。

参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `course_key` | `str` | 来自 `CourseRecord.course_key` |

返回：

| 类型 | 说明 |
| --- | --- |
| `list[ChapterRecord]` | 章节记录列表 |

返回示例：

```python
[
    ChapterRecord(
        chapter_key="chapter-04***f3",
        chapter_id="705***508",
        course_key="course-54***b5",
        title="符***作用",
        order="1.1",
        studentstudy_url="https://mooc1.chaoxing.com/mycourse/studentstudy?chapterId=705***508&courseId=261***755&clazzid=142***962&cpi=407***562&enc=c7***e1",
    ),
    ChapterRecord(
        chapter_key="chapter-04***21",
        chapter_id="705***509",
        course_key="course-54***b5",
        title="“符***”的种种误用",
        order="1.2",
        studentstudy_url="https://mooc1.chaoxing.com/mycourse/studentstudy?chapterId=705***509&courseId=261***755&clazzid=142***962&cpi=407***562&enc=c7***e1",
    ),
]
```

`ChapterRecord` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `chapter_key` | `str` | 本地稳定 key，如 `chapter-04***f3` |
| `chapter_id` | `str` | 超星章节 ID |
| `course_key` | `str` | 所属课程 key |
| `title` | `str` | 章节标题 |
| `order` | `str` | 章节序号，如 `1.1` |
| `studentstudy_url` | `str` | 章节学习页 URL |

## `list_videos()`

```python
videos = downloader.list_videos(chapter_key)
```

根据章节 key 返回该章节内的视频任务点。

参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `chapter_key` | `str` | 来自 `ChapterRecord.chapter_key` |

返回：

| 类型 | 说明 |
| --- | --- |
| `list[VideoRecord]` | 视频记录列表 |

返回示例：

```python
[
    VideoRecord(
        video_key="video-6d***00",
        chapter_key="chapter-04***f3",
        title="符***作用",
        object_id="f2c7***9c1a",
        job_id="job-***",
        mid="mid-***",
        duration=681,
        size=438***166,
        media_url="https://.../1.1.mp4",
        download_url="https://.../1.1.mp4",
        filename="1.1.mp4",
    )
]
```

`VideoRecord` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `video_key` | `str` | 本地稳定 key，如 `video-6d***00` |
| `chapter_key` | `str` | 所属章节 key |
| `title` | `str` | 视频标题 |
| `object_id` | `str` | 超星媒体 object ID |
| `job_id` | `str` | 任务点 job ID |
| `mid` | `str` | 媒体 ID |
| `duration` | `int` | 时长，单位秒 |
| `size` | `int` | 文件大小，单位字节 |
| `media_url` | `str` | 媒体播放地址 |
| `download_url` | `str` | 直接下载地址 |
| `filename` | `str` | 原始文件名 |

## `download_video()`

```python
path = downloader.download_video(video_key)
```

下载指定视频，返回本地文件路径。

也可以指定本次下载目录：

```python
path = downloader.download_video(video_key, output_dir="my-downloads")
```

也可以传入进度回调：

```python
def on_progress(downloaded: int, total: int | None) -> None:
    if total:
        print(f"{downloaded / total:.1%}")
    else:
        print(f"{downloaded} bytes")

path = downloader.download_video(video_key, progress=on_progress)
```

参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `video_key` | `str` | 来自 `VideoRecord.video_key` |
| `output_dir` | `str \| pathlib.Path \| None` | 可选；覆盖本次下载目录，不传则使用 `state_dir/downloads/` |
| `progress` | `Callable[[int, int \| None], None] \| None` | 可选；每写入一个下载分块后回调，参数为已下载字节数和总字节数 |

如果服务器没有返回 `Content-Length`，`progress` 的第二个参数 `total` 为 `None`。

返回：

| 类型 | 说明 |
| --- | --- |
| `pathlib.Path` | 已下载文件路径，默认位于 `state_dir/downloads/` |

返回示例：

```python
Path(".chaoxing/downloads/1.1.mp4")
```

实际返回值是 `pathlib.Path` 对象，可以继续用于文件判断、读取或传给其他库：

```python
path.exists()
path.name
path.read_bytes()
```

## 状态目录

默认状态目录为 `.chaoxing/`：

```text
.chaoxing/
  browser/       Playwright persistent browser context
  session.json   登录 Cookie、referer、base_url 等会话信息
  cache.json     课程、章节、视频和课程入口参数缓存
  downloads/     默认下载目录
```

外部项目只需要持有这个目录即可复用登录状态：

```python
downloader = ChaoxingDownloader.init(state_dir="runtime/chaoxing")
downloader = ChaoxingDownloader.load(state_dir="runtime/chaoxing")
```
