"""Security-related tests for RS Metadata Crawler."""

import os
from pathlib import Path

import pytest


class TestUserAgent:
    """Tests for User-Agent header."""

    def test_user_agent_format(self, crawler_module):
        assert "rs-metadata-crawler" in crawler_module.USER_AGENT
        assert crawler_module.__version__ in crawler_module.USER_AGENT

    def test_session_has_user_agent(self, crawler_module):
        session = crawler_module.create_session()
        assert "rs-metadata-crawler" in session.headers.get("User-Agent", "")

    def test_session_no_proxy(self, crawler_module):
        session = crawler_module.create_session()
        assert session.trust_env is False


class TestTrustEnv:
    """Tests for trust_env setting."""

    def test_session_trust_env_false(self, crawler_module):
        session = crawler_module.create_session()
        assert session.trust_env is False


class TestInputValidation:
    """Tests for input validation."""

    def test_validate_bbox_rejects_invalid_lon(self, crawler_module):
        with pytest.raises(ValueError, match="Longitude"):
            crawler_module.validate_bbox([200.0, 39.0, 117.0, 40.0])

    def test_validate_bbox_rejects_invalid_lat(self, crawler_module):
        with pytest.raises(ValueError, match="Latitude"):
            crawler_module.validate_bbox([116.0, 100.0, 117.0, 40.0])

    def test_validate_date_rejects_bad_format(self, crawler_module):
        with pytest.raises(ValueError, match="Invalid date"):
            crawler_module.validate_date("2024/01/01")

    def test_validate_date_rejects_invalid_month(self, crawler_module):
        with pytest.raises(ValueError, match="Invalid date"):
            crawler_module.validate_date("2024-13-01")


class TestCacheSecurity:
    """Tests for cache security."""

    def test_cache_dir_created_safely(self, crawler_module, tmp_path):
        cache_dir = str(tmp_path / "safe_cache")
        key = crawler_module.get_cache_key("test", {"param": "value"})
        crawler_module.save_cached_result(cache_dir, key, [{"test": True}])
        assert Path(cache_dir).exists()

    def test_cache_path_no_traversal(self, crawler_module, tmp_path):
        cache_dir = str(tmp_path / "cache")
        key = "test_key"
        crawler_module.save_cached_result(cache_dir, key, [{"test": True}])
        cache_path = Path(cache_dir) / f"{key}.json"
        assert ".." not in str(cache_path)
        assert cache_path.parent == Path(cache_dir)


class TestPlatformValidation:
    """Tests for platform validation."""

    def test_valid_platforms(self, crawler_module):
        valid_platforms = ["sentinel-1", "sentinel-2", "sentinel-3", "sentinel-5p",
                          "landsat-5", "landsat-7", "landsat-8", "landsat-9"]
        for p in valid_platforms:
            assert p in crawler_module.PLATFORM_MAP

    def test_platform_aliases(self, crawler_module):
        aliases = {"s1": "sentinel-1", "s2": "sentinel-2", "s3": "sentinel-3",
                   "s5p": "sentinel-5p", "l5": "landsat-5", "l7": "landsat-7",
                   "l8": "landsat-8", "l9": "landsat-9"}
        for alias, expected in aliases.items():
            assert crawler_module.PLATFORM_ALIASES[alias] == expected
