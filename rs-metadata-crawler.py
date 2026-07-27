#!/usr/bin/env python3
"""
RS Metadata Crawler - Crawl satellite imagery metadata from multiple sources.

Crawls METADATA ONLY (scene IDs, dates, cloud cover, path/row, footprint)
from Copernicus Open Access Hub, USGS EarthExplorer, and Microsoft Planetary Computer.
Does NOT download actual satellite images.

Privacy: This tool only queries public metadata APIs. No personal data is collected.
User-Agent: rs-metadata-crawler/0.1.0 (https://github.com/rui.duobao/rs-metadata-crawler)
"""

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)

# Local place-resolver (batch3 v0.2.0+)
try:
    from place_resolver import (
        resolve_place,
        get_preset,
        list_presets,
        format_bbox,
        PlaceNotFoundError,
        PRESETS,
    )
except ImportError as _exc:
    print(
        f"Warning: place_resolver.py not found ({_exc}). --place/--preset disabled.",
        file=sys.stderr,
    )
    PRESETS = {}

    def resolve_place(*args, **kwargs):
        raise RuntimeError("place_resolver.py missing")

    def get_preset(name):
        raise ValueError(f"Unknown preset: {name}")

    def list_presets():
        return "(place_resolver.py missing)"

    def format_bbox(b):
        return f"{b[0]} {b[1]} {b[2]} {b[3]}"

    class PlaceNotFoundError(ValueError):
        pass

__version__ = "0.2.0"
__author__ = "rui.duobao"

USER_AGENT = f"rs-metadata-crawler/{__version__} (https://github.com/rui.duobao/rs-metadata-crawler)"


def write_qa_summary(qa_path: str, args, scenes, stats) -> None:
    """Write a JSON run-summary sidecar to qa_path (Phase 5 optimization).

    Records the bbox / place / preset, the date range, the source, and the
    scene counts (total / sources / date range / mean cloud cover) so each
    metadata crawl is auditable.
    """
    summary = {
        "skill": "rs-metadata-crawler",
        "command": "search",
        "version": __version__,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "bbox": list(args.bbox) if getattr(args, "bbox", None) else None,
        "place": getattr(args, "place", None),
        "preset": getattr(args, "preset", None),
        "start_date": getattr(args, "start_date", None),
        "end_date": getattr(args, "end_date", None),
        "platform": getattr(args, "platform", None),
        "source": getattr(args, "source", None),
        "max_cloud": getattr(args, "max_cloud", None),
        "limit": getattr(args, "limit", None),
        "cache_dir": getattr(args, "cache_dir", None),
        "output": getattr(args, "output", None),
        "format": getattr(args, "format", None),
        "n_scenes": len(scenes) if scenes is not None else 0,
        "stats": stats,
    }
    parent = os.path.dirname(os.path.abspath(qa_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(qa_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

PLATFORM_MAP = {
    "sentinel-1": "copernicus",
    "sentinel-2": "copernicus",
    "sentinel-3": "copernicus",
    "sentinel-5p": "copernicus",
    "landsat-5": "usgs",
    "landsat-7": "usgs",
    "landsat-8": "usgs",
    "landsat-9": "usgs",
}

PLATFORM_ALIASES = {
    "s1": "sentinel-1",
    "s2": "sentinel-2",
    "s3": "sentinel-3",
    "s5p": "sentinel-5p",
    "l5": "landsat-5",
    "l7": "landsat-7",
    "l8": "landsat-8",
    "l9": "landsat-9",
}


def create_session() -> requests.Session:
    """Create a requests session with proper headers."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })
    session.trust_env = False
    return session


def validate_bbox(bbox: List[float]) -> Tuple[float, float, float, float]:
    """Validate and return bounding box (west, south, east, north)."""
    if len(bbox) != 4:
        raise ValueError("Bounding box must have 4 values: west south east north")
    west, south, east, north = [float(x) for x in bbox]
    if not (-180 <= west <= 180 and -180 <= east <= 180):
        raise ValueError("Longitude must be between -180 and 180")
    if not (-90 <= south <= 90 and -90 <= north <= 90):
        raise ValueError("Latitude must be between -90 and 90")
    if west >= east:
        raise ValueError("West must be less than east")
    if south >= north:
        raise ValueError("South must be less than north")
    return west, south, east, north


def validate_date(date_str: str) -> str:
    """Validate date string format."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def get_cache_key(source: str, params: Dict[str, Any]) -> str:
    """Generate cache key from source and parameters."""
    key_str = f"{source}:{json.dumps(params, sort_keys=True)}"
    return hashlib.md5(key_str.encode()).hexdigest()


def get_cached_result(cache_dir: str, cache_key: str) -> Optional[List[Dict]]:
    """Get cached search result."""
    cache_path = Path(cache_dir) / f"{cache_key}.json"
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("expires", 0) > time.time():
                    return data.get("results", [])
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def save_cached_result(cache_dir: str, cache_key: str, results: List[Dict], ttl: int = 3600):
    """Save search result to cache."""
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    cache_path = Path(cache_dir) / f"{cache_key}.json"
    data = {
        "expires": time.time() + ttl,
        "results": results,
        "cached_at": datetime.now().isoformat(),
    }
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class CopernicusCrawler:
    """Crawl metadata from Copernicus Open Access Hub."""

    BASE_URL = "https://scihub.copernicus.eu/dhus/search"

    PLATFORM_MAP = {
        "sentinel-1": "Sentinel-1",
        "sentinel-2": "Sentinel-2",
        "sentinel-3": "Sentinel-3",
        "sentinel-5p": "Sentinel-5P",
    }

    def __init__(self, session: requests.Session):
        self.session = session

    def search(
        self,
        bbox: Tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        platform: str = "sentinel-2",
        max_cloud: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Search Copernicus OpenSearch API for metadata."""
        west, south, east, north = bbox
        platform_name = self.PLATFORM_MAP.get(platform, "Sentinel-2")

        query_parts = [
            f"platformname:{platform_name}",
            f"beginposition:[{start_date}T00:00:00.000Z TO {end_date}T23:59:59.999Z]",
            f"footprint:\"Intersects(POLYGON(({west} {south},{east} {south},{east} {north},{west} {north},{west} {south})))\"",
        ]

        if max_cloud is not None and platform in ["sentinel-2", "sentinel-3"]:
            query_parts.append(f"cloudcoverpercentage:[0 TO {max_cloud}]")

        query = " AND ".join(query_parts)

        all_results = []
        start = 0
        rows = min(limit, 100)

        while start < limit:
            params = {
                "q": query,
                "start": start,
                "rows": rows,
                "format": "json",
            }

            try:
                resp = self.session.get(self.BASE_URL, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                print(f"Warning: Copernicus API error: {e}", file=sys.stderr)
                break

            entries = data.get("feed", {}).get("entry", [])
            if not entries:
                break

            if isinstance(entries, dict):
                entries = [entries]

            for entry in entries:
                scene = self._parse_entry(entry, platform)
                if scene:
                    all_results.append(scene)

            start += rows
            if len(entries) < rows:
                break

        return all_results[:limit]

    def _parse_entry(self, entry: Dict, platform: str) -> Optional[Dict]:
        """Parse Copernicus API entry to standard format."""
        try:
            title = entry.get("title", "")
            scene_id = entry.get("id", title)

            date_str = ""
            for dt in entry.get("date", []):
                if dt.get("@name") == "beginposition":
                    date_str = dt.get("#text", "")
                    break

            cloud_cover = None
            for prop in entry.get("double", []):
                if prop.get("@name") == "cloudcoverpercentage":
                    cloud_cover = float(prop.get("#text", 0))
                    break

            footprint = ""
            for prop in entry.get("str", []):
                if prop.get("@name") == "footprint":
                    footprint = prop.get("#text", "")
                    break

            return {
                "scene_id": scene_id,
                "source": "copernicus",
                "platform": platform,
                "title": title,
                "date": date_str[:10] if date_str else "",
                "cloud_cover": cloud_cover,
                "footprint": footprint,
                "metadata": {
                    "ingestion_date": next(
                        (d.get("#text", "") for d in entry.get("date", [])
                         if d.get("@name") == "ingestiondate"), ""
                    ),
                    "size": next(
                        (p.get("#text", "") for p in entry.get("str", [])
                         if p.get("@name") == "size"), ""
                    ),
                },
            }
        except (KeyError, ValueError, IndexError):
            return None


class USGSCrawler:
    """Crawl metadata from USGS EarthExplorer."""

    M2M_URL = "https://earthexplorer.usgs.gov/inventory/json/v/1.5.0"

    DATASET_MAP = {
        "landsat-5": "LANDSAT_TM_C2_L2",
        "landsat-7": "LANDSAT_ETM_C2_L2",
        "landsat-8": "LANDSAT_8_C2_L2",
        "landsat-9": "LANDSAT_9_C2_L2",
    }

    def __init__(self, session: requests.Session):
        self.session = session

    def search(
        self,
        bbox: Tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        platform: str = "landsat-8",
        max_cloud: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Search USGS M2M API for metadata."""
        west, south, east, north = bbox
        dataset = self.DATASET_MAP.get(platform, "LANDSAT_8_C2_L2")

        search_params = {
            "datasetName": dataset,
            "temporalFilter": {
                "startDate": start_date,
                "endDate": end_date,
            },
            "spatialFilter": {
                "filterType": "mbr",
                "lowerLeft": {"latitude": south, "longitude": west},
                "upperRight": {"latitude": north, "longitude": east},
            },
            "maxResults": limit,
            "startingNumber": 1,
            "sortOrder": "ASC",
        }

        if max_cloud is not None:
            search_params["sceneFilter"] = {
                "cloudCoverFilter": {"min": 0, "max": max_cloud}
            }

        try:
            resp = self.session.post(
                f"{self.M2M_URL}/search",
                json=search_params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"Warning: USGS API error: {e}", file=sys.stderr)
            return []

        results = []
        for scene in data.get("data", {}).get("results", []):
            parsed = self._parse_scene(scene, platform)
            if parsed:
                results.append(parsed)

        return results

    def _parse_scene(self, scene: Dict, platform: str) -> Optional[Dict]:
        """Parse USGS scene to standard format."""
        try:
            scene_id = scene.get("entityId", "")
            display_id = scene.get("displayId", "")

            date_str = scene.get("temporalCoverageStartDate", "")

            cloud_cover = None
            if "cloudCover" in scene:
                cloud_cover = float(scene["cloudCover"])

            footprint = ""
            if "sceneBounds" in scene:
                footprint = scene["sceneBounds"]

            return {
                "scene_id": scene_id,
                "source": "usgs",
                "platform": platform,
                "title": display_id,
                "date": date_str[:10] if date_str else "",
                "cloud_cover": cloud_cover,
                "footprint": footprint,
                "metadata": {
                    "acquisition_date": scene.get("temporalCoverageStartDate", ""),
                    "path": scene.get("path", ""),
                    "row": scene.get("row", ""),
                    "processing_level": scene.get("processingLevel", ""),
                },
            }
        except (KeyError, ValueError):
            return None


class PlanetaryComputerCrawler:
    """Crawl metadata from Microsoft Planetary Computer STAC API."""

    STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"

    COLLECTION_MAP = {
        "sentinel-2": "sentinel-2-l2a",
        "landsat-8": "landsat-8-c2-l2",
        "landsat-9": "landsat-9-c2-l2",
    }

    def __init__(self, session: requests.Session):
        self.session = session

    def search(
        self,
        bbox: Tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        platform: str = "sentinel-2",
        max_cloud: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Search Planetary Computer STAC API for metadata."""
        west, south, east, north = bbox
        collection = self.COLLECTION_MAP.get(platform, "sentinel-2-l2a")

        request_body = {
            "collections": [collection],
            "bbox": [west, south, east, north],
            "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
            "limit": min(limit, 100),
            "sortby": [{"field": "properties.datetime", "direction": "asc"}],
        }

        if max_cloud is not None:
            request_body["filter"] = {
                "op": "<=",
                "args": [{"property": "eo:cloud_cover"}, max_cloud],
            }

        all_results = []
        next_url = self.STAC_URL

        while next_url and len(all_results) < limit:
            try:
                if next_url == self.STAC_URL:
                    resp = self.session.post(next_url, json=request_body, timeout=30)
                else:
                    resp = self.session.get(next_url, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                print(f"Warning: Planetary Computer API error: {e}", file=sys.stderr)
                break

            for feature in data.get("features", []):
                parsed = self._parse_feature(feature, platform)
                if parsed:
                    all_results.append(parsed)

            next_url = None
            for link in data.get("links", []):
                if link.get("rel") == "next":
                    next_url = link.get("href")
                    break

        return all_results[:limit]

    def _parse_feature(self, feature: Dict, platform: str) -> Optional[Dict]:
        """Parse STAC feature to standard format."""
        try:
            props = feature.get("properties", {})
            scene_id = feature.get("id", "")

            date_str = props.get("datetime", "")
            if date_str:
                date_str = date_str[:10]

            cloud_cover = props.get("eo:cloud_cover")

            footprint = json.dumps(feature.get("geometry", {}))

            return {
                "scene_id": scene_id,
                "source": "planetary_computer",
                "platform": platform,
                "title": scene_id,
                "date": date_str,
                "cloud_cover": cloud_cover,
                "footprint": footprint,
                "metadata": {
                    "collection": feature.get("collection", ""),
                    "platform": props.get("platform", ""),
                    "instrument": props.get("instruments", [""])[0] if props.get("instruments") else "",
                    "processing_level": props.get("processing:level", ""),
                    "gsd": props.get("gsd", ""),
                },
            }
        except (KeyError, ValueError, IndexError):
            return None


def deduplicate_scenes(scenes: List[Dict]) -> List[Dict]:
    """Deduplicate scenes by scene_id, keeping first occurrence."""
    seen = set()
    unique = []
    for scene in scenes:
        sid = scene.get("scene_id", "")
        if sid and sid not in seen:
            seen.add(sid)
            unique.append(scene)
    return unique


def compute_statistics(scenes: List[Dict]) -> Dict:
    """Compute statistics for a list of scenes."""
    if not scenes:
        return {
            "total_scenes": 0,
            "sources": {},
            "platforms": {},
            "date_range": {"start": None, "end": None},
            "cloud_cover": {"min": None, "max": None, "mean": None, "median": None},
        }

    sources = {}
    platforms = {}
    dates = []
    cloud_covers = []

    for scene in scenes:
        src = scene.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

        plat = scene.get("platform", "unknown")
        platforms[plat] = platforms.get(plat, 0) + 1

        date = scene.get("date", "")
        if date:
            dates.append(date)

        cc = scene.get("cloud_cover")
        if cc is not None:
            cloud_covers.append(cc)

    dates.sort()
    cloud_covers.sort()

    return {
        "total_scenes": len(scenes),
        "sources": sources,
        "platforms": platforms,
        "date_range": {
            "start": dates[0] if dates else None,
            "end": dates[-1] if dates else None,
        },
        "cloud_cover": {
            "min": min(cloud_covers) if cloud_covers else None,
            "max": max(cloud_covers) if cloud_covers else None,
            "mean": sum(cloud_covers) / len(cloud_covers) if cloud_covers else None,
            "median": cloud_covers[len(cloud_covers) // 2] if cloud_covers else None,
        },
    }


def merge_results(result_files: List[str]) -> List[Dict]:
    """Merge and deduplicate results from multiple files."""
    all_scenes = []
    for filepath in result_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_scenes.extend(data)
                elif isinstance(data, dict) and "scenes" in data:
                    all_scenes.extend(data["scenes"])
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)

    return deduplicate_scenes(all_scenes)


def export_results(scenes: List[Dict], output_path: str, fmt: str = "json"):
    """Export results to JSON or CSV."""
    if fmt == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(scenes, f, ensure_ascii=False, indent=2)
    elif fmt == "csv":
        if not scenes:
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["scene_id", "source", "platform", "title", "date", "cloud_cover", "footprint"])
            return

        flat_scenes = []
        all_fieldnames = set()
        for scene in scenes:
            flat = {k: v for k, v in scene.items() if k != "metadata"}
            if "metadata" in scene:
                for mk, mv in scene["metadata"].items():
                    flat[f"meta_{mk}"] = mv
            flat_scenes.append(flat)
            all_fieldnames.update(flat.keys())

        fieldnames = sorted(all_fieldnames)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(flat_scenes)


def resolve_args(args):
    """Resolve --bbox / --place / --preset; fill in platform / source / max-cloud.

    Returns (bbox, source_label, err_code).
    """
    # Apply preset first
    if getattr(args, "preset", None):
        p = get_preset(args.preset)
        for k, v in p.items():
            if k == "description":
                continue
            current = getattr(args, k, None)
            if k in ("platform", "source", "max_cloud") and current in (
                # argparse defaults
                "sentinel-2", None,
            ):
                setattr(args, k, v)
            if k == "bbox" and current is None:
                setattr(args, k, v)

    # --bbox wins
    if getattr(args, "bbox", None) and len(args.bbox) == 4:
        return (
            validate_bbox(args.bbox),
            f"--bbox {format_bbox(args.bbox)}",
            None,
        )

    # --place
    if getattr(args, "place", None):
        try:
            bbox = resolve_place(args.place)
            return bbox, f"--place '{args.place}' → {format_bbox(bbox)}", None
        except PlaceNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return None, "not_found", 1

    # --preset (if no bbox/place, fall back to preset's bbox)
    if getattr(args, "preset", None):
        p = get_preset(args.preset)
        bbox = p.get("bbox")
        if bbox is None:
            return None, f"--preset '{args.preset}' (no spatial filter)", None
        return bbox, f"--preset '{args.preset}' → {format_bbox(bbox)}", None

    return None, "(no spatial filter)", 1  # err: must have bbox/place/preset


def cmd_search(args):
    """Execute search command."""
    bbox, source_label, err = resolve_args(args)
    if err:
        if err == 1 and source_label == "(no spatial filter)":
            print(
                "Error: --bbox W S E N, --place 'name', or --preset <name> is required.",
                file=sys.stderr,
            )
        return err
    if not (args.start_date and args.end_date):
        print("Error: --start-date and --end-date are required.", file=sys.stderr)
        return 1
    start_date = validate_date(args.start_date)
    end_date = validate_date(args.end_date)

    platform = args.platform.lower()
    platform = PLATFORM_ALIASES.get(platform, platform)

    if platform not in PLATFORM_MAP:
        print(f"Error: Unknown platform '{args.platform}'. Supported: {', '.join(PLATFORM_MAP.keys())}", file=sys.stderr)
        return 1

    source = args.source
    if not source:
        source = PLATFORM_MAP[platform]

    session = create_session()

    cache_key = get_cache_key(source, {
        "bbox": args.bbox,
        "start_date": start_date,
        "end_date": end_date,
        "platform": platform,
        "max_cloud": args.max_cloud,
        "limit": args.limit,
    })

    if args.cache_dir:
        cached = get_cached_result(args.cache_dir, cache_key)
        if cached:
            print(f"Using cached results ({len(cached)} scenes)")
            scenes = cached
        else:
            scenes = _do_search(session, source, bbox, start_date, end_date, platform, args.max_cloud, args.limit)
            save_cached_result(args.cache_dir, cache_key, scenes)
    else:
        scenes = _do_search(session, source, bbox, start_date, end_date, platform, args.max_cloud, args.limit)

    output_path = args.output or f"rs-metadata-{platform}-{start_date}-{end_date}.{args.format}"
    export_results(scenes, output_path, args.format)

    stats = compute_statistics(scenes)
    print(f"\nSearch Results:")
    print(f"  Total scenes: {stats['total_scenes']}")
    print(f"  Date range: {stats['date_range']['start']} to {stats['date_range']['end']}")
    if stats['cloud_cover']['mean'] is not None:
        print(f"  Cloud cover: {stats['cloud_cover']['min']:.1f}% - {stats['cloud_cover']['max']:.1f}% (mean: {stats['cloud_cover']['mean']:.1f}%)")
    print(f"  Output: {output_path}")

    # Phase 5: --qa sidecar summary
    if getattr(args, "qa", None):
        try:
            write_qa_summary(args.qa, args, scenes, stats)
            print(f"QA: {args.qa}")
        except OSError as e:
            print(f"WARN: could not write QA sidecar {args.qa}: {e}", file=sys.stderr)

    return 0


def _do_search(session, source, bbox, start_date, end_date, platform, max_cloud, limit):
    """Execute search against specified source."""
    if source == "copernicus":
        crawler = CopernicusCrawler(session)
    elif source == "usgs":
        crawler = USGSCrawler(session)
    elif source == "planetary":
        crawler = PlanetaryComputerCrawler(session)
    else:
        print(f"Error: Unknown source '{source}'", file=sys.stderr)
        return []

    return crawler.search(bbox, start_date, end_date, platform, max_cloud, limit)


def cmd_stats(args):
    """Execute stats command."""
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
            scenes = data if isinstance(data, list) else data.get("scenes", [])
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading {args.input}: {e}", file=sys.stderr)
        return 1

    stats = compute_statistics(scenes)

    print(f"\nStatistics for {args.input}")
    print(f"{'=' * 50}")
    print(f"Total scenes: {stats['total_scenes']}")

    if stats['sources']:
        print(f"\nBy source:")
        for src, count in stats['sources'].items():
            print(f"  {src}: {count}")

    if stats['platforms']:
        print(f"\nBy platform:")
        for plat, count in stats['platforms'].items():
            print(f"  {plat}: {count}")

    if stats['date_range']['start']:
        print(f"\nDate range: {stats['date_range']['start']} to {stats['date_range']['end']}")

    if stats['cloud_cover']['mean'] is not None:
        cc = stats['cloud_cover']
        print(f"\nCloud cover:")
        print(f"  Min: {cc['min']:.1f}%")
        print(f"  Max: {cc['max']:.1f}%")
        print(f"  Mean: {cc['mean']:.1f}%")
        print(f"  Median: {cc['median']:.1f}%")

    return 0


def cmd_merge(args):
    """Execute merge command."""
    scenes = merge_results(args.inputs)

    output_path = args.output or "merged-results.json"
    export_results(scenes, output_path, "json")

    stats = compute_statistics(scenes)
    print(f"\nMerged {len(args.inputs)} files")
    print(f"Total unique scenes: {stats['total_scenes']}")
    print(f"Output: {output_path}")

    return 0


def cmd_list_presets(args):
    print(list_presets())
    return 0


def cmd_list_regions(args):
    try:
        from place_resolver import HARDCODED_BBOXES
    except ImportError:
        print("place_resolver.py missing", file=sys.stderr)
        return 1
    print(f"Offline region catalog ({len(HARDCODED_BBOXES)} entries):\n")
    for key in sorted(HARDCODED_BBOXES.keys()):
        bbox = HARDCODED_BBOXES[key]
        print(f"  {key:<24} {format_bbox(bbox)}")
    return 0


def main(argv=None):
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="rs-metadata-crawler",
        description="Crawl satellite imagery metadata from Copernicus, USGS, and Planetary Computer",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    search_parser = subparsers.add_parser("search", help="Search for satellite metadata")
    search_parser.add_argument("--bbox", nargs=4, type=float,
                               help="Bounding box: west south east north")
    search_parser.add_argument("--place",
                               help="Place name (e.g. '北京市', '长江流域'). Offline + Nominatim.")
    search_parser.add_argument("--preset", choices=list(PRESETS.keys()),
                               help="Apply a named preset (e.g. s2-china-recent).")
    search_parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    search_parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    search_parser.add_argument("--platform", default="sentinel-2",
                               help="Satellite platform (default: sentinel-2)")
    search_parser.add_argument("--max-cloud", type=float, help="Maximum cloud cover %%")
    search_parser.add_argument("--source", choices=["copernicus", "usgs", "planetary"],
                               help="Data source (auto-detected from platform)")
    search_parser.add_argument("--output", help="Output file path")
    search_parser.add_argument("--format", choices=["json", "csv"], default="json",
                               help="Output format (default: json)")
    search_parser.add_argument("--limit", type=int, default=100,
                               help="Maximum results per source (default: 100)")
    search_parser.add_argument("--cache-dir", help="Cache directory")
    search_parser.add_argument("--qa", default=None, metavar="PATH",
                               help="Write a JSON run-summary sidecar to PATH (e.g. --qa run.qa.json). "
                                    "Records the bbox/place/preset, date range, source, and scene counts.")
    search_parser.set_defaults(func=cmd_search)

    stats_parser = subparsers.add_parser("stats", help="Show statistics for results")
    stats_parser.add_argument("--input", required=True, help="Input JSON file")
    stats_parser.set_defaults(func=cmd_stats)

    merge_parser = subparsers.add_parser("merge", help="Merge and deduplicate results")
    merge_parser.add_argument("--inputs", nargs="+", required=True, help="Input files to merge")
    merge_parser.add_argument("--output", help="Output file path")
    merge_parser.set_defaults(func=cmd_merge)

    lp = subparsers.add_parser("list-presets", help="List available --preset names")
    lp.set_defaults(func=cmd_list_presets)

    lr = subparsers.add_parser("list-regions", help="List offline-baked region names")
    lr.set_defaults(func=cmd_list_regions)

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
