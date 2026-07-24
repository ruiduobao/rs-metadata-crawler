---
description: 'Crawl satellite imagery metadata from Copernicus, USGS EarthExplorer,
  and Microsoft Planetary Computer.

  Search by bbox, date range, cloud cover, and platform. Output CSV/JSON with statistics
  and deduplication.

  从 Copernicus、USGS EarthExplorer 和 Microsoft Planetary Computer 爬取卫星影像元数据。

  支持按边界框、日期范围、云量和卫星平台搜索，输出 CSV/JSON 格式，含统计摘要和去重功能。

  '
name: rs-metadata-crawler
---

# RS Metadata Crawler

Crawl satellite imagery metadata from multiple sources without downloading actual images.

## Supported Data Sources

| Source | Satellites | Auth Required |
|--------|-----------|---------------|
| Copernicus Open Access Hub | Sentinel-1/2/3/5P | No (metadata only) |
| USGS EarthExplorer | Landsat-5/7/8/9 | No (public endpoints) |
| Microsoft Planetary Computer | Sentinel-2, Landsat | No |

## Usage

```bash
# Search Sentinel-2 metadata
python rs-metadata-crawler.py search --bbox 116 39 117 40 --start-date 2024-01-01 --end-date 2024-12-31 --platform sentinel-2 --max-cloud 20

# Search Landsat from USGS
python rs-metadata-crawler.py search --bbox 116 39 117 40 --start-date 2024-01-01 --end-date 2024-12-31 --platform landsat-8 --source usgs

# Show statistics
python rs-metadata-crawler.py stats --input results.json

# Merge and deduplicate results
python rs-metadata-crawler.py merge --inputs a.json b.json --output merged.json
```

## Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--bbox` | Bounding box: west south east north | `116 39 117 40` |
| `--start-date` | Start date (YYYY-MM-DD) | `2024-01-01` |
| `--end-date` | End date (YYYY-MM-DD) | `2024-12-31` |
| `--platform` | Satellite platform | `sentinel-2`, `landsat-8` |
| `--max-cloud` | Maximum cloud cover % | `20` |
| `--source` | Data source | `copernicus`, `usgs`, `planetary` |
| `--output` | Output file path | `results.json` |
| `--format` | Output format | `json`, `csv` |
| `--limit` | Max results per source | `100` |
| `--cache-dir` | Cache directory | `.cache` |

---

## 中文说明

从 Copernicus、USGS EarthExplorer 和 Microsoft Planetary Computer 爬取卫星影像元数据，不下载实际影像。

### 支持的数据源

| 数据源 | 卫星 | 需要认证 |
|--------|------|----------|
| Copernicus Open Access Hub | Sentinel-1/2/3/5P | 否（仅元数据） |
| USGS EarthExplorer | Landsat-5/7/8/9 | 否（公开接口） |
| Microsoft Planetary Computer | Sentinel-2, Landsat | 否 |

### 使用方法

```bash
# 搜索 Sentinel-2 元数据
python rs-metadata-crawler.py search --bbox 116 39 117 40 --start-date 2024-01-01 --end-date 2024-12-31 --platform sentinel-2 --max-cloud 20

# 从 USGS 搜索 Landsat
python rs-metadata-crawler.py search --bbox 116 39 117 40 --start-date 2024-01-01 --end-date 2024-12-31 --platform landsat-8 --source usgs

# 查看统计信息
python rs-metadata-crawler.py stats --input results.json

# 合并去重
python rs-metadata-crawler.py merge --inputs a.json b.json --output merged.json
```
