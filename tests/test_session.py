from chaoxing_downloader.session import SessionConfig, build_headers


def test_build_headers_includes_cookie_and_referer() -> None:
    config = SessionConfig(
        cookie="foo=bar",
        user_agent="UA",
        referer="https://mooc1.chaoxing.com/",
    )
    headers = build_headers(config)
    assert headers["Cookie"] == "foo=bar"
    assert headers["User-Agent"] == "UA"
    assert headers["Referer"] == "https://mooc1.chaoxing.com/"
