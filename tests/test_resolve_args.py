"""test_resolve_args.py — Tests for resolve_args() in rs-metadata-crawler."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

import rs_metadata_crawler  # noqa: E402


def make_args(**kwargs):
    defaults = dict(
        platform="sentinel-2",
        source=None,
        bbox=None,
        place=None,
        preset=None,
        start_date="2024-06-01",
        end_date="2024-06-30",
        max_cloud=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestResolveArgs(unittest.TestCase):
    def test_bbox(self):
        args = make_args(bbox=[73, 18, 135, 54])
        bbox, label, err = rs_metadata_crawler.resolve_args(args)
        self.assertIsNone(err)
        self.assertEqual(bbox, (73.0, 18.0, 135.0, 54.0))

    def test_place(self):
        args = make_args(place="北京市")
        bbox, label, err = rs_metadata_crawler.resolve_args(args)
        self.assertIsNone(err)
        self.assertEqual(bbox, (115.7, 39.4, 116.8, 40.3))

    def test_preset_fills_bbox(self):
        args = make_args(preset="s2-china-recent")
        bbox, label, err = rs_metadata_crawler.resolve_args(args)
        self.assertIsNone(err)
        self.assertEqual(bbox, (73.0, 18.0, 135.0, 54.0))
        # preset should fill in platform / source / max_cloud
        self.assertEqual(args.platform, "sentinel-2")
        self.assertEqual(args.source, "planetary")
        self.assertEqual(args.max_cloud, 30.0)

    def test_no_extent_errors(self):
        args = make_args()
        bbox, label, err = rs_metadata_crawler.resolve_args(args)
        self.assertEqual(err, 1)

    def test_bbox_wins_over_place(self):
        args = make_args(bbox=[100, 20, 120, 40], place="北京市")
        bbox, label, err = rs_metadata_crawler.resolve_args(args)
        self.assertIsNone(err)
        self.assertEqual(bbox, (100.0, 20.0, 120.0, 40.0))

    def test_user_platform_kept(self):
        args = make_args(preset="s2-china-recent", platform="landsat-8")
        bbox, label, err = rs_metadata_crawler.resolve_args(args)
        # The preset logic should NOT overwrite an explicit user platform
        self.assertEqual(args.platform, "landsat-8")


if __name__ == "__main__":
    unittest.main(verbosity=2)
