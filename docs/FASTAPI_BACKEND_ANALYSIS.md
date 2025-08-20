# FastAPI Backend Analysis for Streamlit Integration

## Overview

The Multi-Source Geospatial Data Downloader has a well-structured FastAPI backend that provides comprehensive RESTful API endpoints for downloading geospatial data from multiple federal sources (FEMA, USGS, NOAA). This analysis documents the key integration points for building a Streamlit frontend.

## Base API Configuration

**Base URL**: `http://localhost:8000` (development) / `https://project-data-downloader.onrender.com` (production)
**Documentation**: Available at `/docs` (interactive Swagger UI)
**OpenAPI Schema**: Available at `/openapi.json`

## Core API Endpoints

### 1. Health Check & API Info

#### `GET /health`
- **Purpose**: Health check endpoint
- **Response**: `{"status": "healthy", "message": "API is running"}`
- **Use in Streamlit**: Check API availability on app startup

#### `GET /`
- **Purpose**: API information and version
- **Response**: Basic API metadata with links to documentation

### 2. Data Source Discovery

#### `GET /downloaders`
- **Purpose**: Get all available data source downloaders and their layers
- **Response Model**: `DownloadersResponse`
- **Response Structure**:
```json
{
  "fema": {
    "id": "fema",
    "name": "FEMA National Flood Hazard Layer (NFHL)",
    "description": "Federal Emergency Management Agency flood hazard mapping data...",
    "layers": {
      "28": {
        "id": "28",
        "name": "Flood_Hazard_Zones",
        "description": "Flood Hazard Zones",
        "geometry_type": "Polygon",
        "data_type": "Vector"
      }
    }
  },
  "usgs_lidar": {...},
  "noaa_atlas14": {...}
}
```

#### `GET /downloaders/{downloader_id}/layers`
- **Purpose**: Get detailed layer information for a specific downloader
- **Parameters**: `downloader_id` (path parameter)
- **Response Model**: `LayersResponse`

### 3. Job Management System

#### `POST /jobs` - Create Download Job
- **Purpose**: Create and queue a new download job
- **Request Model**: `JobRequest`
- **Request Body Structure**:
```json
{
  "downloader_id": "fema",
  "layer_ids": ["28", "16"],
  "aoi_bounds": {
    "minx": -105.3,
    "miny": 39.9,
    "maxx": -105.1,
    "maxy": 40.1
  },
  "config": {
    "timeout": 60
  }
}
```
- **Alternative AOI Format** (GeoJSON geometry):
```json
{
  "downloader_id": "fema",
  "layer_ids": ["28"],
  "aoi_geometry": {
    "type": "Polygon",
    "coordinates": [[
      [-105.3, 39.9], [-105.1, 39.9], 
      [-105.1, 40.1], [-105.3, 40.1], [-105.3, 39.9]
    ]]
  }
}
```
- **Response**: Job ID and initial status
- **Background Processing**: Job starts automatically via `BackgroundTasks`

#### `GET /jobs/{job_id}` - Job Status Monitoring
- **Purpose**: Get current job status and progress
- **Response Model**: `JobStatusResponse`
- **Response Structure**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2024-01-15T10:30:00Z",
  "started_at": "2024-01-15T10:30:05Z",
  "completed_at": "2024-01-15T10:32:15Z",
  "progress": {
    "completed_layers": 2,
    "total_layers": 2,
    "percent_complete": 100,
    "zip_file": "/path/to/results.zip"
  },
  "result_summary": {
    "total_layers": 2,
    "successful_layers": 2,
    "failed_layers": 0,
    "total_features": 1247,
    "success_rate": 1.0,
    "has_download": true,
    "data_url": "/jobs/{job_id}/data",
    "download_url": "/jobs/{job_id}/result"
  }
}
```

**Job Status Values**:
- `pending`: Job created, waiting to start
- `running`: Job actively processing
- `completed`: Job finished successfully
- `failed`: Job encountered an error

### 4. Data Retrieval Endpoints

#### `GET /jobs/{job_id}/data` - Primary Data Endpoint (GPT-Optimized)
- **Purpose**: Get unified text-based data for immediate consumption
- **Response Model**: `UnifiedDataResponse`
- **Data Types**:
  - `geospatial`: Returns GeoJSON (max 2000 features)
  - `precipitation`: Returns structured NOAA data
  - `elevation`: Returns elevation/terrain data
- **Best for Streamlit**: Direct data visualization and processing

#### `GET /jobs/{job_id}/result` - File Download
- **Purpose**: Download ZIP file containing all job results
- **Response**: `FileResponse` with ZIP file
- **Headers**: Includes `Content-Length` and proper MIME type
- **Use Case**: When users need raw files

#### `GET /jobs/{job_id}/summary` - Data Summary
- **Purpose**: Get summary statistics (always summary, never full data)
- **Response Model**: `DataSummary`
- **Use Case**: Quick overview without loading full dataset

#### `GET /jobs/{job_id}/preview` - Data Preview
- **Purpose**: Get small sample of data (max 50 features default)
- **Parameters**: `max_features` (query parameter)
- **Response Model**: `DataPreviewResponse`
- **Use Case**: Quick preview for large datasets

### 5. Export Endpoints

#### `GET /jobs/{job_id}/export/geojson`
- **Purpose**: Export as GeoJSON file
- **Response**: Direct file download

#### `GET /jobs/{job_id}/export/shapefile`
- **Purpose**: Export as shapefile ZIP
- **Response**: ZIP containing .shp, .shx, .dbf, .prj files

#### `GET /jobs/{job_id}/export/pdf`
- **Purpose**: Export PDF reports (NOAA data)
- **Response**: PDF file or ZIP of multiple PDFs

### 6. Preview System

#### `POST /preview` - Live Data Preview
- **Purpose**: Synchronous preview of layer data (limited features)
- **Request Model**: `PreviewRequest`
- **Response Model**: `PreviewResponse`
- **Use Case**: Let users see sample data before creating full job

### 7. Administrative Endpoints

#### `DELETE /jobs/{job_id}`
- **Purpose**: Delete job and its results
- **Use Case**: Cleanup functionality in Streamlit

#### `POST /admin/cleanup`
- **Purpose**: Clean up old jobs and results
- **Parameters**: `max_age_days` (default: 7)

## Request/Response Models Summary

### Key Models for Streamlit Integration

1. **AOI Input Models**:
   - `AOIBounds`: Bounding box (minx, miny, maxx, maxy)
   - `AOIGeometry`: GeoJSON geometry object

2. **Job Models**:
   - `JobRequest`: Create job payload
   - `JobResponse`: Job creation response
   - `JobStatusResponse`: Job status with progress

3. **Data Models**:
   - `UnifiedDataResponse`: Primary data endpoint response
   - `DataSummary`: Summary statistics
   - `DataPreviewResponse`: Preview sample data

4. **Discovery Models**:
   - `DownloadersResponse`: Available data sources
   - `LayersResponse`: Available layers per source

## Available Data Sources

### FEMA NFHL (National Flood Hazard Layer)
- **ID**: `fema`
- **Key Layers**:
  - `28`: Flood Hazard Zones (most important)
  - `16`: Base Flood Elevations (BFEs)
  - `14`: Cross-Sections
  - `20`: Water Lines (Stream Centerlines)
  - `27`: Flood Hazard Boundaries

### USGS LiDAR
- **ID**: `usgs_lidar`
- **Key Layers**:
  - `dem`: Digital Elevation Model

### NOAA Atlas 14
- **ID**: `noaa_atlas14`
- **Key Layers**:
  - `pds_depth_english`: Precipitation depth data
  - `pds_intensity_english`: Precipitation intensity data

## Authentication & Security

- **CORS**: Configured to allow all origins (`allow_origins=["*"]`)
- **No Authentication**: Currently no authentication required
- **Rate Limiting**: Not implemented (consider for production)

## Background Processing System

### Job Manager Architecture
- **File Storage**: Jobs saved as JSON files in `output/jobs/`
- **Results Storage**: Results saved in `output/results/{job_id}/`
- **ZIP Creation**: Automatic ZIP file creation for download
- **Cleanup**: Automatic cleanup of old jobs (configurable)

### Progress Tracking
- Real-time progress updates with percentage complete
- Layer-by-layer processing status
- Error handling and reporting per layer

## Error Handling

### HTTP Status Codes
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found (job/resource doesn't exist)
- `500`: Internal Server Error

### Error Response Format
```json
{
  "error": "Error Type",
  "detail": "Detailed error message",
  "job_id": "job-id-if-applicable"
}
```

## Streamlit Integration Recommendations

### 1. API Client Setup
```python
import requests
import streamlit as st

class GeospatialAPIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self):
        return self.session.get(f"{self.base_url}/health")
    
    def get_downloaders(self):
        return self.session.get(f"{self.base_url}/downloaders")
    
    def create_job(self, job_request):
        return self.session.post(f"{self.base_url}/jobs", json=job_request)
    
    def get_job_status(self, job_id):
        return self.session.get(f"{self.base_url}/jobs/{job_id}")
    
    def get_job_data(self, job_id):
        return self.session.get(f"{self.base_url}/jobs/{job_id}/data")
```

### 2. AOI Input Methods
- **Map Widget**: Use `streamlit-folium` for interactive map selection
- **Coordinate Input**: Manual lat/lon entry
- **File Upload**: Support for shapefiles/GeoJSON
- **Address Geocoding**: Convert addresses to coordinates

### 3. Job Management UI
- **Progress Bar**: Use `st.progress()` with job status polling
- **Status Display**: Real-time status updates
- **Results Panel**: Display data summary and download options

### 4. Data Visualization
- **Map Display**: Use `folium` or `pydeck` for geospatial data
- **Charts**: Use `plotly` for NOAA precipitation data
- **Tables**: Use `st.dataframe()` for attribute data

### 5. File Handling
- **Direct Data**: Use `/data` endpoint for immediate visualization
- **Downloads**: Provide download buttons for various formats
- **Caching**: Use `@st.cache_data` for API responses

## Configuration

### Environment Variables
- `API_HOST`: Server host (default: "0.0.0.0")
- `API_PORT`: Server port (default: 8000)
- `API_RELOAD`: Enable auto-reload (default: false)
- `API_LOG_LEVEL`: Logging level (default: "info")

### Production Considerations
- Configure CORS for specific domains
- Add rate limiting
- Implement authentication if needed
- Set up monitoring and logging
- Use reverse proxy (nginx) for better performance

## Example Streamlit Integration Flow

1. **App Initialization**: Health check and load available data sources
2. **User Input**: AOI selection via map or coordinates
3. **Data Source Selection**: Show available downloaders and layers
4. **Job Creation**: Submit job with selected parameters
5. **Progress Monitoring**: Real-time status updates with progress bar
6. **Data Display**: Visualize results using `/data` endpoint
7. **Export Options**: Provide download links for various formats

This comprehensive analysis provides all the necessary information to build a robust Streamlit frontend that integrates seamlessly with the existing FastAPI backend.