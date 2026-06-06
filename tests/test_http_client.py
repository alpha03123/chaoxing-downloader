import httpx

from chaoxing_downloader.http_client import ChaoxingClient
from chaoxing_downloader.session import SessionConfig


def test_get_text_follows_redirects() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(302, headers={"Location": "https://example.test/final"})
        return httpx.Response(200, text="ok")

    client = ChaoxingClient(
        SessionConfig(cookie="UID=1"),
        transport=httpx.MockTransport(handler),
    )

    assert client.get_text("https://example.test/start") == "ok"


def test_iter_bytes_yields_chunks_and_total() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"abcdef", headers={"Content-Length": "6"})

    client = ChaoxingClient(
        SessionConfig(cookie="UID=1"),
        transport=httpx.MockTransport(handler),
    )

    assert list(client.iter_bytes("https://example.test/file", chunk_size=2)) == [
        (b"ab", 6),
        (b"cd", 6),
        (b"ef", 6),
    ]


def test_request_delay_runs_before_request() -> None:
    events: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        events.append("request")
        return httpx.Response(200, text="ok")

    client = ChaoxingClient(
        SessionConfig(cookie="UID=1"),
        transport=httpx.MockTransport(handler),
        request_delay=1.5,
        sleeper=lambda seconds: events.append(f"sleep:{seconds}"),
    )

    assert client.get_text("https://example.test/start") == "ok"
    assert events == ["sleep:1.5", "request"]


def test_iter_bytes_delays_once_before_stream_request() -> None:
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"abcdef", headers={"Content-Length": "6"})

    client = ChaoxingClient(
        SessionConfig(cookie="UID=1"),
        transport=httpx.MockTransport(handler),
        request_delay=2.0,
        sleeper=sleeps.append,
    )

    assert list(client.iter_bytes("https://example.test/file", chunk_size=2)) == [
        (b"ab", 6),
        (b"cd", 6),
        (b"ef", 6),
    ]
    assert sleeps == [2.0]


def test_request_delay_rejects_negative_value() -> None:
    try:
        ChaoxingClient(SessionConfig(cookie="UID=1"), request_delay=-0.1)
    except ValueError as exc:
        assert "request_delay" in str(exc)
        return

    raise AssertionError("expected ValueError")
