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

**`GET /jobs/{job_id}/data`** - Unified text-based data delivery
- **GIS Data** (FEMA, USGS LiDAR): Returns clean GeoJSON (max 2000 features)
- **NOAA Data**: Returns structured precipitation dictionaries
- **Pure JSON response** - no binary files, no download links
- **GPT-ready format** with usage instructions

### Additional GPT Endpoints

**`GET /jobs/{job_id}/summary`** - Always returns summary statistics (never full data)
**`GET /jobs/{job_id}/preview`** - Small preview sample for any dataset size
**`GET /jobs/{job_id}/export/geojson`** - Direct GeoJSON file download
**`GET /jobs/{job_id}/export/shapefile`** - Shapefile ZIP download
**`GET /jobs/{job_id}/export/pdf`** - PDF reports download

### Response Format Examples

#### Geospatial Data (FEMA/USGS)
```json
{
  "job_id": "abc123",
  "status": "completed",
  "data_type": "geospatial",
  "geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [...]},
        "properties": {
          "OBJECTID": 1,
          "STUDY_ID": "12345",
          "layer_source": "flood_zones"
        }
      }
    ]
  },
  "metadata": {
    "feature_count": 150,
    "layers": [{"name": "flood_zones", "feature_count": 150}],
    "data_sources": ["fema"],
    "coordinate_system": "EPSG:4326"
  },
  "location": {
    "bounds": {"minx": -105.3, "miny": 39.9, "maxx": -105.1, "maxy": 40.1},
    "center": {"lat": 40.0, "lon": -105.2},
    "place_name": "Northern US (Western)"
  },
  "usage_instructions": "This GeoJSON contains 150 features from 1 layers. You can use this data directly with geopandas: gdf = gpd.GeoDataFrame.from_features(data['geojson']['features']). To create a shapefile: gdf.to_file('output.shp'). To create a CSV of attributes: gdf.drop('geometry', axis=1).to_csv('attributes.csv')."
}
```

#### Precipitation Data (NOAA Atlas 14)
```json
{
  "job_id": "def456",
  "status": "completed",
  "data_type": "precipitation",
  "rainfall_data": {
    "location": "Phoenix, AZ",
    "coordinates": [33.4, -112.1],
    "precipitation_frequencies": {
      "2_year": {"1_hour": 0.85, "2_hour": 1.12, "6_hour": 1.45, "12_hour": 1.65, "24_hour": 1.85},
      "5_year": {"1_hour": 1.05, "2_hour": 1.38, "6_hour": 1.78, "12_hour": 2.02, "24_hour": 2.28},
      "10_year": {"1_hour": 1.20, "2_hour": 1.58, "6_hour": 2.04, "12_hour": 2.32, "24_hour": 2.62},
      "25_year": {"1_hour": 1.42, "2_hour": 1.87, "6_hour": 2.41, "12_hour": 2.74, "24_hour": 3.10},
      "50_year": {"1_hour": 1.60, "2_hour": 2.11, "6_hour": 2.72, "12_hour": 3.09, "24_hour": 3.50},
      "100_year": {"1_hour": 1.80, "2_hour": 2.37, "6_hour": 3.06, "12_hour": 3.48, "24_hour": 3.94}
    },
    "units": "inches",
    "data_source": "NOAA Atlas 14"
  },
  "metadata": {
    "data_source": "NOAA Atlas 14",
    "layers_requested": ["ams_depth_english"],
    "units": "inches"
  },
  "location": {
    "bounds": {"minx": -112.2, "miny": 33.3, "maxx": -112.0, "maxy": 33.5},
    "center": {"lat": 33.4, "lon": -112.1},
    "place_name": "Phoenix, AZ"
  },
  "usage_instructions": "This precipitation frequency data can be used to create charts, tables, or analysis. Use pandas to work with the data: df = pd.DataFrame(data['rainfall_data']['precipitation_frequencies']). To create a CSV: df.to_csv('rainfall_data.csv'). To plot: df.plot(kind='bar')."
}
```

### GPT Integration Benefits

1. **Immediate Data Access**: Small datasets available instantly as GeoJSON
2. **No Binary Issues**: Pure JSON eliminates `ClientResponseError` and `ResponseTooLargeError`
3. **Code Interpreter Ready**: Data formats work directly with pandas, geopandas
4. **File Creation on Demand**: GPT can create shapefiles, CSVs, PDFs using Code Interpreter
5. **Rich Instructions**: Each response includes specific usage guidance

### Custom GPT Workflow

1. **Create Jobs**: Use `POST /jobs` as before
2. **Monitor Progress**: Use `GET /jobs/{job_id}` 
3. **Access Data**: Use `GET /jobs/{job_id}/data` (primary endpoint)
4. **Process Data**: Use received JSON directly with Code Interpreter
5. **Create Files**: Generate shapefiles, CSVs, charts as needed

## Text-Based Data API for Custom GPT Actions

The API is designed to provide pure text/JSON data for Custom GPT Actions, eliminating binary file issues and enabling immediate data processing within ChatGPT.

### Primary Endpoint

**`GET /jobs/{job_id}/data`** - Unified text-based data delivery
- **GIS Data** (FEMA, USGS LiDAR): Returns clean GeoJSON (max 2000 features)
- **NOAA Data**: Returns structured precipitation dictionaries
- **Pure JSON response** - no binary files, no download links
- **GPT-ready format** with usage instructions

### Response Examples

#### Geospatial Data (FEMA/USGS)
```json
{
  "job_id": "abc123",
  "status": "completed",
  "data_type": "geospatial",
  "geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [...]},
        "properties": {
          "OBJECTID": 1,
          "STUDY_ID": "12345",
          "layer_source": "flood_zones"
        }
      }
    ]
  },
  "metadata": {
    "feature_count": 150,
    "layers": [{"name": "flood_zones", "feature_count": 150}],
    "data_sources": ["fema"],
    "coordinate_system": "EPSG:4326"
  },
  "location": {
    "bounds": {"minx": -105.3, "miny": 39.9, "maxx": -105.1, "maxy": 40.1},
    "center": {"lat": 40.0, "lon": -105.2},
    "place_name": "Northern US (Western)"
  },
  "usage_instructions": "This GeoJSON contains 150 features from 1 layers. You can use this data directly with geopandas: gdf = gpd.GeoDataFrame.from_features(data['geojson']['features']). To create a shapefile: gdf.to_file('output.shp'). To create a CSV of attributes: gdf.drop('geometry', axis=1).to_csv('attributes.csv')."
}
```

#### Precipitation Data (NOAA Atlas 14)
```json
{
  "job_id": "def456",
  "status": "completed",
  "data_type": "precipitation",
  "rainfall_data": {
    "location": "Phoenix, AZ",
    "coordinates": [33.4, -112.1],
    "precipitation_frequencies": {
      "2_year": {"1_hour": 0.85, "2_hour": 1.12, "6_hour": 1.45, "12_hour": 1.65, "24_hour": 1.85},
      "5_year": {"1_hour": 1.05, "2_hour": 1.38, "6_hour": 1.78, "12_hour": 2.02, "24_hour": 2.28},
      "10_year": {"1_hour": 1.20, "2_hour": 1.58, "6_hour": 2.04, "12_hour": 2.32, "24_hour": 2.62},
      "25_year": {"1_hour": 1.42, "2_hour": 1.87, "6_hour": 2.41, "12_hour": 2.74, "24_hour": 3.10},
      "50_year": {"1_hour": 1.60, "2_hour": 2.11, "6_hour": 2.72, "12_hour": 3.09, "24_hour": 3.50},
      "100_year": {"1_hour": 1.80, "2_hour": 2.37, "6_hour": 3.06, "12_hour": 3.48, "24_hour": 3.94}
    },
    "units": "inches",
    "data_source": "NOAA Atlas 14"
  },
  "metadata": {
    "data_source": "NOAA Atlas 14",
    "layers_requested": ["ams_depth_english"],
    "units": "inches"
  },
  "location": {
    "bounds": {"minx": -112.2, "miny": 33.3, "maxx": -112.0, "maxy": 33.5},
    "center": {"lat": 33.4, "lon": -112.1},
    "place_name": "Phoenix, AZ"
  },
  "usage_instructions": "This precipitation frequency data can be used to create charts, tables, or analysis. Use pandas to work with the data: df = pd.DataFrame(data['rainfall_data']['precipitation_frequencies']). To create a CSV: df.to_csv('rainfall_data.csv'). To plot: df.plot(kind='bar')."
}
```

### GPT Integration Benefits

1. **Immediate Data Access**: Small datasets available instantly as GeoJSON
2. **No Binary Issues**: Pure JSON eliminates `ClientResponseError` and `ResponseTooLargeError`
3. **Code Interpreter Ready**: Data formats work directly with pandas, geopandas
4. **File Creation on Demand**: GPT can create shapefiles, CSVs, PDFs using Code Interpreter
5. **Rich Instructions**: Each response includes specific usage guidance

### Custom GPT Workflow

1. **Create Jobs**: Use `POST /jobs` as before
2. **Monitor Progress**: Use `GET /jobs/{job_id}` 
3. **Access Data**: Use `GET /jobs/{job_id}/data` (primary endpoint)
4. **Process Data**: Use received JSON directly with Code Interpreter
5. **Create Files**: Generate shapefiles, CSVs, charts as needed 