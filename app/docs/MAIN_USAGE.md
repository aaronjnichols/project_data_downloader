# How to Run the Full Feature Set with main.py

## ✅ **Setup Complete!**

The codebase has been updated to support the full feature set including NOAA Atlas 14 precipitation frequency data with automatic PDF generation.

## 🚀 **Running the Complete Download**

To test the full feature set with your AOI (`data/aoi.shp`):

```bash
python main.py --project my_project.yaml
```

## 📊 **What Will Be Downloaded**

The updated configuration (`my_project.yaml`) includes:

### 1. **FEMA Flood Data**
- Layer 28: Special Flood Hazard Areas (SFHAs)  
- Layer 16: Base Flood Elevations (BFEs)
- Layer 20: Stream centerlines

### 2. **USGS LiDAR Data**
- DEM with 10-foot contour generation

### 3. **NOAA Atlas 14 Precipitation Data** ⭐ (NEW with PDF!)
- `pds_depth_english`: PDS Precipitation Depths (inches)
- `pds_intensity_english`: PDS Precipitation Intensities (in/hr)

**Each NOAA download automatically generates:**
- ✅ Raw CSV file (original NOAA API response)
- ✅ Processed CSV file (clean tabular data)
- ✅ Metadata JSON file (parameters and summary)
- ✅ **Professional PDF Report** (8.5"×11" with data tables and DDF curves)

## 📁 **Expected Output Structure**

```
output/
├── fema/
│   ├── Layer_28_*.shp     # Flood zones
│   ├── Layer_16_*.shp     # BFEs  
│   └── Layer_20_*.shp     # Stream centerlines
├── usgs_lidar/
│   ├── *.tif              # DEM raster
│   └── *_contours.shp     # Generated contours
└── noaa_atlas14/
    ├── noaa_atlas14_pds_depth_english_*.csv         # Raw data
    ├── noaa_atlas14_pds_depth_english_*_processed.csv # Clean table
    ├── noaa_atlas14_pds_depth_english_*_metadata.json # Parameters
    ├── noaa_atlas14_pds_depth_english_*_report.pdf    # 📊 PDF REPORT
    ├── noaa_atlas14_pds_intensity_english_*.csv       # Raw intensity data
    ├── noaa_atlas14_pds_intensity_english_*_processed.csv
    ├── noaa_atlas14_pds_intensity_english_*_metadata.json
    └── noaa_atlas14_pds_intensity_english_*_report.pdf # 📊 PDF REPORT
```

## 🎯 **Other Useful Commands**

```bash
# List all available data sources and layers
python main.py --list-layers

# List only NOAA Atlas 14 layers
python main.py --list-layers noaa_atlas14

# Download only NOAA data
python main.py --project my_project.yaml --sources noaa_atlas14

# Preview what would be downloaded (dry run)
python main.py --project my_project.yaml --dry-run
```

## 📄 **PDF Report Features**

Each NOAA Atlas 14 PDF report includes:

### Page 1: Data Table & Metadata
- Complete precipitation frequency estimates table
- Location coordinates (lat/lon) 
- Download timestamp
- Data source and version information
- Analysis parameters

### Page 2: Professional DDF Curves  
- **Top plot**: Precipitation depth vs duration (multiple return periods)
- **Bottom plot**: Precipitation depth vs return period (multiple durations)
- Color-coded legends matching NOAA Atlas 14 style
- Publication-quality formatting

## 🎉 **Ready to Run!**

Your AOI file (`data/aoi.shp`) is already configured. Just run:

```bash
python main.py --project my_project.yaml
```

The system will automatically:
1. Load your Arizona AOI shapefile
2. Download data from all enabled sources
3. Generate professional PDF reports for precipitation data
4. Create organized output structure with all files 