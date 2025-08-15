# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-source geospatial data downloader that fetches data from federal/public sources (FEMA, USGS, NOAA) within user-defined Areas of Interest (AOI). Provides both CLI and REST API interfaces.

## Key Commands

### Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# CLI: Full download with project config
python main.py --project my_project.yaml

# CLI: Download specific sources only
python main.py --project my_project.yaml --sources fema noaa_atlas14

# CLI: Dry run to preview downloads
python main.py --project my_project.yaml --dry-run

# CLI: List available data layers
python main.py --list-layers

# API: Start server
python start_api.py

# API: Test functionality
python test_api.py

# Docker deployment
docker-compose up --build
```

## Architecture

### Plugin-Based Downloader System
All data source downloaders inherit from `BaseDownloader` in `core/base_downloader.py`. Each downloader must implement:
- `query_layers()` - Return available layers for the AOI
- `download_layer()` - Download and clip data to AOI bounds
- Auto-registration in `downloaders/__init__.py`

### Core Components
- **`main.py`**: CLI orchestrator that coordinates AOI loading, downloader initialization, and output processing
- **`core/aoi_manager.py`**: Validates and reprojects AOI shapefiles, handles spatial reference systems
- **`core/data_processor.py`**: Organizes outputs, generates metadata, creates summary reports
- **`api/`**: FastAPI implementation with background job processing and file serving

### Data Flow
1. Load AOI shapefile → Validate/reproject to appropriate CRS
2. Initialize selected downloaders → Query available layers
3. Download data → Clip to AOI bounds
4. Process outputs → Generate metadata and reports
5. Organize in hierarchical structure under `output/Project_Name/`

### Currently Implemented Downloaders
- **FEMA** (`fema_downloader.py`): 31 NFHL layers via ArcGIS REST API
- **USGS LiDAR** (`usgs_lidar_downloader.py`): 3DEP DEMs with optional contour generation via rasterio
- **NOAA Atlas 14** (`noaa_atlas14_downloader.py`): Precipitation data with automatic PDF report generation

### Adding New Data Sources
1. Create new class inheriting from `BaseDownloader`
2. Implement required methods with proper `LayerInfo` and `DownloadResult` returns
3. Register in `downloaders/__init__.py`
4. Handle spatial clipping to AOI bounds
5. Generate appropriate metadata

## Configuration

### Project Configuration (YAML)
```yaml
project_name: "My Project"
aoi_shapefile: "data/my_aoi.shp"
sources:
  fema:
    layers: ["S_FLD_HAZ_AR", "S_BFE"]
  usgs_lidar:
    resolution: 1m
    generate_contours: true
```

### API Integration
- OpenAPI schema at `/openapi.json` for GPT Actions
- Background job processing with status tracking
- File download endpoints for result retrieval

## Important Patterns

- **Dataclass Models**: Use `LayerInfo` and `DownloadResult` for type safety
- **Spatial Operations**: All data automatically clipped to AOI bounds using GeoPandas/rasterio
- **Error Handling**: Structured logging with proper error propagation
- **Metadata**: Generate JSON metadata for all downloads
- **Registry Pattern**: Downloaders auto-register on import