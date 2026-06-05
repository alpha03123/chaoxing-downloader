from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class TaskPoint:
    title: str
    kind: str
    status: str
    media_url: str = ""
    object_id: str = ""
    job_id: str = ""
    mid: str = ""


@dataclass(frozen=True)
class Chapter:
    title: str
    tasks: list[TaskPoint] = field(default_factory=list)


@dataclass(frozen=True)
class CoursePage:
    title: str
    chapters: list[Chapter] = field(default_factory=list)


@dataclass(frozen=True)
class AppConfig:
    cookie: str
    referer: str
    base_url: str = ""
    output_dir: str = "downloads"
    cache_path: str = ".chaoxing-cache.json"


@dataclass(frozen=True)
class CourseRecord:
    course_key: str
    course_id: str
    clazz_id: str
    cpi: str
    enc: str
    title: str
    teacher: str
    open_time: str
    course_url: str
    course_study_url: str = ""


@dataclass(frozen=True)
class ChapterRecord:
    chapter_key: str
    chapter_id: str
    course_key: str
    title: str
    order: str
    studentstudy_url: str


@dataclass(frozen=True)
class VideoRecord:
    video_key: str
    chapter_key: str
    title: str
    object_id: str
    job_id: str
    mid: str
    duration: int = 0
    size: int = 0
    media_url: str = ""
    download_url: str = ""
    filename: str = ""


@dataclass(frozen=True)
class CacheState:
    courses: list[CourseRecord] = field(default_factory=list)
    chapters: list[ChapterRecord] = field(default_factory=list)
    videos: list[VideoRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "courses": [asdict(item) for item in self.courses],
            "chapters": [asdict(item) for item in self.chapters],
            "videos": [asdict(item) for item in self.videos],
        }
