"""Test configuration and fixtures for RS Metadata Crawler."""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

# Load rs-metadata-crawler.py as a module
CRAWLER_PATH = Path(__file__).parent.parent / "rs-metadata-crawler.py"
spec = importlib.util.spec_from_file_location("rs_metadata_crawler", CRAWLER_PATH)
rs_metadata_crawler = importlib.util.module_from_spec(spec)
sys.modules["rs_metadata_crawler"] = rs_metadata_crawler
spec.loader.exec_module(rs_metadata_crawler)


@pytest.fixture
def crawler_module():
    """Provide the crawler module."""
    return rs_metadata_crawler


@pytest.fixture
def sample_bbox():
    """Provide a sample bounding box."""
    return [116.0, 39.0, 117.0, 40.0]


@pytest.fixture
def sample_dates():
    """Provide sample date range."""
    return "2024-01-01", "2024-12-31"


@pytest.fixture
def copernicus_response():
    """Provide a mock Copernicus API response."""
    return {
        "feed": {
            "entry": [
                {
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
                },
                {
                    "id": "S2A_MSIL2A_20240115T000000_N0000_R000_T50TML_20240115T000000",
                    "title": "S2A_MSIL2A_20240115T000000_N0000_R000_T50TML_20240115T000000",
                    "date": [
                        {"@name": "beginposition", "#text": "2024-01-15T00:00:00.000Z"},
                        {"@name": "ingestiondate", "#text": "2024-01-16T00:00:00.000Z"},
                    ],
                    "double": [
                        {"@name": "cloudcoverpercentage", "#text": "5.2"},
                    ],
                    "str": [
                        {"@name": "footprint", "#text": "POLYGON((116 39,117 39,117 40,116 40,116 39))"},
                        {"@name": "size", "#text": "750 MB"},
                    ],
                },
            ]
        }
    }


@pytest.fixture
def usgs_response():
    """Provide a mock USGS API response."""
    return {
        "data": {
            "results": [
                {
                    "entityId": "LC08_L2SP_123032_20240101_20240115_02_T1",
                    "displayId": "LC08_L2SP_123032_20240101_20240115_02_T1",
                    "temporalCoverageStartDate": "2024-01-01T00:00:00.000Z",
                    "cloudCover": 10.5,
                    "sceneBounds": "POLYGON((116 39,117 39,117 40,116 40,116 39))",
                    "path": 123,
                    "row": 32,
                    "processingLevel": "L2SP",
                },
                {
                    "entityId": "LC08_L2SP_123032_20240115_20240130_02_T1",
                    "displayId": "LC08_L2SP_123032_20240115_20240130_02_T1",
                    "temporalCoverageStartDate": "2024-01-15T00:00:00.000Z",
                    "cloudCover": 25.3,
                    "sceneBounds": "POLYGON((116 39,117 39,117 40,116 40,116 39))",
                    "path": 123,
                    "row": 32,
                    "processingLevel": "L2SP",
                },
            ]
        }
    }


@pytest.fixture
def planetary_response():
    """Provide a mock Planetary Computer API response."""
    return {
        "features": [
            {
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
            },
            {
                "id": "S2A_MSIL2A_20240115T000000_N0000_R000_T50TML_20240115T000000",
                "properties": {
                    "datetime": "2024-01-15T00:00:00Z",
                    "eo:cloud_cover": 5.2,
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
            },
        ],
        "links": [],
    }


@pytest.fixture
def sample_scenes():
    """Provide sample scenes for testing."""
    return [
        {
            "scene_id": "S2A_MSIL2A_20240101T000000_N0000_R000_T50TML_20240101T000000",
            "source": "copernicus",
            "platform": "sentinel-2",
            "title": "S2A_MSIL2A_20240101T000000",
            "date": "2024-01-01",
            "cloud_cover": 15.5,
            "footprint": "POLYGON((116 39,117 39,117 40,116 40,116 39))",
            "metadata": {"size": "800 MB"},
        },
        {
            "scene_id": "LC08_L2SP_123032_20240101_20240115_02_T1",
            "source": "usgs",
            "platform": "landsat-8",
            "title": "LC08_L2SP_123032_20240101_20240115_02_T1",
            "date": "2024-01-01",
            "cloud_cover": 10.5,
            "footprint": "POLYGON((116 39,117 39,117 40,116 40,116 39))",
            "metadata": {"path": 123, "row": 32},
        },
        {
            "scene_id": "S2A_MSIL2A_20240115T000000_N0000_R000_T50TML_20240115T000000",
            "source": "planetary_computer",
            "platform": "sentinel-2",
            "title": "S2A_MSIL2A_20240115T000000",
            "date": "2024-01-15",
            "cloud_cover": 5.2,
            "footprint": '{"type": "Polygon", "coordinates": [[[116, 39], [117, 39], [117, 40], [116, 40], [116, 39]]]}',
            "metadata": {"collection": "sentinel-2-l2a"},
        },
    ]
