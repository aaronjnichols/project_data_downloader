# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Development Commands

### Setup and Installation
```bash
make install              # Install production dependencies  
make install-dev         # Install development dependencies + dev tools
make dev-setup          # Complete development environment setup
```

### Code Quality and Testing
```bash
make quality            # Run all code quality checks (format, lint, type-check, security)
make test              # Run all tests
make test-unit         # Run unit tests only
make test-integration  # Run integration tests only
make test-coverage     # Run tests with coverage report
```

### Application Services
```bash
make run-api           # Start FastAPI server (http://localhost:8000)
make run-streamlit     # Start Streamlit web interface
python main.py --project my_project.yaml  # CLI download execution
```

### Individual Quality Tools
```bash
make format            # Format code with black and isort
make lint              # Run flake8 linting
make type-check        # Run mypy type checking
make security          # Run bandit security checks and safety dependency scanning
```

## Architecture Overview

This is a **plugin-based geospatial data downloader** with three main interfaces:

### 1. Core Architecture
- **`src/core/base_downloader.py`** - Abstract base class defining the plugin interface
- **`src/core/aoi_manager.py`** - Area of Interest (AOI) shapefile management
- **`src/core/data_processor.py`** - Data processing and clipping operations
- **`src/downloaders/`** - Plugin modules for each data source (FEMA, USGS, NOAA)

### 2. Three User Interfaces
- **CLI**: `main.py` - Command-line interface using YAML project configurations
- **REST API**: `api/main.py` - FastAPI server for programmatic access and GPT Actions
- **Web UI**: `streamlit_app.py` - Interactive web interface with map visualization

### 3. Data Sources (Plugin System)
- **FEMA NFHL**: Flood hazard layers via WFS services
- **USGS LiDAR**: 3DEP elevation data with contour generation
- **NOAA Atlas 14**: Precipitation frequency data with PDF report generation

## Project Configuration

### Main Configuration Files
- **`config/project_template.yaml`** - Template for creating project configurations
- **`config/settings.yaml`** - Global application settings
- **`pyproject.toml`** - Python project metadata, dependencies, and tool configurations

### Creating a New Project
```bash
cp config/project_template.yaml my_project.yaml
# Edit my_project.yaml with your AOI path and data source selections
python main.py --project my_project.yaml
```

## Plugin Development Pattern

New data source plugins must inherit from `BaseDownloader` and implement:
- `get_available_layers()` - Return list of available data layers
- `download_layer()` - Download a specific layer within the AOI
- Error handling with retry strategies
- Metadata generation for downloaded data

## Key Dependencies and Their Usage

- **geopandas/shapely**: Spatial data processing and AOI clipping
- **rasterio**: Raster data handling (DEMs, contours)
- **fastapi/uvicorn**: REST API framework and server
- **streamlit**: Web interface framework
- **matplotlib**: PDF report generation for NOAA data
- **requests**: HTTP downloads with retry logic

## Output Structure

All downloads are organized as:
```
output/
├── {project_name}/
│   ├── jobs/{job_id}.json          # Job metadata
│   └── results/{job_id}/           # Downloaded data
│       ├── {files}.shp             # Shapefiles
│       ├── {files}.tif             # Raster data
│       ├── {files}.pdf             # Generated reports
│       └── {job_id}_results.zip    # Compressed package
```

## Testing Strategy

- **Unit tests** (`tests/unit/`): Individual component testing
- **Integration tests** (`tests/integration/`): API and Streamlit interface testing  
- **E2E tests** (`tests/e2e/`): Full workflow testing with real data sources
- **Test markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`

## Development Workflow

1. Use `make dev-setup` for initial environment setup
2. Run `make quality` before committing code
3. Use `make test` to verify functionality
4. For new features, add corresponding unit and integration tests
5. Update documentation in `docs/` for user-facing changes

## Important Notes

- All geospatial operations require an AOI shapefile in `data/` directory
- API runs on port 8000, Streamlit on default port (8501)
- Large downloads are handled asynchronously with job tracking
- PDF generation for NOAA data requires matplotlib backend configuration
- Security scanning is included in quality checks via bandit and safety