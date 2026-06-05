from pathlib import Path

from chaoxing_downloader.config import ConfigError, load_config


def test_load_config_reads_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[session]
cookie = "a=b"
referer = "https://mooc1.chaoxing.com/"

[entry]
base_url = "https://i.chaoxing.com/base?ws=1"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(str(config_path))

    assert config.cookie == "a=b"
    assert config.referer == "https://mooc1.chaoxing.com/"
    assert config.base_url == "https://i.chaoxing.com/base?ws=1"
    assert config.output_dir == "downloads"
    assert config.cache_path == ".chaoxing-cache.json"


def test_load_config_requires_cookie(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[session]
referer = "https://mooc1.chaoxing.com/"
""".strip(),
        encoding="utf-8",
    )

    try:
        load_config(str(config_path))
    except ConfigError as exc:
        assert "session.cookie" in str(exc)
    else:
        raise AssertionError("expected ConfigError")
