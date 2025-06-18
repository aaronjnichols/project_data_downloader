# Multi-Source Geospatial Data Downloader

A Python application for automatically downloading geospatial data from multiple federal and public data sources within a user-defined Area of Interest (AOI). Built with an extensible plugin architecture for easy addition of new data sources.

## Features

### Currently Supported Data Sources
- **FEMA NFHL (National Flood Hazard Layer)** - All 31 layers including:
  - Flood Hazard Zones
  - Base Flood Elevations (BFEs)  
  - Cross-Sections
  - Water Lines (Stream Centerlines)
  - Levees
  - FIRM Panels
  - And 25+ additional flood-related layers

### Planned Data Sources (Future Releases)
- **USGS LiDAR** (3DEP program)
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
   
   # Download only FEMA data
   python main.py --project my_project.yaml --sources fema
   
   # Preview what would be downloaded (dry run)
   python main.py --project my_project.yaml --dry-run
   ```

## Command Line Interface

### Available Commands

```bash
# List all available data sources and layers
python main.py --list-layers

# List layers for specific source
python main.py --list-layers fema

# Download with custom configuration
python main.py --project my_project.yaml --config config/settings.yaml

# Download specific sources only
python main.py --project my_project.yaml --sources fema nlcd

# Dry run to preview downloads
python main.py --project my_project.yaml --dry-run
```

## Configuration

### Project Configuration (`my_project.yaml`)

```yaml
project:
  name: "My Project"
  aoi_file: "data/aoi.shp"
  output_directory: "./output"

data_sources:
  fema:
    enabled: true
    layers: "all"  # or ["28", "16", "14"] for specific layers
    config:
      max_retries: 3
      timeout: 60
```

### Global Settings (`config/settings.yaml`)

Controls application-wide settings like logging, download timeouts, and processing options.

## Output Structure

Downloads are organized by data source:

```
output/
├── My_Project/
│   ├── fema/
│   │   ├── Flood_Hazard_Zones_clipped.shp
│   │   ├── Base_Flood_Elevations_clipped.shp
│   │   └── Cross_Sections_clipped.shp
│   ├── metadata/
│   │   ├── download_summary_20231215_143022.json
│   │   └── download_summary_20231215_143022.txt
│   └── logs/
```

## Architecture

### Plugin-Based Design

The application uses a plugin architecture where each data source is implemented as a separate downloader class:

```
├── core/                    # Base classes and utilities
├── downloaders/             # Data source plugins
│   ├── fema_downloader.py
│   ├── usgs_lidar_downloader.py  # (future)
│   └── nlcd_downloader.py        # (future)
├── utils/                   # Utility functions
└── config/                  # Configuration files
```

### Adding New Data Sources

To add a new data source:

1. Create a new downloader class inheriting from `BaseDownloader`
2. Implement required methods: `get_available_layers()`, `download_layer()`
3. Register the downloader in `downloaders/__init__.py`

Example:
```python
from core.base_downloader import BaseDownloader, LayerInfo, DownloadResult

class MyDataDownloader(BaseDownloader):
    @property
    def source_name(self) -> str:
        return "My Data Source"
    
    def get_available_layers(self) -> Dict[str, LayerInfo]:
        # Return available layers
        pass
    
    def download_layer(self, layer_id: str, aoi_bounds, output_path: str) -> DownloadResult:
        # Download implementation
        pass
```

## Dependencies

- **geopandas**: Spatial data processing
- **requests**: HTTP downloads with retry logic
- **PyYAML**: Configuration file parsing
- **rasterio**: Raster data processing
- **shapely**: Geometric operations

See `requirements.txt` for complete list.

## Troubleshooting

### Common Issues

1. **AOI Loading Errors:**
   - Ensure AOI shapefile exists and path is correct
   - Check shapefile has valid geometries
   - Verify CRS is properly defined

2. **Download Failures:**
   - Check internet connectivity
   - Verify AOI intersects with data coverage area
   - Try increasing timeout in configuration

3. **Memory Issues:**
   - Reduce AOI size for large downloads
   - Enable processing options to limit data size

### Logging

Logs are written to console and optionally to files. Configure logging level in `config/settings.yaml`:

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  console_logging: true
  file_logging: true
```

## Contributing

### Development Setup

1. Clone repository
2. Install development dependencies: `pip install -r requirements.txt`
3. Follow the plugin architecture for new data sources

### Future Enhancements

- USGS LiDAR downloader
- NLCD raster data support  
- NRCS soils data integration
- Enhanced error handling and retry logic
- Progress bars for large downloads
- Data format conversion options

## License

[Specify your license here]

## Contact

[Your contact information] 