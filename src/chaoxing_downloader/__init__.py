"""Public API for chaoxing-downloader."""

from .api import ChaoxingDownloader
from .auth_init import InitCancelled
from .models import ChapterRecord, CourseRecord, VideoRecord

__all__ = [
    "ChaoxingDownloader",
    "InitCancelled",
    "CourseRecord",
    "ChapterRecord",
    "VideoRecord",
]
