# chaoxing-downloader

学习通课程视频下载工具，支持浏览器登录、课程/章节/视频三级浏览

依赖：Python 3.11+、httpx、beautifulsoup4、playwright（Chromium）

Python 库使用，见 [Python API 文档](docs/api/README.md)。
## 安装

```powershell
pip install chaoxing-downloader
```

## 登录

```powershell
chaoxing-downloader init
```

会弹出浏览器，手动登录超星后自动：
- 采集 `.chaoxing.com` cookie 并写入 `config.toml`
- 写入课程列表和课程入口参数到 `.chaoxing-cache.json`

可选参数：

```
--config config.toml            配置文件写入路径（默认 config.toml）
--user-data-dir .chaoxing-browser   浏览器数据目录
--timeout 300                   等待登录超时秒数
--course-delay 2.0              预热课程入口时，每门课程进入前等待秒数
```

## 配置文件

默认读当前目录的 `config.toml`，由 `init` 自动生成，通常不需要手动编辑：

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

课程/章节/视频查询和下载命令支持 `--delay <seconds>`，用于降低请求频率：

```powershell
chaoxing-downloader list-courses --delay 1.5
chaoxing-downloader list-chapters --course course-54600bb5 --delay 1.5
chaoxing-downloader list-videos --chapter chapter-0434a4f3 --delay 1.5
chaoxing-downloader download-video --video video-6d0d9300 --delay 1.5
```

所有命令支持 `--config <path>` 指定配置文件。

## Python 示例

仓库内提供了一个最小示例脚本，会自动判断是否已初始化、列出第一个课程/章节/视频并下载：

```powershell
python examples/download_first_video.py
```


## 缓存

解析结果缓存在 `.chaoxing-cache.json`（路径由 `[cache].path` 控制），包括课程/章节/视频的 key、URL、object_id 和下载地址。

## 课程入口参数

部分课程进入章节时需要从课程入口页拿到 `enc`、`t` 等参数。`init` 会在登录后自动预热课程并缓存最终课程入口 URL，正常情况下不需要手动处理。

## 常见问题

**Playwright 未安装**

```powershell
.\.venv\Scripts\python -m pip install playwright
.\.venv\Scripts\python -m playwright install chromium
```

**中文乱码**

```powershell
$env:PYTHONIOENCODING='utf-8'
```

**未安装为命令**

```powershell
$env:PYTHONPATH='.\src'
python -m chaoxing_downloader list-courses
```
## 许可证

本项目基于 [MIT License](LICENSE) 开源。

## 免责声明

本项目仅用于用户本人已授权课程的视频离线学习和技术研究，不提供任何课程资源，不支持免登录、绕过权限、绕过付费、破解加密或 DRM。

使用者应遵守所在学校、平台服务协议和相关法律法规。通过本工具下载的内容仅限个人学习使用，不得传播、转售、公开分享或用于任何商业用途。因使用本项目产生的账号风险、版权纠纷或其他后果由使用者自行承担。

本项目不会上传、收集或共享用户 Cookie、课程信息和下载内容。
