"""Integration tests for RS Metadata Crawler."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestCopernicusIntegration:
    """Integration tests for Copernicus crawler."""

    @patch("rs_metadata_crawler.requests.Session.get")
    def test_copernicus_search_mock(self, mock_get, crawler_module, copernicus_response):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = copernicus_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        crawler = crawler_module.CopernicusCrawler(crawler_module.create_session())
        results = crawler.search(
            bbox=(116.0, 39.0, 117.0, 40.0),
            start_date="2024-01-01",
            end_date="2024-12-31",
            platform="sentinel-2",
            max_cloud=20,
            limit=10,
        )

        assert len(results) == 2
        assert results[0]["source"] == "copernicus"
        assert results[0]["platform"] == "sentinel-2"
        assert results[0]["cloud_cover"] == 15.5

    @patch("rs_metadata_crawler.requests.Session.get")
    def test_copernicus_search_pagination(self, mock_get, crawler_module):
        page1 = {
            "feed": {
                "entry": [
                    {
                        "id": f"S2A_{i}",
                        "title": f"S2A_{i}",
                        "date": [{"@name": "beginposition", "#text": "2024-01-01T00:00:00Z"}],
                        "double": [{"@name": "cloudcoverpercentage", "#text": "10"}],
                        "str": [{"@name": "footprint", "#text": "POLYGON((0 0,1 0,1 1,0 1,0 0))"}],
                    }
                    for i in range(100)
                ]
            }
        }
        page2 = {"feed": {"entry": []}}

        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = page1
        mock_response1.raise_for_status = MagicMock()

        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = page2
        mock_response2.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_response1, mock_response2]

        crawler = crawler_module.CopernicusCrawler(crawler_module.create_session())
        results = crawler.search(
            bbox=(0.0, 0.0, 1.0, 1.0),
            start_date="2024-01-01",
            end_date="2024-12-31",
            platform="sentinel-2",
            limit=150,
        )

        assert len(results) == 100

    @patch("rs_metadata_crawler.requests.Session.get")
    def test_copernicus_search_error(self, mock_get, crawler_module):
        import requests
        mock_get.side_effect = requests.RequestException("Connection error")

        crawler = crawler_module.CopernicusCrawler(crawler_module.create_session())
        results = crawler.search(
            bbox=(116.0, 39.0, 117.0, 40.0),
            start_date="2024-01-01",
            end_date="2024-12-31",
            platform="sentinel-2",
        )

        assert results == []


class TestUSGSIntegration:
    """Integration tests for USGS crawler."""

    @patch("rs_metadata_crawler.requests.Session.post")
    def test_usgs_search_mock(self, mock_post, crawler_module, usgs_response):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = usgs_response
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        crawler = crawler_module.USGSCrawler(crawler_module.create_session())
        results = crawler.search(
            bbox=(116.0, 39.0, 117.0, 40.0),
            start_date="2024-01-01",
            end_date="2024-12-31",
            platform="landsat-8",
            max_cloud=30,
            limit=10,
        )

        assert len(results) == 2
        assert results[0]["source"] == "usgs"
        assert results[0]["platform"] == "landsat-8"
        assert results[0]["cloud_cover"] == 10.5

    @patch("rs_metadata_crawler.requests.Session.post")
    def test_usgs_search_error(self, mock_post, crawler_module):
        import requests
        mock_post.side_effect = requests.RequestException("Connection error")

        crawler = crawler_module.USGSCrawler(crawler_module.create_session())
        results = crawler.search(
            bbox=(116.0, 39.0, 117.0, 40.0),
            start_date="2024-01-01",
            end_date="2024-12-31",
            platform="landsat-8",
        )

        assert results == []


class TestPlanetaryComputerIntegration:
    """Integration tests for Planetary Computer crawler."""

    @patch("rs_metadata_crawler.requests.Session.post")
    def test_planetary_search_mock(self, mock_post, crawler_module, planetary_response):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = planetary_response
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        crawler = crawler_module.PlanetaryComputerCrawler(crawler_module.create_session())
        results = crawler.search(
            bbox=(116.0, 39.0, 117.0, 40.0),
            start_date="2024-01-01",
            end_date="2024-12-31",
            platform="sentinel-2",
            max_cloud=20,
            limit=10,
        )

        assert len(results) == 2
        assert results[0]["source"] == "planetary_computer"
        assert results[0]["platform"] == "sentinel-2"
        assert results[0]["cloud_cover"] == 15.5

    @patch("rs_metadata_crawler.requests.Session.post")
    def test_planetary_search_with_pagination(self, mock_post, crawler_module):
        page1 = {
            "features": [
                {
                    "id": f"S2A_{i}",
                    "properties": {
                        "datetime": "2024-01-01T00:00:00Z",
                        "eo:cloud_cover": 10.0,
                        "platform": "sentinel-2a",
                        "instruments": ["msi"],
                        "processing:level": "L2A",
                        "gsd": 10,
                    },
                    "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                    "collection": "sentinel-2-l2a",
                }
                for i in range(10)
            ],
            "links": [{"rel": "next", "href": "https://example.com/next"}],
        }
        page2 = {
            "features": [
                {
                    "id": "S2A_extra",
                    "properties": {
                        "datetime": "2024-01-02T00:00:00Z",
                        "eo:cloud_cover": 5.0,
                        "platform": "sentinel-2a",
                        "instruments": ["msi"],
                        "processing:level": "L2A",
                        "gsd": 10,
                    },
                    "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                    "collection": "sentinel-2-l2a",
                }
            ],
            "links": [],
        }

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = page1
        mock_post_response.raise_for_status = MagicMock()

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = page2
        mock_get_response.raise_for_status = MagicMock()

        mock_post.side_effect = [mock_post_response]
        with patch("rs_metadata_crawler.requests.Session.get", return_value=mock_get_response):
            crawler = crawler_module.PlanetaryComputerCrawler(crawler_module.create_session())
            results = crawler.search(
                bbox=(0.0, 0.0, 1.0, 1.0),
                start_date="2024-01-01",
                end_date="2024-12-31",
                platform="sentinel-2",
                limit=50,
            )

        assert len(results) == 11

    @patch("rs_metadata_crawler.requests.Session.post")
    def test_planetary_search_error(self, mock_post, crawler_module):
        import requests
        mock_post.side_effect = requests.RequestException("Connection error")

        crawler = crawler_module.PlanetaryComputerCrawler(crawler_module.create_session())
        results = crawler.search(
            bbox=(116.0, 39.0, 117.0, 40.0),
            start_date="2024-01-01",
            end_date="2024-12-31",
            platform="sentinel-2",
        )

        assert results == []


class TestFullWorkflow:
    """Integration tests for full workflow."""

    @patch("rs_metadata_crawler._do_search")
    def test_search_stats_merge_workflow(self, mock_search, crawler_module, sample_scenes, tmp_path):
        mock_search.return_value = sample_scenes

        output1 = str(tmp_path / "search1.json")
        output2 = str(tmp_path / "search2.json")
        merged = str(tmp_path / "merged.json")

        crawler_module.main([
            "search",
            "--bbox", "116", "39", "117", "40",
            "--start-date", "2024-01-01",
            "--end-date", "2024-06-30",
            "--output", output1,
        ])

        crawler_module.main([
            "search",
            "--bbox", "116", "39", "117", "40",
            "--start-date", "2024-07-01",
            "--end-date", "2024-12-31",
            "--output", output2,
        ])

        result = crawler_module.main([
            "merge",
            "--inputs", output1, output2,
            "--output", merged,
        ])
        assert result == 0
        assert Path(merged).exists()

        result = crawler_module.main(["stats", "--input", merged])
        assert result == 0

    @patch("rs_metadata_crawler._do_search")
    def test_search_with_cache(self, mock_search, crawler_module, sample_scenes, tmp_path):
        mock_search.return_value = sample_scenes
        cache_dir = str(tmp_path / "cache")
        output = str(tmp_path / "cached_output.json")

        crawler_module.main([
            "search",
            "--bbox", "116", "39", "117", "40",
            "--start-date", "2024-01-01",
            "--end-date", "2024-12-31",
            "--cache-dir", cache_dir,
            "--output", output,
        ])

        assert mock_search.call_count == 1

        output2 = str(tmp_path / "cached_output2.json")
        crawler_module.main([
            "search",
            "--bbox", "116", "39", "117", "40",
            "--start-date", "2024-01-01",
            "--end-date", "2024-12-31",
            "--cache-dir", cache_dir,
            "--output", output2,
        ])

        assert mock_search.call_count == 1

    @patch("rs_metadata_crawler._do_search")
    def test_full_workflow_landsat(self, mock_search, crawler_module, sample_scenes, tmp_path):
        landsat_scenes = [s for s in sample_scenes if s["platform"] == "landsat-8"]
        mock_search.return_value = landsat_scenes

        output = str(tmp_path / "landsat_results.json")
        result = crawler_module.main([
            "search",
            "--bbox", "116", "39", "117", "40",
            "--start-date", "2024-01-01",
            "--end-date", "2024-12-31",
            "--platform", "landsat-8",
            "--source", "usgs",
            "--output", output,
        ])
        assert result == 0

        result = crawler_module.main(["stats", "--input", output])
        assert result == 0
