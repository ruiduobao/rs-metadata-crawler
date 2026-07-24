# RS Metadata Crawler / 遥感元数据爬虫

[English](#english) | [中文](#中文)

---

## English

### Introduction

RS Metadata Crawler is a command-line tool for crawling satellite imagery metadata from multiple remote sensing data sources. It allows remote sensing professionals to quickly search and browse available imagery **before downloading**, saving time spent on manual website browsing.

**Metadata Only** - This tool crawls scene IDs, dates, cloud cover, path/row, and footprints. It does NOT download actual satellite images.

### Supported Data Sources

| Source | Satellites | Auth Required |
|--------|-----------|---------------|
| [Copernicus Open Access Hub](https://scihub.copernicus.eu) | Sentinel-1/2/3/5P | No (metadata only) |
| [USGS EarthExplorer](https://earthexplorer.usgs.gov) | Landsat-5/7/8/9 | No (public endpoints) |
| [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com) | Sentinel-2, Landsat | No |

### Features

- Search by bounding box, date range, cloud cover, and satellite platform
- Output results in JSON or CSV format
- Statistics summary: total scenes, date range, cloud cover distribution
- Deduplication: merge results from multiple sources, remove duplicates
- Pagination support for large result sets
- Local caching to avoid repeated API calls

### Installation

```bash
pip install requests
```

### Usage

```bash
# Search Sentinel-2 metadata
python rs-metadata-crawler.py search --bbox 116 39 117 40 --start-date 2024-01-01 --end-date 2024-12-31 --platform sentinel-2 --max-cloud 20

# Search Landsat from USGS
python rs-metadata-crawler.py search --bbox 116 39 117 40 --start-date 2024-01-01 --end-date 2024-12-31 --platform landsat-8 --source usgs

# Search from Planetary Computer
python rs-metadata-crawler.py search --bbox 116 39 117 40 --start-date 2024-01-01 --end-date 2024-12-31 --platform sentinel-2 --source planetary

# Show statistics
python rs-metadata-crawler.py stats --input results.json

# Merge and deduplicate results
python rs-metadata-crawler.py merge --inputs a.json b.json --output merged.json
```

### Parameters

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

### Platform Aliases

| Alias | Platform |
|-------|----------|
| `s1` | sentinel-1 |
| `s2` | sentinel-2 |
| `s3` | sentinel-3 |
| `s5p` | sentinel-5p |
| `l5` | landsat-5 |
| `l7` | landsat-7 |
| `l8` | landsat-8 |
| `l9` | landsat-9 |

---

## 中文

### 简介

遥感元数据爬虫是一个命令行工具，用于从多个遥感数据源爬取卫星影像元数据。它可以帮助遥感专业人员在下载之前快速搜索和浏览可用影像，节省手动浏览网站的时间。

**仅元数据** - 本工具爬取场景ID、日期、云量、行/列号和覆盖范围，不下载实际的卫星影像。

### 支持的数据源

| 数据源 | 卫星 | 是否需要认证 |
|--------|------|-------------|
| [哥白尼开放访问中心](https://scihub.copernicus.eu) | Sentinel-1/2/3/5P | 否（仅元数据） |
| [USGS EarthExplorer](https://earthexplorer.usgs.gov) | Landsat-5/7/8/9 | 否（公开端点） |
| [微软行星计算机](https://planetarycomputer.microsoft.com) | Sentinel-2, Landsat | 否 |

### 功能特点

- 按边界框、日期范围、云量和卫星平台搜索
- 输出 JSON 或 CSV 格式的结果
- 统计摘要：总场景数、日期范围、云量分布
- 去重：合并多个数据源的结果，去除重复
- 分页支持大型结果集
- 本地缓存避免重复 API 调用

### 安装

```bash
pip install requests
```

### 使用方法

```bash
# 搜索 Sentinel-2 元数据
python rs-metadata-crawler.py search --bbox 116 39 117 40 --start-date 2024-01-01 --end-date 2024-12-31 --platform sentinel-2 --max-cloud 20

# 从 USGS 搜索 Landsat
python rs-metadata-crawler.py search --bbox 116 39 117 40 --start-date 2024-01-01 --end-date 2024-12-31 --platform landsat-8 --source usgs

# 从行星计算机搜索
python rs-metadata-crawler.py search --bbox 116 39 117 40 --start-date 2024-01-01 --end-date 2024-12-31 --platform sentinel-2 --source planetary

# 显示统计信息
python rs-metadata-crawler.py stats --input results.json

# 合并和去重结果
python rs-metadata-crawler.py merge --inputs a.json b.json --output merged.json
```

### 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--bbox` | 边界框：西 南 东 北 | `116 39 117 40` |
| `--start-date` | 开始日期 (YYYY-MM-DD) | `2024-01-01` |
| `--end-date` | 结束日期 (YYYY-MM-DD) | `2024-12-31` |
| `--platform` | 卫星平台 | `sentinel-2`, `landsat-8` |
| `--max-cloud` | 最大云量 % | `20` |
| `--source` | 数据源 | `copernicus`, `usgs`, `planetary` |
| `--output` | 输出文件路径 | `results.json` |
| `--format` | 输出格式 | `json`, `csv` |
| `--limit` | 每个源最大结果数 | `100` |
| `--cache-dir` | 缓存目录 | `.cache` |

### 平台别名

| 别名 | 平台 |
|------|------|
| `s1` | sentinel-1 |
| `s2` | sentinel-2 |
| `s3` | sentinel-3 |
| `s5p` | sentinel-5p |
| `l5` | landsat-5 |
| `l7` | landsat-7 |
| `l8` | landsat-8 |
| `l9` | landsat-9 |

---

## License / 许可证

MIT-0 (MIT No Attribution)
