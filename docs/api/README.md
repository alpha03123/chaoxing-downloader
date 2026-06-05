# chaoxing-downloader Python API


## 源码边界

```text
src/chaoxing_downloader/
  api.py        公开API：ChaoxingDownloader
  state.py      库模式状态目录：session.json / cache.json / browser/
  auth_init.py  浏览器登录、课程预热、登录 Cookie 采集
  workflow.py   课程/章节/视频/下载业务流程
  *_parser.py   页面解析
```



## API文档

- 完整方法和字段参考见 [API Reference](reference.md)。

## 推荐用法

首次使用：

```python
from chaoxing_downloader import ChaoxingDownloader

downloader = ChaoxingDownloader.init()

courses = downloader.list_courses()
chapters = downloader.list_chapters(courses[0].course_key)
videos = downloader.list_videos(chapters[0].chapter_key)
path = downloader.download_video(videos[0].video_key)
```

再次使用：

```python
from chaoxing_downloader import ChaoxingDownloader

downloader = ChaoxingDownloader.load()
courses = downloader.list_courses()
```

## 状态目录

默认状态目录：

```text
.chaoxing/
```

内部结构：

```text
.chaoxing/
  browser/       Playwright persistent browser context
  session.json   cookie、referer、base_url 等登录会话信息
  cache.json     课程、章节、视频、课程入口参数缓存
  downloads/     默认下载目录
```

调用方也可以指定：

```python
downloader = ChaoxingDownloader.init(state_dir="runtime/chaoxing")
downloader = ChaoxingDownloader.load(state_dir="runtime/chaoxing")
```

## `init()`

```python
downloader = ChaoxingDownloader.init(
    state_dir=".chaoxing",
    timeout_seconds=300,
)
```

行为：

1. 启动有头 Chromium。
2. 用户在浏览器里完成超星登录。
3. API 检测是否进入个人空间课程主页。
4. 自动解析课程列表。
5. 逐门课程进入课程入口，采集最终 `mycourse/stu` 入口参数。
6. 保存浏览器状态、session 和 cache。
7. 返回可直接使用的 `ChaoxingDownloader` 实例。

API当前还是阻塞的
## `load()`

```python
downloader = ChaoxingDownloader.load(state_dir=".chaoxing")
```

行为：

1. 读取 `.chaoxing/session.json`。
2. 使用 `.chaoxing/cache.json` 作为缓存。
3. 构造可用的 `ChaoxingDownloader` 实例。
4. 不会再弹浏览器。



## 查询课程

```python
courses = downloader.list_courses()
```

返回：

```python
list[CourseRecord]
```

`CourseRecord` 主要字段：

```python
course.course_key
course.course_id
course.clazz_id
course.cpi
course.title
course.teacher
course.open_time
```

## 查询章节

```python
chapters = downloader.list_chapters(course_key)
```

返回：

```python
list[ChapterRecord]
```

## 查询视频

```python
videos = downloader.list_videos(chapter_key)
```

返回：

```python
list[VideoRecord]
```

`VideoRecord` 主要字段：

```python
video.video_key
video.chapter_key
video.title
video.object_id
video.duration
video.size
video.filename
video.media_url
video.download_url
```

## 下载视频

```python
path = downloader.download_video(video_key)
```

默认下载到 `state_dir/downloads/`。

可以用 `output_dir` 覆盖本次下载目录：

```python
path = downloader.download_video(video_key, output_dir="my-downloads")
```
