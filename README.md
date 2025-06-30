# Multi-Source Geospatial Data Downloader

A Python application for automatically downloading geospatial data from multiple federal and public data sources within a user-defined Area of Interest (AOI). Built with an extensible plugin architecture for easy addition of new data sources.

## Project Structure

```
.
├── config/                  # Global and project configuration files
├── core/                    # Core application logic and base classes
├── data/                    # User-provided data (e.g., AOI shapefiles)
├── docs/                    # Documentation and usage guides
├── downloaders/             # Data source downloader plugins
├── examples/                # Example scripts and notebooks
├── logs/                    # Log files
├── output/                  # Downloaded data and reports
├── tests/                   # Unit and integration tests
├── utils/                   # Utility functions
├── main.py                  # Main application entry point
└── requirements.txt         # Project dependencies
```

## Features

### Currently Supported Data Sources
- **FEMA NFHL (National Flood Hazard Layer)** - All 31 layers including flood zones, BFEs, and stream centerlines
- **USGS LiDAR** - 3DEP digital elevation models with optional contour generation
- **NOAA Atlas 14** - Precipitation frequency data with automatic PDF report generation

### Planned Data Sources (Future Releases)
- **NLCD** (National Land Cover Database)
- **NRCS Soils** (SSURGO/STATSGO2)

## Quick Start

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd project_data_downloader
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Basic Usage

1. **Prepare your AOI shapefile:**
   - Place your Area of Interest shapefile in the `data/` directory
   - Update the path in your project configuration

2. **Configure your project:**
   ```bash
   # Copy the template and customize
   cp config/project_template.yaml my_project.yaml
   # Edit my_project.yaml with your AOI path and desired data sources
   ```

3. **Run the downloader:**
   ```bash
   # Download all configured data sources
   python main.py --project my_project.yaml
   
   # Download only NOAA Atlas 14 data
   python main.py --project my_project.yaml --sources noaa_atlas14
   
   # Preview what would be downloaded (dry run)
   python main.py --project my_project.yaml --dry-run
   ```

## 📖 Documentation

- [Main Usage Guide](docs/MAIN_USAGE.md) - Command line interface
- [API Usage Guide](docs/API_USAGE.md) - REST API endpoints  
- [Custom GPT Instructions](docs/CUSTOM_GPT_INSTRUCTIONS.md) - GPT configuration details
- [Custom GPT Setup Guide](docs/CUSTOM_GPT_SETUP_GUIDE.md) - Step-by-step GPT setup
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) - Production deployment

## Configuration

See `config/README.md` for details on project and global configuration.

## Output Structure

Downloads are organized by data source and project name:

```
output/
├── My_Project/
│   ├── fema/
│   │   ├── Flood_Hazard_Zones_clipped.shp
│   ├── usgs_lidar/
│   │   ├── dem.tif
│   ├── noaa_atlas14/
│   │   ├── noaa_atlas14_pds_depth_english_..._report.pdf
│   ├── metadata/
│   │   ├── download_summary.json
```

## Architecture

See `docs/ARCHITECTURE.md` for an overview of the plugin-based architecture and instructions for adding new data sources.

## REST API

🆕 **NEW**: This project now includes a REST API for integration with Custom GPT Actions!

### Quick Start API

```bash
# Install API dependencies
pip install -r requirements.txt

# Start the API server
python start_api.py

# Test the API
python test_api.py
```

**API Endpoints:**
- `GET /downloaders` - List available data sources
- `POST /jobs` - Create download jobs  
- `GET /jobs/{job_id}` - Monitor job progress
- `GET /jobs/{job_id}/result` - Download results
- `GET /openapi.json` - OpenAPI schema for GPT Actions

**For GPT Integration:** Deploy the API and use `https://your-domain.com/openapi.json` as your GPT Action schema URL.

📖 **Full API Documentation:** See `API_README.md` and `docs/API_USAGE.md`

## Dependencies

- **geopandas**: Spatial data processing
- **requests**: HTTP downloads with retry logic
- **PyYAML**: Configuration file parsing
- **rasterio**: Raster data processing
- **matplotlib**: PDF report and plot generation
- **fastapi**: REST API framework
- **uvicorn**: ASGI server

See `requirements.txt` for a complete list of dependencies. No external GIS software (e.g., GDAL, QGIS) is required.

## Troubleshooting

- Ensure your AOI shapefile exists and the path in `my_project.yaml` is correct.
- Check internet connectivity if downloads fail.
- Review log files in the `logs/` directory for detailed error messages.

## Contributing

### Development Setup

1. Clone repository
2. Install development dependencies: `pip install -r requirements.txt`
3. Follow the plugin architecture for new data sources

### Future Enhancements

- NLCD raster data support
- NRCS soils data integration
- Enhanced error handling and retry logic
- Progress bars for large downloads
- Data format conversion options

## License

[Specify your license here]

## Contact

[Your contact information] 