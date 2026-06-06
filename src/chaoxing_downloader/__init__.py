"""Public API for chaoxing-downloader."""

from .api import ChaoxingDownloader
from .auth_init import InitCancelled
from .course_parser import UnsupportedChapterError
from .models import ChapterRecord, CourseRecord, VideoRecord

__all__ = [
    "ChaoxingDownloader",
    "InitCancelled",
    "UnsupportedChapterError",
    "CourseRecord",
    "ChapterRecord",
    "VideoRecord",
]
