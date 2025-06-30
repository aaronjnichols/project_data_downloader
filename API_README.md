# 🌍 Multi-Source Geospatial Data Downloader API

A powerful REST API that enables downloading geospatial data from multiple federal and public data sources within user-defined Areas of Interest (AOI). Perfect for integration with Custom GPT Actions in ChatGPT!

## 🚀 Quick Start

### Option 1: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start the API server
python start_api.py

# API will be available at:
# http://localhost:8000
```

### Option 2: Docker

```bash
# Using Docker Compose (recommended)
docker-compose up --build

# Or with plain Docker
docker build -t geospatial-api .
docker run -p 8000:8000 geospatial-api
```

### Option 3: Test the API

```bash
# Run comprehensive API tests
python test_api.py
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Interactive API documentation |
| `GET` | `/openapi.json` | OpenAPI schema (for GPT Actions) |
| `GET` | `/downloaders` | List all data sources |
| `GET` | `/downloaders/{id}/layers` | Get layers for a data source |
| `POST` | `/jobs` | Create download job |
| `GET` | `/jobs/{job_id}` | Get job status |
| `GET` | `/jobs/{job_id}/result` | Download results ZIP |
| `POST` | `/preview` | Preview data (sync) |
| `DELETE` | `/jobs/{job_id}` | Delete job |

## 🗂️ Available Data Sources

### 🌊 FEMA NFHL (Flood Data)
- **ID:** `fema`
- **Popular Layers:**
  - `28`: Flood Hazard Zones
  - `16`: Base Flood Elevations
  - `14`: Cross-Sections
  - `20`: Stream Centerlines

### 🏔️ USGS LiDAR (Elevation Data)
- **ID:** `usgs_lidar`  
- **Layers:**
  - `dem`: Digital Elevation Model

### 🌧️ NOAA Atlas 14 (Precipitation Data)
- **ID:** `noaa_atlas14`
- **Layers:**
  - `pds_depth_english`: Precipitation depth
  - `pds_intensity_english`: Precipitation intensity

## 💻 Usage Examples

### 1. Get Available Data Sources

```bash
curl -X GET "http://localhost:8000/downloaders"
```

### 2. Create a Download Job

```bash
curl -X POST "http://localhost:8000/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "downloader_id": "fema",
    "layer_ids": ["28", "16"],
    "aoi_bounds": {
      "minx": -105.3,
      "miny": 39.9,
      "maxx": -105.1,
      "maxy": 40.1
    }
  }'
```

### 3. Check Job Status

```bash
curl -X GET "http://localhost:8000/jobs/{job_id}"
```

### 4. Download Results

```bash
curl -X GET "http://localhost:8000/jobs/{job_id}/result" \
  -o geospatial_data.zip
```

## 🤖 Custom GPT Integration

### Step 1: Deploy Your API
Deploy to a cloud service with HTTPS:
- **Render**: Easy deployment from GitHub
- **Railway**: Simple container deployment  
- **Fly.io**: Global edge deployment
- **AWS/Google Cloud**: Enterprise solutions

### Step 2: Configure GPT Action

In ChatGPT's GPT Builder:

1. **Go to Actions tab**
2. **Import from URL**: `https://your-domain.com/openapi.json`
3. **Authentication**: None (or configure as needed)
4. **Privacy Policy**: Add your policy URL

### Step 3: GPT Instructions

```
You are a Geospatial Data Assistant that helps users download GIS data.

When a user requests geospatial data:

1. Ask for their Area of Interest (coordinates or description)
2. Show available data sources using /downloaders
3. Let them select which layers they want
4. Create a job using /jobs endpoint
5. Monitor progress with /jobs/{job_id}
6. Provide download link when complete

Always explain what each data layer contains and suggest relevant layers based on their needs.

For flood analysis, recommend FEMA layers 28 (flood zones) and 16 (elevations).
For elevation analysis, recommend USGS LiDAR DEM.
For precipitation analysis, recommend NOAA Atlas 14 layers.
```

## 🔧 Configuration

### Environment Variables

```bash
export API_HOST="0.0.0.0"      # Server host
export API_PORT="8000"         # Server port  
export API_RELOAD="false"      # Auto-reload (dev only)
export API_LOG_LEVEL="info"    # Logging level
```

### Production Considerations

1. **Rate Limiting**: Add `slowapi` middleware
2. **Authentication**: Add API keys or OAuth
3. **CORS**: Configure for your domain
4. **Monitoring**: Add logging and metrics
5. **Caching**: Cache downloader metadata
6. **Storage**: Use cloud storage for large files

## 📊 API Response Examples

### Job Status Response

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:32:15Z",
  "progress": {
    "completed_layers": 2,
    "total_layers": 2,
    "percent_complete": 100
  },
  "result_summary": {
    "total_layers": 2,
    "successful_layers": 2,
    "total_features": 1247,
    "success_rate": 1.0,
    "has_download": true
  }
}
```

### Error Response

```json
{
  "error": "Bad Request",
  "detail": "Unknown downloader: invalid_source",
  "job_id": null
}
```

## 🐛 Troubleshooting

### Common Issues

1. **API won't start**
   ```bash
   # Check dependencies
   pip install -r requirements.txt
   
   # Check port availability
   lsof -i :8000
   ```

2. **Downloads fail**
   - Check internet connectivity
   - Verify AOI coordinates are valid
   - Check API logs for detailed errors

3. **GPT Action not working**
   - Verify OpenAPI schema URL is accessible
   - Check CORS configuration
   - Ensure API is deployed with HTTPS

### Debug Mode

```bash
# Start with debug logging
API_LOG_LEVEL=debug python start_api.py

# Check logs
tail -f logs/api.log
```

## 📈 Performance

- **Concurrent Jobs**: Handled via async background tasks
- **File Sizes**: Automatically creates ZIP files for download
- **Cleanup**: Old jobs auto-deleted after 7 days
- **Memory**: Streams large files to avoid memory issues

## 🔒 Security

- **Input Validation**: All inputs validated with Pydantic
- **File Safety**: Downloads stored in isolated directories
- **Error Handling**: Detailed errors without exposing internals
- **Rate Limiting**: Ready for production rate limiting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `python test_api.py`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Visit `/docs` when API is running
- **Issues**: Report bugs on GitHub
- **API Schema**: Check `/openapi.json` for complete specification

---

**Ready to integrate with your Custom GPT? Start by deploying the API and pointing your GPT Action to `/openapi.json`!** 🎉 