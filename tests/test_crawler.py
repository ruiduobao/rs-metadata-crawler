"""Tests for the crawler module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestValidateBbox:
    """Tests for bounding box validation."""

    def test_valid_bbox(self, crawler_module):
        result = crawler_module.validate_bbox([116.0, 39.0, 117.0, 40.0])
        assert result == (116.0, 39.0, 117.0, 40.0)

    def test_invalid_bbox_wrong_length(self, crawler_module):
        with pytest.raises(ValueError, match="4 values"):
            crawler_module.validate_bbox([116.0, 39.0, 117.0])

    def test_invalid_bbox_west_east(self, crawler_module):
        with pytest.raises(ValueError, match="West must be less"):
            crawler_module.validate_bbox([117.0, 39.0, 116.0, 40.0])

    def test_invalid_bbox_south_north(self, crawler_module):
        with pytest.raises(ValueError, match="South must be less"):
            crawler_module.validate_bbox([116.0, 40.0, 117.0, 39.0])

    def test_invalid_bbox_longitude_range(self, crawler_module):
        with pytest.raises(ValueError, match="Longitude"):
            crawler_module.validate_bbox([200.0, 39.0, 117.0, 40.0])

    def test_invalid_bbox_latitude_range(self, crawler_module):
        with pytest.raises(ValueError, match="Latitude"):
            crawler_module.validate_bbox([116.0, 100.0, 117.0, 40.0])


class TestValidateDate:
    """Tests for date validation."""

    def test_valid_date(self, crawler_module):
        result = crawler_module.validate_date("2024-01-01")
        assert result == "2024-01-01"

    def test_invalid_date_format(self, crawler_module):
        with pytest.raises(ValueError, match="Invalid date format"):
            crawler_module.validate_date("01-01-2024")

    def test_invalid_date_value(self, crawler_module):
        with pytest.raises(ValueError, match="Invalid date format"):
            crawler_module.validate_date("2024-13-01")


class TestPlatformMap:
    """Tests for platform mapping."""

    def test_platform_map_contains_sentinel(self, crawler_module):
        assert "sentinel-2" in crawler_module.PLATFORM_MAP
        assert crawler_module.PLATFORM_MAP["sentinel-2"] == "copernicus"

    def test_platform_map_contains_landsat(self, crawler_module):
        assert "landsat-8" in crawler_module.PLATFORM_MAP
        assert crawler_module.PLATFORM_MAP["sentinel-2"] == "copernicus"

    def test_platform_aliases(self, crawler_module):
        assert crawler_module.PLATFORM_ALIASES["s2"] == "sentinel-2"
        assert crawler_module.PLATFORM_ALIASES["l8"] == "landsat-8"


class TestDeduplication:
    """Tests for scene deduplication."""

    def test_deduplicate_empty(self, crawler_module):
        result = crawler_module.deduplicate_scenes([])
        assert result == []

    def test_deduplicate_no_duplicates(self, crawler_module, sample_scenes):
        result = crawler_module.deduplicate_scenes(sample_scenes)
        assert len(result) == 3

    def test_deduplicate_with_duplicates(self, crawler_module, sample_scenes):
        scenes = sample_scenes + sample_scenes
        result = crawler_module.deduplicate_scenes(scenes)
        assert len(result) == 3

    def test_deduplicate_empty_scene_id(self, crawler_module):
        scenes = [
            {"scene_id": "", "source": "test"},
            {"scene_id": "test1", "source": "test"},
        ]
        result = crawler_module.deduplicate_scenes(scenes)
        assert len(result) == 1


class TestStatistics:
    """Tests for statistics computation."""

    def test_stats_empty(self, crawler_module):
        stats = crawler_module.compute_statistics([])
        assert stats["total_scenes"] == 0
        assert stats["date_range"]["start"] is None

    def test_stats_with_scenes(self, crawler_module, sample_scenes):
        stats = crawler_module.compute_statistics(sample_scenes)
        assert stats["total_scenes"] == 3
        assert stats["date_range"]["start"] == "2024-01-01"
        assert stats["date_range"]["end"] == "2024-01-15"
        assert stats["cloud_cover"]["min"] == 5.2
        assert stats["cloud_cover"]["max"] == 15.5

    def test_stats_sources(self, crawler_module, sample_scenes):
        stats = crawler_module.compute_statistics(sample_scenes)
        assert stats["sources"]["copernicus"] == 1
        assert stats["sources"]["usgs"] == 1
        assert stats["sources"]["planetary_computer"] == 1

    def test_stats_platforms(self, crawler_module, sample_scenes):
        stats = crawler_module.compute_statistics(sample_scenes)
        assert stats["platforms"]["sentinel-2"] == 2
        assert stats["platforms"]["landsat-8"] == 1


class TestCopernicusCrawler:
    """Tests for Copernicus crawler."""

    def test_parse_entry(self, crawler_module):
        entry = {
            "id": "S2A_MSIL2A_20240101T000000_N0000_R000_T50TML_20240101T000000",
            "title": "S2A_MSIL2A_20240101T000000_N0000_R000_T50TML_20240101T000000",
            "date": [
                {"@name": "beginposition", "#text": "2024-01-01T00:00:00.000Z"},
                {"@name": "ingestiondate", "#text": "2024-01-02T00:00:00.000Z"},
            ],
            "double": [
                {"@name": "cloudcoverpercentage", "#text": "15.5"},
            ],
            "str": [
                {"@name": "footprint", "#text": "POLYGON((116 39,117 39,117 40,116 40,116 39))"},
                {"@name": "size", "#text": "800 MB"},
            ],
        }
        crawler = crawler_module.CopernicusCrawler(crawler_module.create_session())
        result = crawler._parse_entry(entry, "sentinel-2")
        assert result is not None
        assert result["scene_id"] == "S2A_MSIL2A_20240101T000000_N0000_R000_T50TML_20240101T000000"
        assert result["platform"] == "sentinel-2"
        assert result["cloud_cover"] == 15.5

    def test_parse_entry_empty(self, crawler_module):
        crawler = crawler_module.CopernicusCrawler(crawler_module.create_session())
        result = crawler._parse_entry({}, "sentinel-2")
        assert result is not None
        assert result["scene_id"] == ""


class TestUSGSCrawler:
    """Tests for USGS crawler."""

    def test_parse_scene(self, crawler_module):
        scene = {
            "entityId": "LC08_L2SP_123032_20240101_20240115_02_T1",
            "displayId": "LC08_L2SP_123032_20240101_20240115_02_T1",
            "temporalCoverageStartDate": "2024-01-01T00:00:00.000Z",
            "cloudCover": 10.5,
            "sceneBounds": "POLYGON((116 39,117 39,117 40,116 40,116 39))",
            "path": 123,
            "row": 32,
            "processingLevel": "L2SP",
        }
        crawler = crawler_module.USGSCrawler(crawler_module.create_session())
        result = crawler._parse_scene(scene, "landsat-8")
        assert result is not None
        assert result["scene_id"] == "LC08_L2SP_123032_20240101_20240115_02_T1"
        assert result["platform"] == "landsat-8"
        assert result["cloud_cover"] == 10.5

    def test_parse_scene_empty(self, crawler_module):
        crawler = crawler_module.USGSCrawler(crawler_module.create_session())
        result = crawler._parse_scene({}, "landsat-8")
        assert result is not None
        assert result["scene_id"] == ""


class TestPlanetaryComputerCrawler:
    """Tests for Planetary Computer crawler."""

    def test_parse_feature(self, crawler_module):
        feature = {
            "id": "S2A_MSIL2A_20240101T000000_N0000_R000_T50TML_20240101T000000",
            "properties": {
                "datetime": "2024-01-01T00:00:00Z",
                "eo:cloud_cover": 15.5,
                "platform": "sentinel-2a",
                "instruments": ["msi"],
                "processing:level": "L2A",
                "gsd": 10,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[116, 39], [117, 39], [117, 40], [116, 40], [116, 39]]],
            },
            "collection": "sentinel-2-l2a",
        }
        crawler = crawler_module.PlanetaryComputerCrawler(crawler_module.create_session())
        result = crawler._parse_feature(feature, "sentinel-2")
        assert result is not None
        assert result["scene_id"] == "S2A_MSIL2A_20240101T000000_N0000_R000_T50TML_20240101T000000"
        assert result["platform"] == "sentinel-2"
        assert result["cloud_cover"] == 15.5

    def test_parse_feature_empty(self, crawler_module):
        crawler = crawler_module.PlanetaryComputerCrawler(crawler_module.create_session())
        result = crawler._parse_feature({"properties": {}, "geometry": {}}, "sentinel-2")
        assert result is not None
        assert result["scene_id"] == ""


class TestExportResults:
    """Tests for result export."""

    def test_export_json(self, crawler_module, sample_scenes, tmp_path):
        output_path = str(tmp_path / "test_output.json")
        crawler_module.export_results(sample_scenes, output_path, "json")
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 3

    def test_export_csv(self, crawler_module, sample_scenes, tmp_path):
        output_path = str(tmp_path / "test_output.csv")
        crawler_module.export_results(sample_scenes, output_path, "csv")
        assert Path(output_path).exists()

    def test_export_empty_csv(self, crawler_module, tmp_path):
        output_path = str(tmp_path / "empty.csv")
        crawler_module.export_results([], output_path, "csv")
        assert Path(output_path).exists()


class TestCache:
    """Tests for caching functionality."""

    def test_cache_key_generation(self, crawler_module):
        key1 = crawler_module.get_cache_key("copernicus", {"bbox": [116, 39, 117, 40]})
        key2 = crawler_module.get_cache_key("copernicus", {"bbox": [116, 39, 117, 40]})
        assert key1 == key2

    def test_cache_key_different_params(self, crawler_module):
        key1 = crawler_module.get_cache_key("copernicus", {"bbox": [116, 39, 117, 40]})
        key2 = crawler_module.get_cache_key("usgs", {"bbox": [116, 39, 117, 40]})
        assert key1 != key2

    def test_save_and_get_cache(self, crawler_module, sample_scenes, tmp_path):
        cache_dir = str(tmp_path / "cache")
        cache_key = "test_key"
        crawler_module.save_cached_result(cache_dir, cache_key, sample_scenes, ttl=3600)
        result = crawler_module.get_cached_result(cache_dir, cache_key)
        assert result is not None
        assert len(result) == 3

    def test_get_cache_miss(self, crawler_module, tmp_path):
        cache_dir = str(tmp_path / "cache")
        result = crawler_module.get_cached_result(cache_dir, "nonexistent_key")
        assert result is None

    def test_get_cache_expired(self, crawler_module, sample_scenes, tmp_path):
        cache_dir = str(tmp_path / "cache")
        cache_key = "expired_key"
        crawler_module.save_cached_result(cache_dir, cache_key, sample_scenes, ttl=0)
        result = crawler_module.get_cached_result(cache_dir, cache_key)
        assert result is None
