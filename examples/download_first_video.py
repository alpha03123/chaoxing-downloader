from __future__ import annotations

from pathlib import Path

from chaoxing_downloader import ChaoxingDownloader


STATE_DIR = Path(".chaoxing")
DOWNLOAD_DIR = Path("downloads")


def show_progress(downloaded: int, total: int | None) -> None:
    if total:
        percent = downloaded / total * 100
        print(f"\r[download] {percent:6.2f}% {format_size(downloaded)} / {format_size(total)}", end="", flush=True)
    else:
        print(f"\r[download] {format_size(downloaded)}", end="", flush=True)


def format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}GB"


def main() -> None:
    if not ChaoxingDownloader.is_initialized(state_dir=str(STATE_DIR)):
        print("[init] no local session found, opening browser login")
        downloader = ChaoxingDownloader.init(state_dir=str(STATE_DIR))
    else:
        print("[load] loading local session")
        downloader = ChaoxingDownloader.load(state_dir=str(STATE_DIR))

    courses = downloader.list_courses()
    if not courses:
        raise RuntimeError("No courses found")
    course = courses[0]
    print(f"[course] {course.course_key} {course.title}")

    chapters = downloader.list_chapters(course.course_key)
    if not chapters:
        raise RuntimeError(f"No chapters found for {course.course_key}")
    chapter = chapters[0]
    print(f"[chapter] {chapter.chapter_key} {chapter.order} {chapter.title}")

    videos = downloader.list_videos(chapter.chapter_key)
    if not videos:
        raise RuntimeError(f"No videos found for {chapter.chapter_key}")
    video = videos[0]
    print(f"[video] {video.video_key} {video.title} {video.filename}")

    filename = video.filename or f"{video.video_key}.mp4"
    path = downloader.download_video(video.video_key, output_dir=DOWNLOAD_DIR, filename=filename, progress=show_progress)
    print()
    print(f"[downloaded] {path.resolve()}")


if __name__ == "__main__":
    main()
