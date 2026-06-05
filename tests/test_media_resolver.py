from chaoxing_downloader.media_resolver import resolve_media_url


def test_resolve_media_url_prefers_m3u8() -> None:
    html = """
    <html>
      <script>
        window.__DATA__ = {"video":"https://cdn.example.com/a.m3u8"};
      </script>
    </html>
    """
    assert resolve_media_url(html) == "https://cdn.example.com/a.m3u8"
