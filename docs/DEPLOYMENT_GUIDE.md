# 🚀 Deployment Guide for Custom GPT Integration

This guide walks you through deploying the Multi-Source Geospatial Data Downloader API for use with OpenAI's Custom GPT Actions.

## 📋 Prerequisites

- GitHub account (for code hosting)
- Cloud hosting account (Render, Railway, Fly.io, etc.)
- OpenAI ChatGPT Plus subscription (for Custom GPT creation)

## 🌐 Deployment Options

### Option 1: Render (Recommended - Free Tier Available)

1. **Fork/Clone the Repository**
   ```bash
   git clone <your-repo-url>
   cd project_data_downloader
   ```

2. **Create Render Account**
   - Go to [render.com](https://render.com)
   - Sign up with your GitHub account

3. **Deploy Web Service**
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Configure deployment:
     - **Name**: `geospatial-downloader-api`
     - **Environment**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
     - **Instance Type**: Free (or paid for better performance)

4. **Environment Variables** (Optional)
   ```
   API_LOG_LEVEL=info
   PYTHONPATH=/opt/render/project/src
   ```

5. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)
   - Note your service URL: `https://your-app-name.onrender.com`

### Option 2: Railway

1. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   railway login
   ```

2. **Deploy**
   ```bash
   railway new
   railway add
   railway deploy
   ```

3. **Get URL**
   ```bash
   railway domain
   ```

### Option 3: Fly.io

1. **Install Fly CLI**
   ```bash
   # Install flyctl
   curl -L https://fly.io/install.sh | sh
   ```

2. **Deploy**
   ```bash
   fly auth login
   fly launch
   fly deploy
   ```

### Option 4: Docker on Any Platform

```bash
# Build image
docker build -t geospatial-api .

# Run container
docker run -p 8000:8000 geospatial-api

# Or use docker-compose
docker-compose up --build
```

## 🔧 Post-Deployment Setup

### 1. Verify API is Running

Test your deployed API:

```bash
# Replace with your actual URL
curl https://your-app-name.onrender.com/health

# Should return: {"status": "healthy", "message": "API is running"}
```

### 2. Test OpenAPI Schema

```bash
curl https://your-app-name.onrender.com/openapi.json
```

This endpoint provides the schema needed for GPT Actions.

### 3. Test Core Functionality

```bash
# Get available data sources
curl https://your-app-name.onrender.com/downloaders

# Should return information about FEMA, USGS, and NOAA data sources
```

## 🤖 Custom GPT Configuration

### Step 1: Create Custom GPT

1. Go to [ChatGPT](https://chat.openai.com)
2. Click your profile → "My GPTs" → "Create a GPT"
3. Use the GPT Builder interface

### Step 2: Configure GPT Instructions

```
You are a Geospatial Data Assistant that helps users download GIS data from federal sources.

## Your Capabilities
You can download geospatial data from:
- FEMA: Flood hazard zones, base flood elevations, stream centerlines
- USGS: Digital elevation models (DEMs) from LiDAR
- NOAA: Precipitation frequency data with PDF reports

## Workflow
When a user requests geospatial data:

1. **Understand the Request**: Ask for their Area of Interest (AOI)
   - Accept coordinates (lat/lon bounding box)
   - Accept place names (you'll convert to coordinates)
   - Accept uploaded shapefiles/KML (extract bounds)

2. **Show Available Data**: Use /downloaders to display relevant data sources
   - For flood analysis: Recommend FEMA layers 28 (flood zones), 16 (elevations)
   - For elevation analysis: Recommend USGS LiDAR DEM
   - For precipitation analysis: Recommend NOAA Atlas 14 layers

3. **Create Download Job**: Use /jobs endpoint with user's selections

4. **Monitor Progress**: Poll /jobs/{job_id} and provide updates

5. **Deliver Results**: Provide download link when complete

## Example Interactions
- "I need flood data for Houston, Texas" → Show FEMA options → Create job
- "Get elevation data for coordinates -105.3,39.9 to -105.1,40.1" → USGS DEM
- "Precipitation data for Boulder County" → NOAA Atlas 14 options

Always explain what each data layer contains and suggest the most relevant layers for their use case.
```

### Step 3: Configure Actions

1. **In the Actions tab**, click "Create new action"
2. **Import from URL**: `https://your-app-name.onrender.com/openapi.json`
3. **Authentication**: None (or configure API keys if you added them)
4. **Privacy Policy**: Add if required

### Step 4: Test Your GPT

Test with prompts like:
- "I need flood zone data for Miami, Florida"
- "Get elevation data for the coordinates 40.0150, -105.2705 to 40.0950, -105.1705"
- "Download precipitation frequency data for Boulder, Colorado"

## 🔒 Security Considerations

### For Production Use

1. **Add API Authentication**
   ```python
   # In api/main.py, add authentication middleware
   from fastapi.security import HTTPBearer
   ```

2. **Rate Limiting**
   ```bash
   pip install slowapi
   ```

3. **CORS Configuration**
   ```python
   # Update CORS settings in api/main.py
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://chat.openai.com"],  # Restrict to OpenAI
       allow_credentials=True,
       allow_methods=["GET", "POST"],
       allow_headers=["*"],
   )
   ```

4. **Environment Variables**
   ```bash
   # Set in your hosting platform
   API_LOG_LEVEL=warning
   MAX_JOBS_PER_HOUR=10
   ```

## 📊 Monitoring & Maintenance

### Health Monitoring

Set up monitoring for:
- `/health` endpoint
- API response times
- Error rates
- Storage usage

### Log Monitoring

Check logs for:
- Failed downloads
- API errors
- Usage patterns

### Cleanup

The API automatically cleans up old jobs after 7 days. You can also manually trigger cleanup:

```bash
curl -X POST https://your-app-name.onrender.com/admin/cleanup
```

## 🐛 Troubleshooting

### Common Issues

1. **API Not Starting**
   - Check build logs in your hosting platform
   - Verify all dependencies in requirements.txt
   - Ensure Python 3.11+ is being used

2. **GPT Action Not Working**
   - Verify OpenAPI schema URL is accessible
   - Check CORS configuration
   - Test API endpoints manually

3. **Downloads Failing**
   - Check API logs for specific errors
   - Verify internet connectivity from hosting platform
   - Test with smaller AOI areas

### Debug Commands

```bash
# Check API status
curl https://your-app-name.onrender.com/health

# Test data sources
curl https://your-app-name.onrender.com/downloaders

# Check logs (platform-specific)
# Render: View logs in dashboard
# Railway: railway logs
# Fly.io: fly logs
```

## 🎉 Success!

Your Custom GPT is now ready to download geospatial data! Users can:

1. Ask for flood, elevation, or precipitation data
2. Specify their area of interest
3. Get professionally processed GIS files
4. Download ready-to-use shapefiles and reports

**Share your GPT** with colleagues, students, or the public to make geospatial data more accessible!

---

**Need help?** Check the API documentation at `https://your-app-name.onrender.com/docs` 