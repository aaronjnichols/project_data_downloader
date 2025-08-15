# Streamlit Geospatial Data Downloader

A professional web interface for downloading geospatial data from multiple federal and public data sources including FEMA NFHL, USGS LiDAR, and NOAA Atlas 14.

## Features

### 🎯 Area of Interest (AOI) Definition
- **Shapefile Upload**: Upload .shp, .shx, .dbf files with optional .prj and .cpg files
- **Bounding Box**: Define rectangular AOI using coordinate inputs
- **Interactive Map**: Visualize your AOI with Folium-powered maps
- **Validation**: Automatic coordinate and area validation

### 📊 Data Source Integration
- **FEMA NFHL**: National Flood Hazard Layer data including flood zones and base flood elevations
- **USGS LiDAR**: 3DEP digital elevation models with optional contour generation
- **NOAA Atlas 14**: Precipitation frequency data with automatic PDF report generation
- **Dynamic Loading**: Real-time retrieval of available layers from API

### 🚀 Download Management
- **Job Creation**: Submit download requests to FastAPI backend
- **Real-time Progress**: Live progress tracking with status updates
- **Multiple Formats**: Download results as ZIP, GeoJSON, Shapefile, or PDF
- **Error Handling**: Comprehensive error reporting and retry logic

### 🗺️ Visualization & Preview
- **Interactive Maps**: Folium-based mapping with AOI and data visualization
- **Data Preview**: Sample feature display before full download
- **Results Summary**: Statistical overview of downloaded data
- **Professional UI**: Clean, responsive design suitable for engineers

## Installation

### 1. Install Dependencies

```bash
# Install Streamlit-specific requirements
pip install -r requirements_streamlit.txt

# Or install individual packages
pip install streamlit>=1.28.0 streamlit-folium>=0.15.0 geopandas>=0.12.0 folium>=0.14.0 requests>=2.28.0
```

### 2. Configure Environment

Create environment variables or modify `streamlit_config.py`:

```bash
# Development (default)
export API_BASE_URL="http://localhost:8000"

# Production
export API_BASE_URL="https://your-api-domain.com"
export STREAMLIT_ENV="production"
```

### 3. Test Integration

```bash
# Run integration tests
python test_streamlit_integration.py
```

## Usage

### 1. Start the FastAPI Backend

```bash
# Start the API server
python start_api.py

# Or manually
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Launch Streamlit Application

```bash
# Start Streamlit
streamlit run streamlit_app.py

# With custom port
streamlit run streamlit_app.py --server.port 8501
```

### 3. Access the Application

Open your browser to: `http://localhost:8501`

## Application Workflow

### Step 1: Define Area of Interest
1. **Upload Shapefile**: 
   - Use the sidebar file uploader
   - Upload .shp, .shx, .dbf files (required)
   - Optionally include .prj and .cpg files
   - Click "Process Shapefile"

2. **Or Set Bounding Box**:
   - Enter coordinates in the sidebar
   - Min/Max Longitude and Latitude
   - Click "Set Bounding Box"

### Step 2: Visualize AOI
- View your AOI on the interactive map
- Verify the area and bounds are correct
- AOI information displayed in sidebar

### Step 3: Select Data Sources
- View available data sources (automatically loaded)
- Choose from FEMA, USGS LiDAR, or NOAA Atlas 14
- Select specific layers for download
- Review layer descriptions and metadata

### Step 4: Start Download
- Click "Start Download Job"
- Monitor real-time progress
- View job status and completion percentage

### Step 5: Access Results
- Download complete dataset as ZIP
- Preview data with sample features
- Export in various formats (GeoJSON, Shapefile, PDF)
- View summary statistics

## File Structure

```
├── streamlit_app.py              # Main Streamlit application
├── api_client.py                 # FastAPI integration client
├── streamlit_config.py           # Configuration settings
├── requirements_streamlit.txt    # Streamlit dependencies
├── test_streamlit_integration.py # Integration tests
├── test_streamlit_basic.py       # Basic structural tests
├── start_streamlit.py            # Startup script
└── STREAMLIT_README.md          # This documentation
```

## Key Components

### `streamlit_app.py`
- Main application entry point
- UI components and layout
- Session state management
- Map visualization
- Progress monitoring

### `api_client.py`
- Comprehensive API client for FastAPI backend
- Error handling and retries
- All endpoint coverage
- Download management
- Response validation

### `streamlit_config.py`
- Application configuration
- Environment settings
- UI preferences
- Data source information
- Validation parameters

## Configuration Options

### API Settings
```python
API_BASE_URL = "http://localhost:8000"  # FastAPI backend URL
API_TIMEOUT = 30                        # Request timeout (seconds)
API_RETRIES = 3                         # Number of retry attempts
```

### Map Configuration
```python
DEFAULT_MAP_CENTER = [39.8283, -98.5795]  # Continental US center
DEFAULT_MAP_ZOOM = 4                       # Initial zoom level
AOI_MAP_ZOOM = 10                         # AOI zoom level
MAP_WIDTH = 700                           # Map width (pixels)
MAP_HEIGHT = 500                          # Map height (pixels)
```

### File Upload Limits
```python
MAX_UPLOAD_SIZE_MB = 50                    # Maximum upload size
ALLOWED_SHAPEFILE_EXTENSIONS = ['shp', 'shx', 'dbf', 'prj', 'cpg']
REQUIRED_SHAPEFILE_EXTENSIONS = ['shp', 'shx', 'dbf']
```

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Ensure FastAPI backend is running
   - Check `API_BASE_URL` in config
   - Verify network connectivity

2. **Shapefile Upload Issues**
   - Ensure all required files (.shp, .shx, .dbf) are uploaded
   - Check file size limits
   - Verify CRS is supported

3. **Map Not Loading**
   - Check internet connection (Folium requires external tile servers)
   - Verify coordinates are valid
   - Clear browser cache

4. **Job Progress Not Updating**
   - Check API connection
   - Verify job was created successfully
   - Monitor browser console for errors

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG_MODE="true"
export LOG_LEVEL="DEBUG"
```

## Development

### Adding New Features

1. **New Data Source**:
   - Add source info to `Config.DATA_SOURCES`
   - Update API client methods if needed
   - Add UI components in main app

2. **New Export Format**:
   - Add method to `api_client.py`
   - Update results display in `streamlit_app.py`
   - Add configuration options

3. **UI Improvements**:
   - Modify CSS in `StyleConfig.CUSTOM_CSS`
   - Add new components to main app
   - Update configuration as needed

### Testing

```bash
# Run integration tests
python test_streamlit_integration.py

# Test specific functionality
streamlit run streamlit_app.py --server.headless true
```

## Production Deployment

### Environment Variables
```bash
export STREAMLIT_ENV="production"
export API_BASE_URL="https://your-api-domain.com"
export DEBUG_MODE="false"
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements_streamlit.txt .
RUN pip install -r requirements_streamlit.txt

COPY streamlit_app.py api_client.py config.py ./
EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Streamlit Cloud
1. Connect your GitHub repository
2. Set environment variables in Streamlit Cloud dashboard
3. Deploy with `streamlit_app.py` as main file

## Support

For issues and questions:
1. Check this documentation
2. Run integration tests
3. Review FastAPI backend logs
4. Check browser console for errors

## Contributing

1. Follow the existing code structure
2. Add appropriate error handling
3. Update configuration as needed
4. Test integration thoroughly
5. Update documentation