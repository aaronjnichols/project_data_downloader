# Dashboard Implementation Plan

## Overview

This document outlines the implementation plan for adding an analysis dashboard to the Multi-Source Geospatial Data Downloader. The dashboard will provide calculated results based on user-provided or drawn AOI, including flood zone analysis, elevation statistics, slope analysis, and precipitation data visualization.

## Dashboard Requirements Analysis

### Data Sources & Calculations Needed:
1. **FEMA Flood Data**: Area calculations by flood zone, FIRM panel identification
2. **USGS LiDAR**: Elevation statistics, slope analysis, terrain direction
3. **NOAA Atlas 14**: Precipitation depths by return period
4. **AOI Analysis**: Total area, spatial statistics

## Proposed Architecture

### 1. **New Dashboard Component Structure**
```
src/
├── analysis/                    # New analysis module
│   ├── __init__.py
│   ├── flood_analyzer.py       # FEMA flood zone calculations
│   ├── terrain_analyzer.py     # Elevation/slope analysis
│   ├── precipitation_analyzer.py # NOAA data processing
│   └── dashboard_calculator.py  # Orchestrates all analyses
├── dashboard/                   # New dashboard interface
│   ├── __init__.py
│   ├── dashboard_app.py        # Main dashboard page
│   ├── components/             # Reusable dashboard components
│   └── visualizations.py      # Charts and data displays
```

### 2. **Integration Points**

#### **Streamlit Multi-Page App**
- Add new dashboard page to existing `streamlit_app.py`
- Use `st.session_state` to share AOI data between download and dashboard pages
- Leverage existing map components from `legacy/unified_map.py`

#### **API Extensions**
- New `/analysis` endpoints in `api/main.py`
- Background processing for complex terrain calculations
- Cached results for repeated dashboard views

### 3. **Dashboard Data Flow**

```
User AOI Input → Data Download → Analysis Engine → Dashboard Display
     ↓              ↓               ↓                ↓
  Map Drawing → FEMA/USGS/NOAA → Spatial Analysis → Interactive Charts
  File Upload → Job Processing → Statistical Calc → Summary Tables
```

## Detailed Implementation Plan

### **Phase 1: Analysis Engine (`src/analysis/`)**

#### **`flood_analyzer.py`**
```python
class FloodAnalyzer:
    def analyze_flood_zones(self, aoi_gdf, fema_data_gdf):
        # Calculate area by flood zone (AE, X, VE, etc.)
        # Identify overlapping FIRM panels
        # Return statistics and percentages
```

#### **`terrain_analyzer.py`**
```python
class TerrainAnalyzer:
    def analyze_elevation(self, aoi_gdf, dem_raster):
        # Min/max elevation extraction
        # Slope calculation using rasterio
        # Aspect (direction) analysis
        # Return terrain statistics
```

#### **`precipitation_analyzer.py`**
```python
class PrecipitationAnalyzer:
    def process_noaa_data(self, noaa_data, aoi_centroid):
        # Extract precipitation depths by return period
        # Format for dashboard display
        # Return structured data
```

### **Phase 2: Dashboard Interface (`dashboard/`)**

#### **Multi-Page Streamlit Structure**
```python
# streamlit_app.py - Main entry point
def main():
    st.sidebar.selectbox("Choose Page", [
        "Data Downloader",    # Existing functionality
        "Analysis Dashboard", # New dashboard page
        "Job History"         # Optional: job management
    ])

# dashboard/dashboard_app.py - New dashboard page
def show_dashboard():
    # AOI input (reuse existing components)
    # Data source selection
    # Real-time analysis display
    # Export capabilities
```

#### **Dashboard Layout Design**
```
┌─────────────────────────────────────────────────────────┐
│ AOI Selection (Map + Upload)          │ Summary Stats   │
├────────────────────────────────────────┼─────────────────┤
│ Flood Zone Analysis                    │ Elevation Stats │
│ • Zone breakdown (table + pie chart)  │ • Min/Max elev  │
│ • FIRM Panels list                     │ • Avg slope %   │
│                                        │ • Slope direction│
├────────────────────────────────────────┴─────────────────┤
│ Precipitation Analysis (NOAA Atlas 14)                  │
│ • Return period table (2-yr to 1000-yr)                │
│ • Depth-Duration-Frequency curves                       │
├──────────────────────────────────────────────────────────┤
│ Export Options: PDF Report | Data Downloads | Share     │
└──────────────────────────────────────────────────────────┘
```

### **Phase 3: Integration Strategy**

#### **Leverage Existing Components**
- **AOI Management**: Extend `src/core/aoi_manager.py`
- **Data Processing**: Build on `src/core/data_processor.py`
- **Map Interface**: Reuse `legacy/unified_map.py` components
- **Job System**: Utilize existing `api/job_manager.py` for background processing

#### **Database/Caching Layer**
```python
# Optional: Add result caching
class AnalysisCache:
    def cache_results(self, aoi_hash, analysis_results):
        # Cache expensive calculations
        # Enable instant dashboard reloads
```

## Technical Implementation Details

### **1. Spatial Analysis Approach**
```python
# Flood zone area calculation
def calculate_flood_areas(aoi_gdf, fema_zones_gdf):
    # Intersection analysis
    intersections = gpd.overlay(aoi_gdf, fema_zones_gdf, how='intersection')
    
    # Area calculations
    intersections['area_sqft'] = intersections.geometry.area
    zone_stats = intersections.groupby('FLD_ZONE').agg({
        'area_sqft': 'sum'
    })
    
    # Percentage calculations
    total_aoi_area = aoi_gdf.geometry.area.sum()
    zone_stats['percentage'] = zone_stats['area_sqft'] / total_aoi_area * 100
    
    return zone_stats
```

### **2. Terrain Analysis Using Existing Tools**
```python
# Leverage existing USGS downloader capabilities
def analyze_terrain(aoi_gdf, dem_path):
    # Use rasterio for elevation statistics
    # Calculate slope using existing contour generation logic
    # Determine predominant slope direction
```

### **3. Dashboard State Management**
```python
# Streamlit session state pattern
if 'dashboard_data' not in st.session_state:
    st.session_state.dashboard_data = {
        'aoi': None,
        'analysis_results': None,
        'last_updated': None
    }
```

## Benefits of This Approach

### **1. Clean Architecture Integration**
- Extends existing plugin system without disruption
- Reuses proven components (AOI management, data downloaders)
- Follows established patterns in codebase

### **2. User Experience**
- Seamless workflow from data download to analysis
- Interactive dashboard with real-time updates
- Professional presentation suitable for engineering reports

### **3. Technical Advantages**
- Leverages existing spatial processing capabilities
- Can run analysis on previously downloaded data
- Extensible for future data sources (NLCD, NRCS soils)

### **4. Implementation Phases**
- **Phase 1**: Core analysis engine (can be tested independently)
- **Phase 2**: Dashboard interface (builds on existing Streamlit app)
- **Phase 3**: API integration and optimization

## Implementation Roadmap

### **Phase 1: Core Analysis Engine (Week 1-2)**
1. Create `src/analysis/` module structure
2. Implement `flood_analyzer.py` with FEMA data processing
3. Implement `terrain_analyzer.py` with elevation/slope calculations
4. Implement `precipitation_analyzer.py` for NOAA data
5. Create `dashboard_calculator.py` to orchestrate analyses
6. Add comprehensive unit tests for analysis functions

### **Phase 2: Dashboard Interface (Week 3-4)**
1. Extend `streamlit_app.py` with multi-page navigation
2. Create `dashboard/dashboard_app.py` main dashboard page
3. Implement dashboard layout with interactive components
4. Add visualization components (charts, tables, maps)
5. Integrate with existing AOI management system
6. Add export functionality for analysis results

### **Phase 3: API Integration & Optimization (Week 5-6)**
1. Add `/analysis` endpoints to `api/main.py`
2. Implement background processing for large AOIs
3. Add result caching for performance optimization
4. Create comprehensive dashboard documentation
5. Add integration tests for full workflow
6. Performance testing and optimization

## Questions for Refinement

1. **Data Persistence**: Should analysis results be saved for later viewing?
2. **Export Formats**: What formats for dashboard exports (PDF reports, Excel, etc.)?
3. **Performance**: Real-time analysis vs. cached results for large AOIs?
4. **User Access**: Integration with existing job system or standalone dashboard?

## Technical Considerations

### **Performance Optimization**
- Cache analysis results using AOI geometry hash
- Implement progressive loading for large datasets
- Use background processing for complex terrain analysis
- Consider database storage for historical analyses

### **Error Handling**
- Graceful degradation when data sources are unavailable
- Clear user feedback for missing or incomplete data
- Validation of AOI geometry before analysis
- Timeout handling for long-running calculations

### **Extensibility**
- Plugin architecture for adding new analysis types
- Configurable dashboard layouts
- Support for custom analysis parameters
- Integration points for future data sources

This approach maintains clean separation of concerns while providing a comprehensive analysis dashboard that leverages the existing geospatial data infrastructure.