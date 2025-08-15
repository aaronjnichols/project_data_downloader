"""
Multi-Source Geospatial Data Downloader - Streamlit Interface
============================================================

A professional web interface for the geospatial data downloader system.
Supports FEMA NFHL, USGS LiDAR, and NOAA Atlas 14 data sources.

Features:
- Shapefile upload and AOI visualization
- Interactive map interface  
- Real-time job progress tracking
- Multiple data source integration
- Professional dashboard design
"""

import streamlit as st
import geopandas as gpd
import pandas as pd
import json
import tempfile
import zipfile
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import folium
from streamlit_folium import st_folium

# Import our custom modules
from api_client import GeospatialAPIClient
from streamlit_config import Config
from enhanced_map import display_aoi_drawing_interface
from cad_export import export_job_to_cad_formats, create_cad_export_zip

# Configure page
st.set_page_config(
    page_title="Geospatial Data Downloader",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional appearance
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f1f1f;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #555;
        margin-bottom: 2rem;
    }
    .status-success {
        color: #28a745;
        font-weight: 600;
    }
    .status-error {
        color: #dc3545;
        font-weight: 600;
    }
    .status-warning {
        color: #ffc107;
        font-weight: 600;
    }
    .status-info {
        color: #17a2b8;
        font-weight: 600;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #007bff;
    }
    .progress-container {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    if 'api_client' not in st.session_state:
        st.session_state.api_client = GeospatialAPIClient(Config.API_BASE_URL)
    
    if 'uploaded_aoi' not in st.session_state:
        st.session_state.uploaded_aoi = None
    
    if 'aoi_bounds' not in st.session_state:
        st.session_state.aoi_bounds = None
        
    if 'aoi_geometry' not in st.session_state:
        st.session_state.aoi_geometry = None
    
    if 'available_sources' not in st.session_state:
        st.session_state.available_sources = None
    
    if 'current_job_id' not in st.session_state:
        st.session_state.current_job_id = None
    
    if 'job_results' not in st.session_state:
        st.session_state.job_results = {}

def create_header():
    """Create the application header"""
    st.markdown('<h1 class="main-header">🗺️ Geospatial Data Downloader</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Professional geospatial data acquisition from FEMA, USGS, and NOAA sources</p>', 
        unsafe_allow_html=True
    )

def validate_shapefile_upload(uploaded_files):
    """Validate uploaded shapefile components"""
    if not uploaded_files:
        return False, "No files uploaded"
    
    # Check for required components
    required_extensions = {'.shp', '.shx', '.dbf'}
    uploaded_extensions = {Path(f.name).suffix.lower() for f in uploaded_files}
    
    missing_extensions = required_extensions - uploaded_extensions
    if missing_extensions:
        return False, f"Missing required files: {', '.join(missing_extensions)}"
    
    return True, "Valid shapefile"

def process_shapefile_upload(uploaded_files):
    """Process uploaded shapefile and extract geometry"""
    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Save uploaded files
            shp_file = None
            for uploaded_file in uploaded_files:
                file_path = temp_path / uploaded_file.name
                with open(file_path, 'wb') as f:
                    f.write(uploaded_file.getvalue())
                
                if file_path.suffix.lower() == '.shp':
                    shp_file = file_path
            
            if not shp_file:
                return None, "No .shp file found"
            
            # Read shapefile
            gdf = gpd.read_file(shp_file)
            
            # Ensure CRS is WGS84
            if gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')
            
            # Get bounds and geometry
            bounds = gdf.total_bounds
            aoi_bounds = {
                'minx': float(bounds[0]),
                'miny': float(bounds[1]),
                'maxx': float(bounds[2]),
                'maxy': float(bounds[3])
            }
            
            # Convert to GeoJSON for API
            geojson = json.loads(gdf.to_json())
            
            # Get union of all geometries for display
            union_geom = gdf.geometry.unary_union
            
            return {
                'gdf': gdf,
                'bounds': aoi_bounds,
                'geojson': geojson,
                'union_geometry': union_geom,
                'feature_count': len(gdf),
                'total_area_km2': round(gdf.geometry.area.sum() * 111.32**2, 2)  # Rough conversion to km2
            }, None
            
    except Exception as e:
        return None, f"Error processing shapefile: {str(e)}"

def create_map(aoi_data=None, bounds=None):
    """Create folium map with AOI"""
    # Default center (Continental US)
    default_center = [39.8283, -98.5795]
    default_zoom = 4
    
    if aoi_data:
        # Center on AOI
        bounds_dict = aoi_data['bounds']
        center_lat = (bounds_dict['miny'] + bounds_dict['maxy']) / 2
        center_lon = (bounds_dict['minx'] + bounds_dict['maxx']) / 2
        m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
        
        # Add AOI boundary
        folium.GeoJson(
            aoi_data['geojson'],
            style_function=lambda x: {
                'fillColor': 'blue',
                'color': 'red',
                'weight': 2,
                'fillOpacity': 0.1,
                'opacity': 0.8
            },
            popup=folium.Popup(f"AOI: {aoi_data['feature_count']} features<br>Area: {aoi_data['total_area_km2']} km²", max_width=200),
            tooltip="Area of Interest"
        ).add_to(m)
        
        # Fit bounds
        sw = [bounds_dict['miny'], bounds_dict['minx']]
        ne = [bounds_dict['maxy'], bounds_dict['maxx']]
        m.fit_bounds([sw, ne])
        
    elif bounds:
        # Center on bounds
        center_lat = (bounds['miny'] + bounds['maxy']) / 2
        center_lon = (bounds['minx'] + bounds['maxx']) / 2
        m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
        
        # Add bounding box
        folium.Rectangle(
            bounds=[[bounds['miny'], bounds['minx']], [bounds['maxy'], bounds['maxx']]],
            color='red',
            fill=True,
            fillColor='blue',
            fillOpacity=0.1,
            weight=2,
            popup="Bounding Box AOI"
        ).add_to(m)
        
    else:
        m = folium.Map(location=default_center, zoom_start=default_zoom)
    
    return m

def load_data_sources():
    """Load available data sources from API"""
    try:
        with st.spinner("Loading available data sources..."):
            sources = st.session_state.api_client.get_downloaders()
            st.session_state.available_sources = sources
            return sources
    except Exception as e:
        st.error(f"Failed to load data sources: {str(e)}")
        return None

def display_data_source_selection(sources):
    """Display data source and layer selection interface"""
    st.subheader("📊 Data Source Selection")
    
    if not sources:
        st.warning("No data sources available. Please check API connection.")
        return None, None
    
    # Convert API response to display format
    source_options = {}
    for source_id, source_info in sources.items():
        if source_info:  # Skip None sources
            source_options[f"{source_info['name']} ({source_id})"] = {
                'id': source_id,
                'info': source_info
            }
    
    if not source_options:
        st.warning("No data sources are currently available.")
        return None, None
    
    # Clear previous selection state when data sources change
    if 'selected_source_key' not in st.session_state:
        st.session_state.selected_source_key = None
        
    # Source selection with unique key to avoid caching issues
    selected_source_name = st.selectbox(
        "Select Data Source",
        options=list(source_options.keys()),
        help="Choose the data source for your download",
        key=f"source_selector_{len(source_options)}"  # Unique key to force refresh
    )
    
    if not selected_source_name:
        return None, None
    
    selected_source = source_options[selected_source_name]
    source_id = selected_source['id']
    source_info = selected_source['info']
    
    # Display source information
    with st.expander("ℹ️ Data Source Information", expanded=True):
        st.write(f"**Description:** {source_info['description']}")
        st.write(f"**Available Layers:** {len(source_info['layers'])}")
    
    # Layer selection
    layer_options = {}
    for layer_id, layer_info in source_info['layers'].items():
        layer_name = f"{layer_info['name']} (ID: {layer_id})"
        layer_options[layer_name] = {
            'id': layer_id,
            'info': layer_info
        }
    
    selected_layers = st.multiselect(
        "Select Layers",
        options=list(layer_options.keys()),
        help="Choose one or more layers to download",
        key=f"layer_selector_{source_id}_{len(layer_options)}"  # Unique key per source
    )
    
    if selected_layers:
        # Display selected layer details
        with st.expander("📋 Selected Layer Details"):
            for layer_name in selected_layers:
                layer = layer_options[layer_name]
                layer_info = layer['info']
                st.write(f"**{layer_info['name']}**")
                st.write(f"- Description: {layer_info['description']}")
                st.write(f"- Geometry Type: {layer_info['geometry_type']}")
                st.write(f"- Data Type: {layer_info['data_type']}")
                st.write("---")
        
        # USGS-specific contour generation options
        config_options = {}
        if source_id == 'usgs_lidar':
            st.subheader("⛰️ Contour Generation Options")
            
            generate_contours = st.checkbox(
                "Generate Contour Lines",
                value=False,
                help="Generate contour line shapefiles from the DEM data",
                key=f"generate_contours_{source_id}"
            )
            
            if generate_contours:
                contour_interval = st.number_input(
                    "Contour Interval (feet)",
                    min_value=1,
                    max_value=100,
                    value=5,
                    step=1,
                    help="Vertical interval between contour lines in feet",
                    key=f"contour_interval_{source_id}"
                )
                
                config_options['contour_interval'] = contour_interval
                
                st.info(f"📏 Contours will be generated every {contour_interval} feet")
        
        layer_ids = [layer_options[name]['id'] for name in selected_layers]
        return source_id, layer_ids, config_options
    
    return source_id, None, {}

def create_download_job(source_id, layer_ids, config_options=None, aoi_bounds=None, aoi_geometry=None):
    """Create and submit download job"""
    try:
        with st.spinner("Creating download job..."):
            job_data = {
                'downloader_id': source_id,
                'layer_ids': layer_ids,
                'config': config_options or {}
            }
            
            if aoi_bounds:
                job_data['aoi_bounds'] = aoi_bounds
            elif aoi_geometry:
                job_data['aoi_geometry'] = aoi_geometry['features'][0]['geometry']
            
            # Debug: Show what's being sent to API
            with st.expander("🔍 Debug: Job Request", expanded=False):
                st.json(job_data)
            
            job_response = st.session_state.api_client.create_job(job_data)
            return job_response['job_id'], None
            
    except Exception as e:
        return None, f"Failed to create job: {str(e)}"

def monitor_job_progress(job_id):
    """Monitor and display job progress"""
    st.subheader("⏳ Job Progress")
    
    # Create progress container
    progress_container = st.container()
    status_container = st.container()
    
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    # Poll for updates
    max_attempts = 300  # 5 minutes with 1-second intervals
    attempt = 0
    
    while attempt < max_attempts:
        try:
            job_status = st.session_state.api_client.get_job_status(job_id)
            status = job_status['status']
            
            # Update progress bar based on status
            if status == 'pending':
                progress_bar.progress(10)
                status_text.markdown('<p class="status-info">⏳ Job pending...</p>', unsafe_allow_html=True)
            elif status == 'running':
                # Use progress from API if available
                progress_data = job_status.get('progress', {})
                if 'percentage' in progress_data:
                    progress_val = min(progress_data['percentage'] / 100, 0.95)
                else:
                    progress_val = 0.5
                progress_bar.progress(progress_val)
                status_text.markdown('<p class="status-info">🔄 Processing data...</p>', unsafe_allow_html=True)
            elif status == 'completed':
                progress_bar.progress(100)
                status_text.markdown('<p class="status-success">✅ Job completed successfully!</p>', unsafe_allow_html=True)
                
                # Display results
                with status_container:
                    display_job_results(job_status)
                break
            elif status == 'failed':
                progress_bar.progress(0)
                error_msg = job_status.get('error_message', 'Unknown error')
                status_text.markdown(f'<p class="status-error">❌ Job failed: {error_msg}</p>', unsafe_allow_html=True)
                break
            
            time.sleep(1)
            attempt += 1
            
        except Exception as e:
            st.error(f"Error monitoring job: {str(e)}")
            break
    
    if attempt >= max_attempts:
        st.warning("Job monitoring timed out. Please check job status manually.")

def display_job_results(job_status):
    """Display job results and download options"""
    result_summary = job_status.get('result_summary')
    if not result_summary:
        st.warning("No result summary available")
        return
    
    st.subheader("📊 Download Results")
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Layers", result_summary['total_layers'])
    
    with col2:
        st.metric("Successful", result_summary['successful_layers'])
    
    with col3:
        st.metric("Failed", result_summary['failed_layers'])
    
    with col4:
        st.metric("Features", result_summary['total_features'])
    
    # Success rate indicator
    success_rate = result_summary['success_rate'] * 100
    if success_rate == 100:
        st.success(f"🎉 All layers downloaded successfully! ({success_rate:.1f}% success rate)")
    elif success_rate >= 75:
        st.warning(f"⚠️ Most layers downloaded successfully ({success_rate:.1f}% success rate)")
    else:
        st.error(f"❌ Many layers failed to download ({success_rate:.1f}% success rate)")
    
    # Download options
    if result_summary['has_download']:
        st.subheader("💾 Download Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📦 Download ZIP", type="primary"):
                download_url = f"{Config.API_BASE_URL}{result_summary['download_url']}"
                st.markdown(f'<a href="{download_url}" target="_blank">Click here to download</a>', unsafe_allow_html=True)
        
        with col2:
            if st.button("🗺️ View Data Preview"):
                display_data_preview(job_status['job_id'])
        
        with col3:
            if st.button("📋 Download Summary"):
                download_url = f"{Config.API_BASE_URL}{result_summary['summary_url']}"
                st.markdown(f'<a href="{download_url}" target="_blank">Click here to download summary</a>', unsafe_allow_html=True)

def display_data_preview(job_id):
    """Display data preview"""
    try:
        with st.spinner("Loading data preview..."):
            preview_data = st.session_state.api_client.get_job_preview(job_id)
            
            if preview_data and preview_data.get('sample_geojson'):
                st.subheader("🔍 Data Preview")
                
                # Show preview stats
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Preview Features", preview_data['feature_count'])
                with col2:
                    st.metric("Total Features", preview_data['total_features'])
                
                # Create map with preview data
                geojson = preview_data['sample_geojson']
                if geojson['features']:
                    # Create simple folium map
                    m = folium.Map(location=[40, -95], zoom_start=4)
                    
                    # Add preview data
                    folium.GeoJson(
                        geojson,
                        style_function=lambda x: {
                            'fillColor': 'green',
                            'color': 'blue',
                            'weight': 1,
                            'fillOpacity': 0.3
                        }
                    ).add_to(m)
                    
                    # Display map
                    st_folium(m, width=700, height=400)
                    
                    # Show feature sample
                    if st.checkbox("Show Feature Details"):
                        st.json(geojson['features'][0] if geojson['features'] else {})
            else:
                st.info("No preview data available for this job")
                
    except Exception as e:
        st.error(f"Error loading preview: {str(e)}")

def main():
    """Main application function"""
    # Initialize session state
    init_session_state()
    
    # Create header
    create_header()
    
    # Sidebar for navigation and AOI input
    with st.sidebar:
        st.header("🎯 Area of Interest (AOI)")
        
        # AOI input method selection
        aoi_method = st.radio(
            "AOI Input Method",
            ["Shapefile Upload", "Bounding Box Coordinates"],
            help="Choose how to define your area of interest"
        )
        
        if aoi_method == "Shapefile Upload":
            st.subheader("📁 Upload Shapefile")
            uploaded_files = st.file_uploader(
                "Choose shapefile components",
                type=['shp', 'shx', 'dbf', 'prj', 'cpg'],
                accept_multiple_files=True,
                help="Upload .shp, .shx, .dbf files (required) and .prj, .cpg files (optional)"
            )
            
            if uploaded_files:
                is_valid, message = validate_shapefile_upload(uploaded_files)
                if is_valid:
                    st.success(message)
                    
                    if st.button("Process Shapefile"):
                        aoi_data, error = process_shapefile_upload(uploaded_files)
                        if aoi_data:
                            st.session_state.uploaded_aoi = aoi_data
                            st.session_state.aoi_bounds = aoi_data['bounds']
                            st.session_state.aoi_geometry = aoi_data['geojson']
                            st.success("Shapefile processed successfully!")
                            st.rerun()
                        else:
                            st.error(error)
                else:
                    st.error(message)
        
        else:  # Bounding Box Coordinates
            st.subheader("📐 Bounding Box")
            
            col1, col2 = st.columns(2)
            with col1:
                min_lon = st.number_input("Min Longitude", value=-105.3, format="%.6f")
                min_lat = st.number_input("Min Latitude", value=39.9, format="%.6f")
            
            with col2:
                max_lon = st.number_input("Max Longitude", value=-105.1, format="%.6f")
                max_lat = st.number_input("Max Latitude", value=40.1, format="%.6f")
            
            if st.button("Set Bounding Box"):
                if min_lon < max_lon and min_lat < max_lat:
                    bounds = {
                        'minx': min_lon,
                        'miny': min_lat,
                        'maxx': max_lon,
                        'maxy': max_lat
                    }
                    st.session_state.aoi_bounds = bounds
                    st.session_state.uploaded_aoi = None
                    st.session_state.aoi_geometry = None
                    st.success("Bounding box set successfully!")
                    st.rerun()
                else:
                    st.error("Invalid coordinates. Ensure min < max for both lat and lon.")
        
        # Display current AOI info
        if st.session_state.uploaded_aoi:
            st.subheader("ℹ️ Current AOI")
            aoi = st.session_state.uploaded_aoi
            st.write(f"**Features:** {aoi['feature_count']}")
            st.write(f"**Area:** {aoi['total_area_km2']} km²")
            st.write(f"**Bounds:** {aoi['bounds']['minx']:.4f}, {aoi['bounds']['miny']:.4f} to {aoi['bounds']['maxx']:.4f}, {aoi['bounds']['maxy']:.4f}")
        elif st.session_state.aoi_bounds:
            st.subheader("ℹ️ Current AOI")
            bounds = st.session_state.aoi_bounds
            st.write(f"**Type:** Bounding Box")
            st.write(f"**Bounds:** {bounds['minx']:.4f}, {bounds['miny']:.4f} to {bounds['maxx']:.4f}, {bounds['maxy']:.4f}")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🗺️ AOI Visualization")
        
        # Display map
        if st.session_state.uploaded_aoi:
            map_obj = create_map(aoi_data=st.session_state.uploaded_aoi)
        elif st.session_state.aoi_bounds:
            map_obj = create_map(bounds=st.session_state.aoi_bounds)
        else:
            map_obj = create_map()
            st.info("👆 Please define an AOI using the sidebar to see it on the map")
        
        st_folium(map_obj, width=700, height=500)
    
    with col2:
        st.subheader("🎮 Quick Actions")
        
        # API connection status
        try:
            health = st.session_state.api_client.health_check()
            st.success("✅ API Connected")
        except:
            st.error("❌ API Disconnected")
            st.stop()
        
        # Load data sources button
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Data Sources"):
                load_data_sources()
        with col2:
            if st.button("🗑️ Clear Selection"):
                # Clear all selection-related session state
                for key in list(st.session_state.keys()):
                    if 'selector' in key or 'selected' in key:
                        del st.session_state[key]
                st.rerun()
        
        # Show current job status
        if st.session_state.current_job_id:
            try:
                job_status = st.session_state.api_client.get_job_status(st.session_state.current_job_id)
                st.write(f"**Current Job:** {st.session_state.current_job_id}")
                st.write(f"**Status:** {job_status['status']}")
            except:
                st.session_state.current_job_id = None
    
    # Data source selection and download
    if st.session_state.aoi_bounds or st.session_state.aoi_geometry:
        # Load data sources if not already loaded
        if not st.session_state.available_sources:
            load_data_sources()
        
        if st.session_state.available_sources:
            source_id, layer_ids, config_options = display_data_source_selection(st.session_state.available_sources)
            
            if source_id and layer_ids:
                st.subheader("🚀 Start Download")
                
                if st.button("Start Download Job", type="primary"):
                    job_id, error = create_download_job(
                        source_id, 
                        layer_ids,
                        config_options=config_options,
                        aoi_bounds=st.session_state.aoi_bounds,
                        aoi_geometry=st.session_state.aoi_geometry
                    )
                    
                    if job_id:
                        st.session_state.current_job_id = job_id
                        st.success(f"Job created: {job_id}")
                        st.rerun()
                    else:
                        st.error(error)
    
    # Monitor current job
    if st.session_state.current_job_id:
        monitor_job_progress(st.session_state.current_job_id)
    
    else:
        # Enhanced AOI Definition Interface
        if st.button("🔄 Switch to Enhanced AOI Drawing"):
            st.session_state.use_enhanced_aoi = True
            st.rerun()
            
        st.info("👆 Please define an AOI and select data sources to start downloading geospatial data")
    
    # Enhanced AOI Drawing Interface (optional alternative)
    if st.session_state.get('use_enhanced_aoi', False):
        st.markdown("---")
        st.header("🎨 Enhanced AOI Drawing Tools")
        
        # Use the enhanced drawing interface
        aoi_geometry, aoi_bounds = display_aoi_drawing_interface()
        
        if aoi_geometry and aoi_bounds:
            st.session_state.aoi_geometry = aoi_geometry
            st.session_state.aoi_bounds = aoi_bounds
            st.session_state.use_enhanced_aoi = False  # Switch back to main interface
            st.success("✅ AOI defined using enhanced drawing tools!")
            st.rerun()
    
    # CAD Export Section
    if st.session_state.current_job_id:
        st.markdown("---")
        st.subheader("🛠️ CAD Export Options")
        
        if st.button("📐 Export to CAD (DXF)"):
            try:
                with st.spinner("Exporting to CAD format..."):
                    from pathlib import Path
                    
                    # Get job directory
                    job_dir = Path(f"output/results/{st.session_state.current_job_id}")
                    
                    if job_dir.exists():
                        # Export to CAD
                        cad_files = export_job_to_cad_formats(st.session_state.current_job_id, job_dir)
                        
                        if cad_files.get('dxf'):
                            st.success("✅ CAD export completed!")
                            
                            # Provide download link
                            with open(cad_files['dxf'], 'rb') as f:
                                st.download_button(
                                    label="📥 Download DXF File",
                                    data=f.read(),
                                    file_name=f"{st.session_state.current_job_id}_export.dxf",
                                    mime="application/dxf"
                                )
                        else:
                            st.error("❌ CAD export failed. No vector data found in job results.")
                    else:
                        st.error("❌ Job results not found.")
                        
            except Exception as e:
                st.error(f"❌ CAD export error: {str(e)}")

if __name__ == "__main__":
    main()