"""Public API for chaoxing-downloader."""

from .api import ChaoxingDownloader
from .models import ChapterRecord, CourseRecord, VideoRecord

__all__ = [
    "ChaoxingDownloader",
    "CourseRecord",
    "ChapterRecord",
    "VideoRecord",
]
