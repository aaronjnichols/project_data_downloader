# Multi-Source Geospatial Data Downloader API

A REST API for downloading geospatial data from multiple federal and public data sources within a user-defined Area of Interest (AOI). Perfect for integration with Custom GPT Actions in ChatGPT.

## Quick Start

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the API server:**
   ```bash
   python start_api.py
   ```

3. **Access the API:**
   - API Server: http://localhost:8000
   - Interactive Documentation: http://localhost:8000/docs
   - OpenAPI Schema: http://localhost:8000/openapi.json

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or with plain Docker
docker build -t geospatial-downloader-api .
docker run -p 8000:8000 geospatial-downloader-api
```

## API Endpoints

### Core Endpoints

#### `GET /downloaders`
Get all available data source downloaders and their layers.

**Response:**
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
  }
}
```

#### `GET /downloaders/{downloader_id}/layers`
Get available layers for a specific downloader.

#### `POST /jobs`
Create a new download job.

**Request Body:**
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

**Alternative with GeoJSON geometry:**
```json
{
  "downloader_id": "fema",
  "layer_ids": ["28"],
  "aoi_geometry": {
    "type": "Polygon",
    "coordinates": [[
      [-105.3, 39.9],
      [-105.1, 39.9],
      [-105.1, 40.1],
      [-105.3, 40.1],
      [-105.3, 39.9]
    ]]
  }
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job created and will start processing shortly"
}
```

#### `GET /jobs/{job_id}`
Get the status of a download job.

**Response:**
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
    "zip_file": "/app/output/results/550e8400-e29b-41d4-a716-446655440000_results.zip"
  },
  "result_summary": {
    "total_layers": 2,
    "successful_layers": 2,
    "failed_layers": 0,
    "total_features": 1247,
    "success_rate": 1.0,
    "has_download": true
  }
}
```

#### `GET /jobs/{job_id}/result`
Download the ZIP file containing all job results.

Returns a ZIP file with all downloaded geospatial data.

### Utility Endpoints

#### `POST /preview`
Get a preview of layer data (synchronous, limited features).

**Request Body:**
```json
{
  "downloader_id": "fema",
  "layer_id": "28",
  "aoi_bounds": {
    "minx": -105.3,
    "miny": 39.9,
    "maxx": -105.1,
    "maxy": 40.1
  },
  "max_features": 50
}
```

**Response:**
```json
{
  "layer_id": "28",
  "feature_count": 12,
  "geojson": {
    "type": "FeatureCollection",
    "features": [...]
  },
  "bounds": {
    "minx": -105.29,
    "miny": 39.91,
    "maxx": -105.11,
    "maxy": 40.09
  },
  "preview_note": "Preview showing 12 of 12 total features"
}
```

#### `DELETE /jobs/{job_id}`
Delete a job and its results.

#### `GET /health`
Health check endpoint.

#### `POST /admin/cleanup`
Admin endpoint to clean up old jobs and results.

## Available Data Sources

### FEMA NFHL (National Flood Hazard Layer)
- **ID:** `fema`
- **Key Layers:**
  - `28`: Flood Hazard Zones
  - `16`: Base Flood Elevations (BFEs)
  - `14`: Cross-Sections
  - `20`: Water Lines (Stream Centerlines)
  - `27`: Flood Hazard Boundaries

### USGS LiDAR
- **ID:** `usgs_lidar`
- **Key Layers:**
  - `dem`: Digital Elevation Model

### NOAA Atlas 14
- **ID:** `noaa_atlas14`
- **Key Layers:**
  - `pds_depth_english`: Precipitation depth data (English units)
  - `pds_intensity_english`: Precipitation intensity data (English units)

## Custom GPT Integration

### OpenAPI Schema URL
Use this URL in your Custom GPT Action configuration:
```
https://your-domain.com/openapi.json
```

### Example GPT Action Flow

1. **User uploads AOI or provides coordinates**
2. **GPT calls `/downloaders` to show available data sources**
3. **User selects data sources and layers**
4. **GPT calls `/jobs` to create download job**
5. **GPT polls `/jobs/{job_id}` to monitor progress**
6. **GPT provides download link from `/jobs/{job_id}/result`**

### Sample GPT Prompt Integration

```
When a user wants geospatial data:

1. Ask them to specify their area of interest (coordinates or upload shapefile)
2. Show available data sources using the /downloaders endpoint
3. Let them select which data layers they want
4. Create a job using the /jobs endpoint
5. Monitor progress and provide updates
6. When complete, provide the download link

Example user interaction:
"I need flood zone data for Boulder, Colorado"
-> Show FEMA layers available
-> Create job for flood hazard zones (layer 28)
-> Monitor and provide download when ready
```

## Error Handling

The API uses standard HTTP status codes:

- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found (job/resource doesn't exist)
- `500`: Internal Server Error

Error responses follow this format:
```json
{
  "error": "Error Type",
  "detail": "Detailed error message",
  "job_id": "job-id-if-applicable"
}
```

## Rate Limiting & Production Considerations

For production deployment:

1. **Add rate limiting** using middleware like `slowapi`
2. **Configure CORS** appropriately for your domain
3. **Use environment variables** for configuration
4. **Set up monitoring** and logging
5. **Configure reverse proxy** (nginx) for better performance
6. **Add authentication** if needed for private use

## Environment Variables

- `API_HOST`: Server host (default: "0.0.0.0")
- `API_PORT`: Server port (default: 8000)
- `API_RELOAD`: Enable auto-reload in development (default: false)
- `API_LOG_LEVEL`: Logging level (default: "info")

## Support

For issues or questions:
1. Check the interactive API documentation at `/docs`
2. Review the OpenAPI schema at `/openapi.json`
3. Check server health at `/health`

## GPT-Optimized Endpoints (NEW)

The API now includes specialized endpoints designed for Custom GPT Actions that automatically handle response size limitations and provide data in GPT-friendly formats.

### Primary GPT Endpoint

**`GET /jobs/{job_id}/data`** - Smart data delivery
- **Small datasets** (< 500KB): Returns complete GeoJSON data
- **Medium datasets** (500KB - 5MB): Returns summary + sample GeoJSON
- **Large datasets** (> 5MB): Returns summary + download links only
- Always includes download links for all formats

### Additional GPT Endpoints

**`GET /jobs/{job_id}/summary`** - Always returns summary statistics (never full data)
**`GET /jobs/{job_id}/preview`** - Small preview sample for any dataset size
**`GET /jobs/{job_id}/export/geojson`** - Direct GeoJSON file download
**`GET /jobs/{job_id}/export/shapefile`** - Shapefile ZIP download
**`GET /jobs/{job_id}/export/pdf`** - PDF reports download

### Response Format Examples

#### Small Dataset Response
```json
{
  "job_id": "abc123",
  "status": "completed",
  "data_size": "small",
  "response_type": "geojson",
  "geojson": {
    "type": "FeatureCollection",
    "features": [...]
  },
  "download_links": {
    "geojson": "/jobs/abc123/export/geojson",
    "shapefile": "/jobs/abc123/export/shapefile",
    "original_zip": "/jobs/abc123/result"
  },
  "instructions": "This dataset is small enough to be included directly as GeoJSON..."
}
```

#### Large Dataset Response
```json
{
  "job_id": "abc123",
  "status": "completed", 
  "data_size": "large",
  "response_type": "links_only",
  "summary": {
    "feature_count": 15000,
    "bounds": {"minx": -105.3, "miny": 39.9, "maxx": -105.1, "maxy": 40.1},
    "attribute_summary": {...}
  },
  "download_links": {...},
  "instructions": "This large dataset contains 15000 features. Use download links..."
}
``` 