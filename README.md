# chaoxing-downloader

学习通课程视频下载工具，支持浏览器登录、课程/章节/视频三级浏览、缓存和批量下载。

依赖：Python 3.11+、httpx、beautifulsoup4、playwright（Chromium）

## 安装

### 方式一：克隆仓库后本地安装

```powershell
git clone https://github.com/alpha03123/chaoxing-downloader.git
cd chaoxing-downloader
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m playwright install chromium
```

### 方式二：直接从 GitHub 安装

```powershell
python -m pip install "git+https://github.com/alpha03123/chaoxing-downloader.git"
python -m playwright install chromium
```

## 登录

```powershell
chaoxing-downloader init
```

会弹出 Chromium，手动登录超星后自动采集 cookie 并写入 `config.toml`。

可选参数：

```
--config config.toml          指定配置文件路径
--user-data-dir .chaoxing-browser  浏览器数据目录
--timeout 300                 等待登录超时秒数
```

## 配置文件

默认读当前目录的 `config.toml`：

```toml
[session]
cookie = "UID=...; vc3=...; uf=...; p_auth_token=..."
referer = "https://mooc1.chaoxing.com/"

[entry]
base_url = "https://i.chaoxing.com/base"

[download]
output_dir = "downloads"

[cache]
path = ".chaoxing-cache.json"
```

## 用法

```powershell
# 列出所有课程
chaoxing-downloader list-courses

# 列出某门课的章节
chaoxing-downloader list-chapters --course course-54600bb5

# 列出某章节的视频
chaoxing-downloader list-videos --chapter chapter-0434a4f3

# 下载视频
chaoxing-downloader download-video --video video-6d0d9300

# 清理缓存
chaoxing-downloader clear-cache
```

所有命令支持 `--config <path>` 指定配置文件。

## 作为 Python 库使用

当前版本已暴露稳定的公开 API：

```python
from chaoxing_downloader import ChaoxingDownloader

downloader = ChaoxingDownloader.from_config("config.toml")

courses = downloader.list_courses()
chapters = downloader.list_chapters(courses[0].course_key)
videos = downloader.list_videos(chapters[0].chapter_key)
path = downloader.download_video(videos[0].video_key)
```

也可以使用便捷函数：

```python
from chaoxing_downloader import load_downloader

downloader = load_downloader("config.toml")
courses = downloader.list_courses()
```

建议外部调用方只依赖：

```python
ChaoxingDownloader
load_downloader
CourseRecord / ChapterRecord / VideoRecord
```

不要直接依赖内部模块实现细节。

## 缓存

解析结果缓存在 `.chaoxing-cache.json`，包括课程/章节/视频的 key、URL、object_id 和下载地址，避免重复请求。

## 课程入口参数

部分课程进入章节时需要额外的课程入口参数，例如 `enc`、`t`、`openc`。当前版本会在 `init` 阶段自动逐门课程预热，并把最终的课程入口 URL 缓存到 `.chaoxing-cache.json`，后续 `list-chapters` 会优先复用这些入口参数。

## 调试

```powershell
chaoxing-downloader inspect-course "https://mooc1.chaoxing.com/mycourse/studentstudy?..." \
  --cookie "UID=...; vc3=..." \
  --referer "https://mooc1.chaoxing.com/"
```

直接解析一个 studentstudy 页面，用于排查页面结构问题。

## 常见问题

**Playwright 未安装**

```powershell
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m playwright install chromium
```
