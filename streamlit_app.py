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
import math
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import folium
from streamlit_folium import st_folium

# Import our custom modules
from api_client import GeospatialAPIClient
from streamlit_config import Config
from unified_map import display_unified_map_interface
from cad_export import export_job_to_cad_formats, create_cad_export_zip

# Configure page
st.set_page_config(
    page_title="Geospatial Data Downloader",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add keyboard shortcuts
st.markdown("""
<script>
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + R: Refresh data sources
    if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
        e.preventDefault();
        // Trigger refresh (would need JS bridge in real implementation)
    }
    // Escape: Clear selection
    if (e.key === 'Escape') {
        // Clear selection logic
    }
});
</script>
""", unsafe_allow_html=True)

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
    
    if 'persistent_downloads' not in st.session_state:
        st.session_state.persistent_downloads = {}

def create_header():
    """Create the application header with quick stats"""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown('<h1 class="main-header">🗺️ Geospatial Data Downloader</h1>', unsafe_allow_html=True)
        st.markdown(
            '<p class="sub-header">Professional geospatial data acquisition from FEMA, USGS, and NOAA sources</p>', 
            unsafe_allow_html=True
        )
    
    with col2:
        # Reserved for future use
        st.empty()

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

def validate_aoi_size(area_km2: float, area_acres: float = None) -> tuple[bool, str]:
    """Validate AOI size against limits"""
    MIN_AREA_ACRES = 0.1  # 0.1 acre minimum
    MAX_AREA_KM2 = 10000  # 10,000 km² maximum
    
    min_area_km2 = MIN_AREA_ACRES / 247.105  # Convert acres to km²
    if area_acres is None:
        area_acres = area_km2 * 247.105
    
    if area_km2 < min_area_km2:
        return False, f"AOI too small! Minimum area: {MIN_AREA_ACRES} acres ({min_area_km2:.6f} km²). Current: {area_acres:.3f} acres."
        
    if area_km2 > MAX_AREA_KM2:
        return False, f"AOI too large! Maximum area: {MAX_AREA_KM2:,} km². Current: {area_km2:.1f} km²."
    
    return True, "Valid AOI size"

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
            
            # Calculate area properly for validation
            gdf_proj = gdf.to_crs('EPSG:3857')  # Project for accurate area calculation
            area_m2 = gdf_proj.geometry.area.sum()
            area_km2 = area_m2 / 1_000_000
            area_acres = area_km2 * 247.105
            
            # Validate AOI size
            is_valid, message = validate_aoi_size(area_km2, area_acres)
            if not is_valid:
                return None, message
            
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
            union_geom = gdf.geometry.union_all()
            
            return {
                'gdf': gdf,
                'bounds': aoi_bounds,
                'geojson': geojson,
                'union_geometry': union_geom,
                'feature_count': len(gdf),
                'total_area_km2': round(area_km2, 3)
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

def display_simple_data_selection(sources):
    """Display simplified data source selection - multiple datasets allowed"""
    st.subheader("📊 Select Data Sources")
    
    if not sources:
        st.warning("No data sources available. Please check API connection.")
        return None, None, {}
    
    # Build available source options
    source_options = {}
    for source_id, source_info in sources.items():
        if source_info:  # Skip None sources
            if source_id == 'fema':
                source_options["🌊 FEMA - All Flood Risk Data"] = {
                    'id': source_id,
                    'info': source_info,
                    'description': "Complete FEMA flood hazard dataset (all layers)"
                }
            elif source_id == 'usgs_lidar':
                source_options["⛰️ USGS - Elevation Data"] = {
                    'id': source_id,
                    'info': source_info,
                    'description': "USGS LiDAR digital elevation models"
                }
            elif source_id == 'noaa_atlas14':
                source_options["🌧️ NOAA - All Precipitation Data"] = {
                    'id': source_id,
                    'info': source_info,
                    'description': "Complete NOAA Atlas 14 precipitation dataset"
                }
    
    if not source_options:
        st.warning("No data sources are currently available.")
        return None, None, {}
    
    # Multiple selection with checkboxes
    st.write("**Select one or more datasets to download:**")
    
    selected_sources = []
    all_layer_ids = []
    all_config_options = {}
    
    for source_name, source_data in source_options.items():
        source_id = source_data['id']
        source_info = source_data['info']
        
        # Checkbox for each source
        if st.checkbox(source_name, help=source_data['description']):
            selected_sources.append(source_id)
            
            # Add all layers from this source
            layer_ids = list(source_info['layers'].keys())
            all_layer_ids.extend(layer_ids)
            
            # Show layer count
            st.write(f"  📋 {len(layer_ids)} layers included")
            
            # USGS-specific contour generation options
            if source_id == 'usgs_lidar':
                with st.container():
                    col_spacer, col_content = st.columns([0.1, 0.9])
                    with col_content:
                        st.markdown("⛰️ **Elevation Options:**")
                        
                        generate_contours = st.checkbox(
                            "Generate Contour Lines (Shapefile + DXF)",
                            value=False,
                            help="Generate contour line shapefiles and DXF files from the DEM data for CAD use",
                            key=f"contours_{source_id}"
                        )
                    
                        if generate_contours:
                            contour_interval = st.number_input(
                                "Contour Interval (feet)",
                                min_value=1,
                                max_value=100,
                                value=5,
                                step=1,
                                help="Vertical interval between contour lines in feet",
                                key=f"interval_{source_id}"
                            )
                            all_config_options['contour_interval'] = contour_interval
                            st.write(f"📏 Contours every {contour_interval} feet")
    
    if not selected_sources:
        return None, None, {}
    
    # Summary of selection
    if len(selected_sources) > 1:
        st.success(f"✅ Selected {len(selected_sources)} datasets with {len(all_layer_ids)} total layers")
        
        # Show what's included
        with st.expander("📋 Selection Summary"):
            for source_id in selected_sources:
                source_info = sources[source_id]
                st.write(f"**{source_id.upper()}**: {len(source_info['layers'])} layers")
    else:
        st.info(f"📝 Selected: {selected_sources[0].upper()} ({len(all_layer_ids)} layers)")
    
    # For the API, we'll need to create separate jobs for each source
    # Return the first source for now, but we'll modify the job creation to handle multiple
    return selected_sources, all_layer_ids, all_config_options

def create_download_jobs(source_ids, sources_dict, config_options=None, aoi_bounds=None, aoi_geometry=None):
    """Create download jobs for multiple sources"""
    if isinstance(source_ids, str):
        # Single source - use original logic
        return create_single_download_job(source_ids, sources_dict, config_options, aoi_bounds, aoi_geometry)
    
    # Multiple sources - create separate jobs
    job_ids = []
    errors = []
    
    with st.spinner(f"Creating {len(source_ids)} download jobs... (This may take up to 2 minutes for NOAA data)"):
        for source_id in source_ids:
            try:
                source_info = sources_dict[source_id]
                layer_ids = list(source_info['layers'].keys())
                
                job_data = {
                    'downloader_id': source_id,
                    'layer_ids': layer_ids,
                    'config': config_options if source_id == 'usgs_lidar' else {}
                }
                
                if aoi_bounds:
                    job_data['aoi_bounds'] = aoi_bounds
                elif aoi_geometry:
                    job_data['aoi_geometry'] = aoi_geometry
                
                # Show individual progress for slow downloaders
                if source_id == 'noaa_atlas14':
                    st.info(f"⏳ Creating NOAA Atlas 14 job... (this can take 1-2 minutes)")
                
                job_response = st.session_state.api_client.create_job(job_data)
                job_ids.append({
                    'job_id': job_response['job_id'],
                    'source_id': source_id,
                    'layer_count': len(layer_ids)
                })
                
                st.success(f"✅ {source_id.upper()} job created successfully")
                
            except Exception as e:
                error_msg = str(e)
                if "timed out" in error_msg.lower():
                    errors.append(f"{source_id}: Job creation timed out - try selecting {source_id.upper()} alone or check if the service is available")
                else:
                    errors.append(f"{source_id}: {error_msg}")
    
    if errors:
        return None, f"Failed to create some jobs: {'; '.join(errors)}"
    
    return job_ids, None

def create_single_download_job(source_id, sources_dict, config_options=None, aoi_bounds=None, aoi_geometry=None):
    """Create single download job - original version"""
    try:
        with st.spinner("Creating download job..."):
            if isinstance(source_id, list):
                source_id = source_id[0]  # Take first if list
            
            source_info = sources_dict[source_id]
            layer_ids = list(source_info['layers'].keys())
            
            job_data = {
                'downloader_id': source_id,
                'layer_ids': layer_ids,
                'config': config_options or {}
            }
            
            if aoi_bounds:
                job_data['aoi_bounds'] = aoi_bounds
            elif aoi_geometry:
                job_data['aoi_geometry'] = aoi_geometry
            
            job_response = st.session_state.api_client.create_job(job_data)
            return job_response['job_id'], None
            
    except Exception as e:
        return None, f"Failed to create job: {str(e)}"

def monitor_job_progress(job_id):
    """Monitor and display job progress - original version"""
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
                status_text.info("⏳ Job pending...")
            elif status == 'running':
                # Use progress from API if available
                progress_data = job_status.get('progress', {})
                if 'percentage' in progress_data:
                    progress_val = min(progress_data['percentage'] / 100, 0.95)
                else:
                    progress_val = 0.5
                progress_bar.progress(progress_val)
                status_text.info("🔄 Processing data...")
            elif status == 'completed':
                progress_bar.progress(100)
                status_text.success("✅ Job completed successfully!")
                
                # Display results without balloons
                with status_container:
                    display_job_results(job_status)
                break
            elif status == 'failed':
                progress_bar.progress(0)
                error_msg = job_status.get('error_message', 'Unknown error')
                status_text.error(f"❌ Job failed: {error_msg}")
                break
            
            time.sleep(1)
            attempt += 1
            
        except Exception as e:
            st.error(f"Error monitoring job: {str(e)}")
            break
    
    if attempt >= max_attempts:
        st.warning("Job monitoring timed out. Please check job status manually.")

def display_job_results(job_status):
    """Display job results and download options - original working version"""
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
    
    # Download options - original working version
    if result_summary['has_download']:
        st.subheader("💾 Download Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📦 Download ZIP", type="primary"):
                download_url = f"{Config.API_BASE_URL}{result_summary['download_url']}"
                st.markdown(f'<a href="{download_url}" target="_blank">Click here to download</a>', unsafe_allow_html=True)
        
        with col2:
            if st.button("🔍 View Data Preview"):
                display_data_preview(job_status['job_id'])
        
        with col3:
            if st.button("📋 Download Summary"):
                download_url = f"{Config.API_BASE_URL}{result_summary['summary_url']}"
                st.markdown(f'<a href="{download_url}" target="_blank">Click here to download summary</a>', unsafe_allow_html=True)

def display_data_preview(job_id):
    """Display data preview - original version"""
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



def display_job_history():
    """Display recent job history"""
    if 'job_history' not in st.session_state:
        st.session_state.job_history = []
    
    if st.session_state.job_history:
        with st.expander("📊 Recent Downloads"):
            for job in st.session_state.job_history[-5:]:  # Show last 5
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**{job['source_id']}** - {len(job['layer_ids'])} layers")
                with col2:
                    st.write(job['status'])
                with col3:
                    if st.button(f"🔄 Repeat", key=f"repeat_{job['job_id']}"):
                        # Implement repeat functionality
                        pass

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
    """Display job results and download options with persistent links"""
    result_summary = job_status.get('result_summary')
    if not result_summary:
        st.warning("No result summary available")
        return
    
    job_id = job_status['job_id']
    
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
    
    # Persistent download options
    if result_summary['has_download']:
        st.subheader("💾 Download Options")
        
        # Store download URLs in session state immediately
        if job_id not in st.session_state.persistent_downloads:
            st.session_state.persistent_downloads[job_id] = {
                'zip_url': f"{Config.API_BASE_URL}{result_summary['download_url']}",
                'summary_url': f"{Config.API_BASE_URL}{result_summary.get('summary_url', '')}",
                'job_name': f"Job_{job_id}",
                'created_at': time.time()
            }
        
        # Display persistent download links
        download_info = st.session_state.persistent_downloads[job_id]
        
        st.success("✅ **Your download links are ready and will remain available:**")
        
        # Main ZIP download - always visible
        st.markdown(f"""
        ### 📦 Main Dataset Download
        **[Download Complete Dataset ZIP]({download_info['zip_url']})**
        
        *Right-click and "Save As" if the file opens in browser*
        """)
        
        # Summary download if available
        if download_info['summary_url']:
            st.markdown(f"""
            ### 📋 Summary Report
            **[Download Summary Report]({download_info['summary_url']})**
            """)
        
        # Additional options in columns
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗺️ View Data Preview", key=f"preview_{job_id}"):
                display_data_preview(job_id)
        
        with col2:
            if st.button("📋 Copy Download URL", key=f"copy_{job_id}"):
                st.code(download_info['zip_url'])
                st.info("💡 Copy the URL above to download later")

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


def has_aoi() -> bool:
    """Check if user has defined an AOI (either drawn or uploaded)"""
    return (
        (st.session_state.get('aoi_geometry') is not None) or 
        (st.session_state.get('aoi_bounds') is not None) or 
        (st.session_state.get('uploaded_aoi') is not None)
    )


def get_aoi_geometry_and_bounds() -> tuple:
    """Get current AOI geometry and bounds from session state"""
    
    # Check for uploaded AOI first (prioritize uploaded over potentially mixed state)
    if st.session_state.get('uploaded_aoi'):
        aoi_data = st.session_state.uploaded_aoi
        if 'geojson' in aoi_data and 'bounds' in aoi_data:
            geometry = aoi_data['geojson']['features'][0]['geometry']
            bounds = aoi_data['bounds']
            return geometry, bounds
    
    # Check for drawn AOI (geometry should be just the geometry object)
    if st.session_state.get('aoi_geometry') and st.session_state.get('aoi_bounds'):
        aoi_geometry = st.session_state.aoi_geometry
        
        # Handle case where aoi_geometry might be a GeoJSON FeatureCollection (from shapefile)
        if isinstance(aoi_geometry, dict):
            if aoi_geometry.get('type') == 'FeatureCollection':
                # Extract geometry from feature collection
                if 'features' in aoi_geometry and len(aoi_geometry['features']) > 0:
                    geometry = aoi_geometry['features'][0]['geometry']
                else:
                    return None, None
            elif aoi_geometry.get('type') in ['Polygon', 'MultiPolygon', 'Point', 'LineString', 'MultiPoint', 'MultiLineString']:
                # Already a geometry object
                geometry = aoi_geometry
            else:
                return None, None
        else:
            return None, None
            
        return geometry, st.session_state.aoi_bounds
    
    return None, None


def generate_location_map_exhibit_ui():
    """Handle the UI for location map exhibit generation"""
    geometry, bounds = get_aoi_geometry_and_bounds()
    
    if not geometry or not bounds:
        st.error("❌ No valid AOI found. Please draw an AOI or upload a shapefile first.")
        return
    
    with st.spinner("🗺️ Generating location map exhibit..."):
        from unified_map import generate_location_map_exhibit
        
        # Generate the location map exhibit
        location_map_path = generate_location_map_exhibit(geometry, bounds)
        
        if location_map_path:
            # Store in session state
            st.session_state.location_map_exhibit = location_map_path
            st.success("📍 **Location map exhibit generated successfully!**")
            
            # Provide immediate download button
            with open(location_map_path, 'rb') as pdf_file:
                st.download_button(
                    label="📥 Download Location Map Exhibit (PDF)",
                    data=pdf_file.read(),
                    file_name=f"location_map_exhibit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    help="Professional location map showing your Area of Interest",
                    use_container_width=True
                )
        else:
            st.error("❌ **Failed to generate location map exhibit.** Please check your AOI and try again.")


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
                    # Calculate area for validation
                    width_deg = max_lon - min_lon
                    height_deg = max_lat - min_lat
                    # Rough area calculation (degrees to km²)
                    area_km2 = width_deg * height_deg * 111.32 * 111.32 * abs(math.cos(math.radians((min_lat + max_lat) / 2)))
                    
                    # Validate area
                    is_valid, message = validate_aoi_size(area_km2)
                    if not is_valid:
                        st.error(message)
                        return
                    
                    bounds = {
                        'minx': min_lon,
                        'miny': min_lat,
                        'maxx': max_lon,
                        'maxy': max_lat
                    }
                    st.session_state.aoi_bounds = bounds
                    st.session_state.uploaded_aoi = None
                    st.session_state.aoi_geometry = None
                    
                    # Show area-based warning
                    area_acres = area_km2 * 247.105
                    if area_km2 >= 2000:
                        st.warning("🚨 **Very large area** - DEM downloads may take 1+ hours.")
                    elif area_km2 >= 500:
                        st.warning("⚠️ **Large area** - DEM downloads may take 30-60 minutes.")
                    elif area_km2 >= 100:
                        st.info("⏱️ **Medium area** - DEM downloads may take 10-20 minutes.")
                    else:
                        st.info("✅ **Small to medium area** - Fast downloads expected.")
                    
                    st.success(f"Bounding box set successfully! Area: {area_km2:.3f} km² ({area_acres:.1f} acres)")
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
    
    
    # Optional Project Information Section
    with st.expander("📋 Project Information (Optional)", expanded=False):
        st.markdown("**Customize your location map exhibit with project details:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            project_name = st.text_input(
                "Project Name",
                value=st.session_state.get('project_name', ''),
                placeholder="Geospatial Data Analysis",
                help="Name of your project or study area"
            )
            
            client_name = st.text_input(
                "Client/Organization",
                value=st.session_state.get('client_name', ''),
                placeholder="Data User",
                help="Organization or client name"
            )
        
        with col2:
            project_number = st.text_input(
                "Project Number",
                value=st.session_state.get('project_number', ''),
                placeholder=f"GDA-{datetime.now().strftime('%Y%m%d')}",
                help="Project number or identifier"
            )
            
            drawn_by = st.text_input(
                "Drawn By",
                value=st.session_state.get('drawn_by', ''),
                placeholder="Auto-Generated",
                help="Your initials or name (optional)",
                max_chars=20
            )
        
        # Store in session state
        st.session_state.project_name = project_name
        st.session_state.client_name = client_name
        st.session_state.project_number = project_number
        st.session_state.drawn_by = drawn_by
        
        if any([project_name, client_name, project_number, drawn_by]):
            st.success("✅ Project information saved - will be included in location map exhibits")

    # Main content area with unified map
    st.subheader("🗺️ Interactive Map Interface")
    
    # Display unified map interface
    new_geometry, new_bounds = display_unified_map_interface()
    
    # Handle new AOI from map drawing (prevent infinite loop)
    if new_geometry and new_bounds:
        st.session_state.aoi_geometry = new_geometry
        st.session_state.aoi_bounds = new_bounds
        # Clear uploaded AOI if user draws new one
        if 'uploaded_aoi' in st.session_state:
            del st.session_state.uploaded_aoi
        # Don't rerun immediately - let user see the results first
    
    # Location Map Exhibit Generation Button (only show if AOI exists)
    if has_aoi():
        st.markdown("---")  # Visual separator
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("📍 Generate Location Map Exhibit", 
                        help="Create a professional location map PDF showing your Area of Interest",
                        type="secondary",
                        use_container_width=True):
                generate_location_map_exhibit_ui()
    
    # Sidebar with enhanced quick actions
    with st.sidebar:
        st.header("🎮 Quick Actions")
        
        # API connection status
        try:
            health = st.session_state.api_client.health_check()
            st.success("✅ API Connected")
        except Exception as e:
            st.error("❌ API Disconnected")
            st.error(f"Error: {str(e)}")
            st.stop()
        
        # Quick action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh", help="Reload data sources (Ctrl+R)"):
                load_data_sources()
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear", help="Clear all selections (Esc)"):
                # Clear all selection-related session state
                keys_to_clear = [k for k in st.session_state.keys() 
                               if any(x in k for x in ['selector', 'selected', 'aoi_', 'current_job'])]
                for key in keys_to_clear:
                    del st.session_state[key]
                st.rerun()
        
        # Show recent activity
        if st.session_state.get('last_successful_download'):
            recent = st.session_state.last_successful_download
            st.write("**Last Download:**")
            st.write(f"Source: {recent['source_id']}")
            st.write(f"Layers: {len(recent['layer_ids'])}")
            
            if st.button("🔄 Repeat Last Download"):
                # Simple repeat functionality - could be enhanced later
                st.info(f"Last download was {recent['source_id']} with {len(recent['layer_ids'])} layers")
    
    # Enhanced data source selection and download
    if st.session_state.aoi_bounds or st.session_state.aoi_geometry or st.session_state.uploaded_aoi:
        # Load data sources if not already loaded
        if not st.session_state.available_sources:
            load_data_sources()
        
        if st.session_state.available_sources:
            # Simple data source selection (now supports multiple)
            selected_sources, layer_ids, config_options = display_simple_data_selection(st.session_state.available_sources)
            
            if selected_sources and layer_ids:
                st.subheader("🚀 Start Download")
                
                # Show what will be downloaded
                if isinstance(selected_sources, list) and len(selected_sources) > 1:
                    st.write(f"**Ready to download {len(selected_sources)} datasets:**")
                    for source_id in selected_sources:
                        source_info = st.session_state.available_sources[source_id]
                        st.write(f"  • {source_id.upper()}: {len(source_info['layers'])} layers")
                
                if st.button("Start Download Job(s)", type="primary"):
                    jobs_result, error = create_download_jobs(
                        selected_sources,
                        st.session_state.available_sources,
                        config_options=config_options,
                        aoi_bounds=st.session_state.aoi_bounds,
                        aoi_geometry=st.session_state.aoi_geometry
                    )
                    
                    if jobs_result:
                        if isinstance(jobs_result, list):
                            # Multiple jobs created
                            st.session_state.current_jobs = jobs_result
                            st.success(f"✅ Created {len(jobs_result)} download jobs!")
                            for job in jobs_result:
                                st.write(f"  • {job['source_id'].upper()}: Job {job['job_id']}")
                        else:
                            # Single job created (backwards compatibility)
                            st.session_state.current_job_id = jobs_result
                            st.success(f"Job created: {jobs_result}")
                        st.rerun()
                    else:
                        st.error(error)
    
    # Monitor current jobs
    if st.session_state.get('current_jobs'):
        monitor_multiple_jobs(st.session_state.current_jobs)
    elif st.session_state.get('current_job_id'):
        monitor_job_progress(st.session_state.current_job_id)
    else:
        # Help and tutorial for new users
        show_tutorials = st.session_state.get('show_tutorials', True)
        if show_tutorials:
            st.info("👋 **Welcome!** Define an Area of Interest (AOI) using the sidebar or by drawing on the map above to get started.")
            
            with st.expander("📖 Quick Tutorial", expanded=False):
                st.markdown("""
                **Getting Started:**
                1. 📍 **Define your AOI** - Upload a shapefile, enter coordinates, or draw on the map
                2. 📊 **Select data sources** - Choose from FEMA flood data, USGS elevation, or NOAA precipitation
                3. 🚀 **Download** - Start your job and get automatic downloads
                
                **Pro Tips:**
                - Choose appropriate data sources based on your analysis needs
                - Try keyboard shortcuts: Ctrl+R (refresh), Esc (clear)
                - Use the enhanced data selection interface for better organization
                """)
        
        # Show available data sources summary
        if st.session_state.available_sources:
            st.subheader("📋 Available Data Sources")
            source_count = len([s for s in st.session_state.available_sources.values() if s])
            st.write(f"**{source_count} data sources ready** - Define an AOI to begin selection")
            
            # Quick preview of available sources
            cols = st.columns(min(3, source_count))
            for i, (source_id, source_info) in enumerate(st.session_state.available_sources.items()):
                if source_info and i < 3:
                    with cols[i]:
                        st.write(f"**{source_info['name']}**")
                        st.write(f"{len(source_info['layers'])} layers")
                        st.write(f"_{source_info['description'][:50]}..._")
    
    # Display persistent downloads section (always visible if downloads exist)
    display_persistent_downloads()

# Add footer with tips
def display_footer():
    """Display clean footer"""
    pass

def monitor_multiple_jobs(jobs_list):
    """Monitor multiple jobs simultaneously"""
    st.subheader(f"⏳ Monitoring {len(jobs_list)} Download Jobs")
    
    # Create containers for each job
    job_containers = {}
    for job in jobs_list:
        job_id = job['job_id']
        source_id = job['source_id']
        
        with st.container():
            st.write(f"**{source_id.upper()}** (Job: {job_id})")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                progress_bar = st.progress(0)
            with col2:
                status_text = st.empty()
            
            job_containers[job_id] = {
                'progress_bar': progress_bar,
                'status_text': status_text,
                'source_id': source_id,
                'completed': False
            }
    
    # Monitor all jobs
    max_attempts = 300
    attempt = 0
    completed_jobs = []
    
    while attempt < max_attempts and len(completed_jobs) < len(jobs_list):
        all_completed = True
        
        for job in jobs_list:
            job_id = job['job_id']
            if job_id in completed_jobs:
                continue
                
            try:
                job_status = st.session_state.api_client.get_job_status(job_id)
                status = job_status['status']
                container = job_containers[job_id]
                
                if status == 'pending':
                    container['progress_bar'].progress(10)
                    container['status_text'].write("⏳ Pending")
                    all_completed = False
                elif status == 'running':
                    progress_data = job_status.get('progress', {})
                    if 'percentage' in progress_data:
                        progress_val = min(progress_data['percentage'] / 100, 0.95)
                    else:
                        progress_val = 0.5
                    container['progress_bar'].progress(progress_val)
                    container['status_text'].write("🔄 Running")
                    all_completed = False
                elif status == 'completed':
                    container['progress_bar'].progress(100)
                    container['status_text'].write("✅ Complete")
                    if job_id not in completed_jobs:
                        completed_jobs.append(job_id)
                        # Store persistent download for this job
                        result_summary = job_status.get('result_summary')
                        if result_summary and result_summary.get('has_download'):
                            if job_id not in st.session_state.persistent_downloads:
                                st.session_state.persistent_downloads[job_id] = {
                                    'zip_url': f"{Config.API_BASE_URL}{result_summary['download_url']}",
                                    'summary_url': f"{Config.API_BASE_URL}{result_summary.get('summary_url', '')}",
                                    'job_name': f"{container['source_id'].upper()}_Job_{job_id}",
                                    'source_id': container['source_id'],
                                    'created_at': time.time()
                                }
                elif status == 'failed':
                    container['progress_bar'].progress(0)
                    error_msg = job_status.get('error_message', 'Unknown error')
                    container['status_text'].write(f"❌ Failed")
                    st.error(f"{container['source_id'].upper()} failed: {error_msg}")
                    if job_id not in completed_jobs:
                        completed_jobs.append(job_id)  # Don't retry failed jobs
                        
            except Exception as e:
                container['status_text'].write(f"❌ Error")
                st.error(f"Error monitoring {container['source_id']}: {str(e)}")
        
        if all_completed:
            break
            
        time.sleep(2)
        attempt += 1
    
    # Summary
    if len(completed_jobs) == len(jobs_list):
        st.success(f"🎉 All {len(jobs_list)} jobs completed!")
        # Clear the jobs from session state
        del st.session_state.current_jobs
    elif attempt >= max_attempts:
        st.warning("Some jobs are still running. Please check back later.")

def get_source_info(source_id):
    """Get formatted information for each data source"""
    source_map = {
        'fema': {
            'name': 'FEMA Flood Risk Data',
            'icon': '🌊',
            'color': '#1f77b4',
            'description': 'National Flood Hazard Layer (NFHL)',
            'typical_layers': ['Flood Zones', 'Base Flood Elevations', 'Flood Insurance Rate Maps']
        },
        'usgs_lidar': {
            'name': 'USGS Elevation Data', 
            'icon': '⛰️',
            'color': '#2ca02c',
            'description': '3D Elevation Program (3DEP)',
            'typical_layers': ['Digital Elevation Models', 'Contour Lines', 'LiDAR Point Clouds']
        },
        'noaa_atlas14': {
            'name': 'NOAA Precipitation Data',
            'icon': '🌧️', 
            'color': '#ff7f0e',
            'description': 'Precipitation-Frequency Atlas',
            'typical_layers': ['Precipitation Maps', 'Frequency Analysis', 'Statistical Reports']
        }
    }
    
    return source_map.get(source_id, {
        'name': f'{source_id.upper()} Data',
        'icon': '📦',
        'color': '#666666', 
        'description': 'Geospatial Dataset',
        'typical_layers': ['Data Layers']
    })


def display_persistent_downloads():
    """Display all available persistent downloads with enhanced UI"""
    if not st.session_state.persistent_downloads:
        return
    
    st.subheader("📥 Available Downloads")
    
    # Sort downloads by creation time (newest first)
    downloads = sorted(
        st.session_state.persistent_downloads.items(),
        key=lambda x: x[1]['created_at'],
        reverse=True
    )
    
    # Display count
    st.write(f"**{len(downloads)}** completed download{'s' if len(downloads) != 1 else ''} ready:")
    st.write("")  # Add some spacing
    
    for job_id, download_info in downloads:
        # Get source information
        source_id = download_info.get('source_id', 'unknown')
        source_info = get_source_info(source_id)
        
        # Create timestamp
        created_time = datetime.fromtimestamp(download_info['created_at'])
        time_str = created_time.strftime("%B %d, %Y at %I:%M %p")
        
        # Custom card styling
        with st.container():
            # Header section with source info
            col_icon, col_title = st.columns([0.5, 9.5])
            
            with col_icon:
                st.markdown(f"<div style='font-size: 2.5rem; text-align: center;'>{source_info['icon']}</div>", 
                           unsafe_allow_html=True)
            
            with col_title:
                st.markdown(f"""
                <div style='padding: 0;'>
                    <h4 style='margin: 0; color: {source_info['color']}; font-size: 1.2rem;'>{source_info['name']}</h4>
                    <p style='margin: 2px 0; color: #666; font-size: 0.9rem;'>{source_info['description']}</p>
                    <p style='margin: 2px 0; color: #888; font-size: 0.8rem;'>Downloaded on {time_str}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Add visual separation
            st.markdown("<div style='margin: 15px 0; border-top: 1px solid #e0e0e0;'></div>", 
                       unsafe_allow_html=True)
            
            # Action buttons section  
            col1, col2, col3, col4 = st.columns([2.5, 1.2, 1.2, 1.1])
            
            with col1:
                # Main download button (styled as primary action)
                st.markdown(f"""
                <a href="{download_info['zip_url']}" 
                   style="display: inline-block; padding: 8px 16px; background: linear-gradient(90deg, {source_info['color']}, {source_info['color']}aa); 
                          color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin-right: 10px;">
                    📥 Download ZIP
                </a>
                """, unsafe_allow_html=True)
            
            with col2:
                # Copy URL button
                if st.button("📋 Copy URL", key=f"copy_persistent_{job_id}", 
                           help="Copy download URL to clipboard"):
                    st.code(download_info['zip_url'], language="")
            
            with col3:
                # Info button (show technical details)
                if st.button("ℹ️ Details", key=f"info_persistent_{job_id}",
                           help="Show technical information"):
                    with st.expander("📋 Technical Details", expanded=True):
                        st.write(f"**Job ID:** `{job_id}`")
                        st.write(f"**Data Source:** {source_info['name']}")
                        st.write(f"**Download URL:** {download_info['zip_url']}")
                        if 'summary_url' in download_info and download_info['summary_url']:
                            st.write(f"**Summary Report:** {download_info['summary_url']}")
                        st.write(f"**Created:** {time_str}")
            
            with col4:
                # Remove button
                if st.button("🗑️ Remove", key=f"delete_persistent_{job_id}", 
                           help="Remove from list (files remain available on server)"):
                    del st.session_state.persistent_downloads[job_id]
                    st.rerun()
            
            # Bottom spacing
            st.markdown("<div style='margin: 25px 0;'></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
    
    # Display footer
    display_footer()