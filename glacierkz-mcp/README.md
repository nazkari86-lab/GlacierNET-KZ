# GlacierNET-KZ MCP Server

MCP server exposing glacier satellite data and AI predictions to any LLM client (Claude, Cursor, OpenRouter, etc.).

Reads actual `.tif` raster files in real-time — no pre-cached stats.

## Quick Start

```bash
cd glacierkz-mcp
pip install -r requirements.txt
python server.py          # stdio mode (default, for Claude Code)
python server.py --sse    # SSE mode (for remote access)
```

## Tools (15)

### Data Discovery

| Tool | Description |
|------|-------------|
| `list_data_years` | All Landsat/Sentinel-2 years available with sizes |
| `list_predictions` | Pre-computed glacier areas per year/model |
| `get_image_metadata(year)` | CRS, resolution, band count, file size, bounding box |
| `get_band_statistics(year)` | Per-band mean/std/min/max/percentiles (excludes NaN) |
| `get_available_models` | Model status, type, years predicted |
| `get_study_area_info` | Region info, target glaciers, bounding box |

### Pixel & Spatial Analysis

| Tool | Description |
|------|-------------|
| `query_pixel(year, longitude, latitude)` | Spectral signature at a lat/lng point |
| `query_pixel_classification(year, longitude, latitude)` | Spectral + terrain classification (snow/rock/vegetation/water) at a point |
| `get_glacier_area(year, model)` | Area stats for one year + model |
| `get_all_glacier_areas` | Comparison table across all years |
| `get_glacier_time_series` | Change-over-time table |
| `analyze_glacier_zones(year)` | Terrain classification by elevation zones |
| `compare_years(year1, year2)` | Side-by-side two-year comparison |

### Full Database Access

| Tool | Description |
|------|-------------|
| `get_database_summary` | Browse entire DB: all years, models, file sizes, study area |
| `describe_map_year(year)` | Full raster analysis of a single year (all bands, spectral indices, land cover) |
| `search_predictions(year, model, min_area, max_area)` | Filter predictions by criteria |
| `export_map_thumbnail(year, output_path)` | RGB PNG preview of a year |

## Resources (3)

| Resource | Description |
|----------|-------------|
| `glacierkz://catalog` | Full dataset catalog (JSON) |
| `glacierkz://year/{year}` | Metadata for a specific year (JSON) |
| `glacierkz://study-area` | Study area description (JSON) |

## Data Sources

- **Landsat** (6 years: 2000–2013) — 9 bands (B2/B3/B4/B8/B11 + NDSI/NDWI/BSI/EVI)
- **Sentinel-2** (3 years: 2016, 2017, 2020) — 11 bands (+ B8A/B12)
- Reflectance scaled ×10000, indices in [-1, 1]
- CRS: EPSG:32642 (UTM zone 42N)
- Resolution: 10m

## Connecting from Claude Code

```bash
# In your project:
claude mcp add glacierkz -- python3 /path/to/glacierkz-mcp/server.py
```

Then ask Claude:
- "What glacier data is available for 2000?"
- "Describe the 2020 map in full detail"
- "Compare glacier areas between 2016 and 2020"
- "Get the complete database summary"
- "Classify the terrain at coordinates 77.0, 43.0 for year 2020"
- "Show me the glacier time series from 2000 to 2020"
