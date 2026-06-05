"""Public API for chaoxing-downloader."""

from .api import ChaoxingDownloader, load_downloader
from .models import ChapterRecord, CourseRecord, VideoRecord

__all__ = [
    "ChaoxingDownloader",
    "load_downloader",
    "CourseRecord",
    "ChapterRecord",
    "VideoRecord",
]
