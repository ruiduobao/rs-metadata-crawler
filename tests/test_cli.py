"""Tests for CLI commands."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestCLIHelp:
    """Tests for CLI help output."""

    def test_main_no_args(self, crawler_module):
        result = crawler_module.main([])
        assert result == 1

    def test_main_version(self, crawler_module):
        with pytest.raises(SystemExit) as exc_info:
            crawler_module.main(["--version"])
        assert exc_info.value.code == 0

    def test_search_help(self, crawler_module):
        with pytest.raises(SystemExit) as exc_info:
            crawler_module.main(["search", "--help"])
        assert exc_info.value.code == 0

    def test_stats_help(self, crawler_module):
        with pytest.raises(SystemExit) as exc_info:
            crawler_module.main(["stats", "--help"])
        assert exc_info.value.code == 0

    def test_merge_help(self, crawler_module):
        with pytest.raises(SystemExit) as exc_info:
            crawler_module.main(["merge", "--help"])
        assert exc_info.value.code == 0


class TestSearchCommand:
    """Tests for search command."""

    @patch("rs_metadata_crawler._do_search")
    def test_search_basic(self, mock_search, crawler_module, sample_scenes, tmp_path):
        mock_search.return_value = sample_scenes
        output_path = str(tmp_path / "output.json")
        result = crawler_module.main([
            "search",
            "--bbox", "116", "39", "117", "40",
            "--start-date", "2024-01-01",
            "--end-date", "2024-12-31",
            "--platform", "sentinel-2",
            "--output", output_path,
        ])
        assert result == 0
        assert Path(output_path).exists()

    @patch("rs_metadata_crawler._do_search")
    def test_search_with_cloud_cover(self, mock_search, crawler_module, sample_scenes, tmp_path):
        mock_search.return_value = sample_scenes
        output_path = str(tmp_path / "output.json")
        result = crawler_module.main([
            "search",
            "--bbox", "116", "39", "117", "40",
            "--start-date", "2024-01-01",
            "--end-date", "2024-12-31",
            "--platform", "sentinel-2",
            "--max-cloud", "20",
            "--output", output_path,
        ])
        assert result == 0

    @patch("rs_metadata_crawler._do_search")
    def test_search_csv_output(self, mock_search, crawler_module, sample_scenes, tmp_path):
        mock_search.return_value = sample_scenes
        output_path = str(tmp_path / "output.csv")
        result = crawler_module.main([
            "search",
            "--bbox", "116", "39", "117", "40",
            "--start-date", "2024-01-01",
            "--end-date", "2024-12-31",
            "--platform", "sentinel-2",
            "--format", "csv",
            "--output", output_path,
        ])
        assert result == 0
        assert Path(output_path).exists()

    def test_search_invalid_platform(self, crawler_module):
        result = crawler_module.main([
            "search",
            "--bbox", "116", "39", "117", "40",
            "--start-date", "2024-01-01",
            "--end-date", "2024-12-31",
            "--platform", "invalid-platform",
        ])
        assert result == 1

    @patch("rs_metadata_crawler._do_search")
    def test_search_with_source(self, mock_search, crawler_module, sample_scenes, tmp_path):
        mock_search.return_value = sample_scenes
        output_path = str(tmp_path / "output.json")
        result = crawler_module.main([
            "search",
            "--bbox", "116", "39", "117", "40",
            "--start-date", "2024-01-01",
            "--end-date", "2024-12-31",
            "--platform", "sentinel-2",
            "--source", "copernicus",
            "--output", output_path,
        ])
        assert result == 0

    @patch("rs_metadata_crawler._do_search")
    def test_search_with_limit(self, mock_search, crawler_module, sample_scenes, tmp_path):
        mock_search.return_value = sample_scenes
        output_path = str(tmp_path / "output.json")
        result = crawler_module.main([
            "search",
            "--bbox", "116", "39", "117", "40",
            "--start-date", "2024-01-01",
            "--end-date", "2024-12-31",
            "--platform", "sentinel-2",
            "--limit", "50",
            "--output", output_path,
        ])
        assert result == 0


class TestStatsCommand:
    """Tests for stats command."""

    def test_stats_with_results(self, crawler_module, sample_scenes, tmp_path):
        input_path = str(tmp_path / "results.json")
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump(sample_scenes, f)
        result = crawler_module.main(["stats", "--input", input_path])
        assert result == 0

    def test_stats_empty_file(self, crawler_module, tmp_path):
        input_path = str(tmp_path / "empty.json")
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        result = crawler_module.main(["stats", "--input", input_path])
        assert result == 0

    def test_stats_nonexistent_file(self, crawler_module):
        result = crawler_module.main(["stats", "--input", "nonexistent.json"])
        assert result == 1


class TestMergeCommand:
    """Tests for merge command."""

    def test_merge_files(self, crawler_module, sample_scenes, tmp_path):
        file1 = str(tmp_path / "file1.json")
        file2 = str(tmp_path / "file2.json")
        output_path = str(tmp_path / "merged.json")

        with open(file1, "w", encoding="utf-8") as f:
            json.dump(sample_scenes[:2], f)
        with open(file2, "w", encoding="utf-8") as f:
            json.dump(sample_scenes[1:], f)

        result = crawler_module.main([
            "merge",
            "--inputs", file1, file2,
            "--output", output_path,
        ])
        assert result == 0
        assert Path(output_path).exists()

    def test_merge_with_duplicates(self, crawler_module, sample_scenes, tmp_path):
        file1 = str(tmp_path / "dup1.json")
        file2 = str(tmp_path / "dup2.json")
        output_path = str(tmp_path / "merged.json")

        with open(file1, "w", encoding="utf-8") as f:
            json.dump(sample_scenes, f)
        with open(file2, "w", encoding="utf-8") as f:
            json.dump(sample_scenes, f)

        result = crawler_module.main([
            "merge",
            "--inputs", file1, file2,
            "--output", output_path,
        ])
        assert result == 0

        with open(output_path, "r", encoding="utf-8") as f:
            merged = json.load(f)
        assert len(merged) == 3

    def test_merge_nonexistent_file(self, crawler_module, tmp_path):
        output_path = str(tmp_path / "merged.json")
        result = crawler_module.main([
            "merge",
            "--inputs", "nonexistent1.json", "nonexistent2.json",
            "--output", output_path,
        ])
        assert result == 0


class TestMergeResults:
    """Tests for merge_results function."""

    def test_merge_multiple_files(self, crawler_module, sample_scenes, tmp_path):
        file1 = str(tmp_path / "m1.json")
        file2 = str(tmp_path / "m2.json")

        with open(file1, "w", encoding="utf-8") as f:
            json.dump(sample_scenes[:2], f)
        with open(file2, "w", encoding="utf-8") as f:
            json.dump(sample_scenes[1:], f)

        result = crawler_module.merge_results([file1, file2])
        assert len(result) == 3

    def test_merge_empty_list(self, crawler_module):
        result = crawler_module.merge_results([])
        assert len(result) == 0

    def test_merge_with_dict_format(self, crawler_module, sample_scenes, tmp_path):
        file1 = str(tmp_path / "dict.json")
        with open(file1, "w", encoding="utf-8") as f:
            json.dump({"scenes": sample_scenes}, f)

        result = crawler_module.merge_results([file1])
        assert len(result) == 3


class TestQaSummary:
    """Phase 5: --qa sidecar summary tests for rs-metadata-crawler."""

    def test_write_qa_summary_records_inputs(self, crawler_module, tmp_path):
        """write_qa_summary should record bbox/dates/source/output fields."""
        import argparse as _ap
        qa_path = str(tmp_path / "run.qa.json")
        args = _ap.Namespace(
            bbox=[116.0, 39.0, 117.0, 40.0],
            place=None, preset=None,
            start_date="2024-01-01", end_date="2024-12-31",
            platform="sentinel-2", source="planetary",
            max_cloud=20.0, limit=10, cache_dir=None,
            output="out.json", format="json",
        )
        scenes = [{"scene_id": "S2A_x"}, {"scene_id": "S2B_y"}]
        stats = {"total_scenes": 2, "date_range": {"start": "2024-01-01", "end": "2024-12-31"}}
        crawler_module.write_qa_summary(qa_path, args, scenes, stats)
        assert Path(qa_path).exists()
        data = json.load(open(qa_path, encoding="utf-8"))
        assert data["skill"] == "rs-metadata-crawler"
        assert data["command"] == "search"
        assert data["bbox"] == [116.0, 39.0, 117.0, 40.0]
        assert data["start_date"] == "2024-01-01"
        assert data["platform"] == "sentinel-2"
        assert data["n_scenes"] == 2
        assert data["stats"] == stats
        assert "timestamp" in data
        assert "version" in data

    def test_write_qa_summary_records_place_and_preset(self, crawler_module, tmp_path):
        """When --place/--preset is used, they should be recorded."""
        import argparse as _ap
        qa_path = str(tmp_path / "run.qa.json")
        args = _ap.Namespace(
            bbox=None, place="北京市", preset="s2-china-recent",
            start_date="2024-06-01", end_date="2024-06-30",
            platform="sentinel-2", source="planetary",
            max_cloud=None, limit=50, cache_dir=None,
            output=None, format="json",
        )
        crawler_module.write_qa_summary(qa_path, args, [], {"total_scenes": 0})
        data = json.load(open(qa_path, encoding="utf-8"))
        assert data["place"] == "北京市"
        assert data["preset"] == "s2-china-recent"
        assert data["bbox"] is None
        assert data["n_scenes"] == 0

    @patch("rs_metadata_crawler._do_search")
    def test_search_writes_qa_sidecar(self, mock_search, crawler_module, sample_scenes, tmp_path):
        """search --qa PATH should produce a JSON sidecar after a successful crawl."""
        mock_search.return_value = sample_scenes
        output_path = str(tmp_path / "output.json")
        qa_path = str(tmp_path / "run.qa.json")
        result = crawler_module.main([
            "search",
            "--bbox", "116", "39", "117", "40",
            "--start-date", "2024-01-01",
            "--end-date", "2024-12-31",
            "--platform", "sentinel-2",
            "--output", output_path,
            "--qa", qa_path,
        ])
        assert result == 0
        assert Path(qa_path).exists()
        data = json.load(open(qa_path, encoding="utf-8"))
        assert data["command"] == "search"
        assert data["n_scenes"] == len(sample_scenes)
        assert data["start_date"] == "2024-01-01"

    def test_search_help_includes_qa(self, crawler_module):
        with pytest.raises(SystemExit) as exc_info:
            crawler_module.main(["search", "--help"])
        assert exc_info.value.code == 0
        import subprocess
        script = str(Path(__file__).parent.parent / "rs-metadata-crawler.py")
        result = subprocess.run(
            ["python", script, "search", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert "--qa" in result.stdout
