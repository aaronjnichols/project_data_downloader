# Custom GPT Setup Guide

## **Step-by-Step Configuration**

### **Step 1: Create New Custom GPT**
1. Go to ChatGPT → Explore → Create a GPT
2. Click "Create" to start building

### **Step 2: Basic Configuration**

#### **Name**
```
Multi-Source Geospatial Data Downloader
```

#### **Description**
```
Download and analyze geospatial data from FEMA flood zones, USGS LiDAR elevation data, and NOAA precipitation frequency data. Upload AOI boundaries or coordinates to get immediate access to GIS data as GeoJSON or precipitation data as structured tables.
```

#### **Instructions** (Copy from CUSTOM_GPT_INSTRUCTIONS.md)
```
You are a specialized geospatial data assistant that helps users download and analyze geospatial datasets from multiple government sources including FEMA flood data, USGS LiDAR elevation data, and NOAA precipitation frequency data.

[... copy the full instructions from the other file ...]
```

### **Step 3: Conversation Starters**
Add these 4 conversation starters:
1. `Download FEMA flood zone data for my property coordinates`
2. `Get USGS elevation data for this area (upload shapefile)`
3. `Find NOAA precipitation frequency data for storm design`
4. `Analyze flood risk for this GeoJSON boundary`

### **Step 4: Configure Actions**

#### **4.1 Import Schema**
1. Click "Create new action"
2. Choose "Import from URL"
3. Enter your API URL: `https://YOUR_RENDER_APP.onrender.com/openapi.json`
4. Click "Import"

#### **4.2 Authentication**
- Set to "None" (public API)

#### **4.3 Privacy Policy**
- Add your privacy policy URL if you have one
- Or use: "This GPT uses a public API for geospatial data downloading"

### **Step 5: Test Configuration**

#### **Test the API Connection**
1. In the GPT builder, test with: "Check if the API is working"
2. Expected: GPT should call `/health` endpoint and get status

#### **Test Data Download**
1. Test with: "Download FEMA data for coordinates -105.3, 39.9, -105.1, 40.1"
2. Expected: GPT should create job, monitor progress, and retrieve data

### **Step 6: Publish**
1. Click "Save" 
2. Choose visibility (Only me / Anyone with link / Public)
3. Click "Confirm"

---

## **API Configuration Details**

### **Your API Base URL**
Replace with your actual Render deployment URL:
```
https://YOUR_APP_NAME.onrender.com
```

### **Key Endpoints the GPT Will Use**
- `GET /health` - Health check
- `GET /downloaders` - List data sources
- `POST /jobs` - Create download jobs  
- `GET /jobs/{job_id}` - Check job status
- `GET /jobs/{job_id}/data` - Get unified data (primary)

### **OpenAPI Schema URL**
```
https://YOUR_APP_NAME.onrender.com/openapi.json
```

---

## **Testing Checklist**

### **✅ Basic Functionality**
- [ ] GPT responds to conversation starters
- [ ] API health check works
- [ ] Can list available downloaders
- [ ] Can create FEMA jobs
- [ ] Can create NOAA jobs
- [ ] Can check job status
- [ ] Can retrieve unified data

### **✅ Data Processing**
- [ ] Processes GeoJSON data correctly
- [ ] Processes NOAA precipitation data
- [ ] Creates shapefiles using geopandas
- [ ] Creates CSV files from data
- [ ] Generates visualizations/charts

### **✅ Error Handling**
- [ ] Handles invalid coordinates gracefully
- [ ] Explains when jobs fail
- [ ] Provides helpful error messages
- [ ] Suggests corrections for common issues

### **✅ User Experience**
- [ ] Explains what it's doing at each step
- [ ] Provides clear data descriptions
- [ ] Offers analysis suggestions
- [ ] Creates useful deliverables

---

## **Common Setup Issues**

### **"Could not find a valid URL in 'servers'"**
**Solution**: Make sure your API has the servers field in OpenAPI config:
```python
app = FastAPI(
    servers=[{"url": "https://YOUR_APP.onrender.com"}]
)
```

### **"Schema validation error"**
**Solution**: Ensure all response models are properly defined with explicit Pydantic models (not Dict types).

### **"Action not working"**
**Solution**: 
1. Check API is deployed and accessible
2. Verify OpenAPI schema loads at `/openapi.json`
3. Test endpoints manually with curl/Postman
4. Check GPT action logs for specific errors

### **"Data not processing correctly"**
**Solution**:
1. Verify the unified endpoint `/jobs/{job_id}/data` returns proper JSON
2. Check data_type field is "geospatial" or "precipitation"
3. Ensure GeoJSON structure is valid
4. Test locally first before GPT integration

---

## **Deployment Verification**

Before configuring the GPT, verify your API is working:

```bash
# Check API health
curl https://YOUR_APP.onrender.com/health

# Check OpenAPI schema
curl https://YOUR_APP.onrender.com/openapi.json

# Test job creation
curl -X POST https://YOUR_APP.onrender.com/jobs \
  -H "Content-Type: application/json" \
  -d '{"downloader_id":"fema","layer_ids":["0"],"aoi_bounds":{"minx":-105.3,"miny":39.9,"maxx":-105.1,"maxy":40.1}}'

# Test unified data endpoint (use job_id from above)
curl https://YOUR_APP.onrender.com/jobs/JOB_ID/data
```

All endpoints should return proper JSON responses without errors.

---

## **Success Indicators**

Your Custom GPT is properly configured when:

1. **✅ API Integration**: GPT can call all API endpoints successfully
2. **✅ Data Processing**: GPT processes both GeoJSON and precipitation data
3. **✅ File Generation**: GPT creates shapefiles, CSVs, and visualizations
4. **✅ User Experience**: GPT provides clear explanations and helpful analysis
5. **✅ Error Handling**: GPT gracefully handles errors and provides guidance

Once configured, users can simply ask for geospatial data and receive immediate, processed results with generated files - exactly what the unified text-based API was designed to enable! 