"""
Unified Map Interface for Geospatial Data Downloader
===================================================

Single map component that handles both AOI visualization and interactive drawing.
Replaces the dual-map system with a streamlined, always-visible interface.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from folium.plugins import Draw, MeasureControl, MousePosition
import logging
from datetime import datetime
import os
from utils.location_map_exhibit import LocationMapGenerator

logger = logging.getLogger(__name__)


def generate_location_map_exhibit(geometry: Dict, bounds: Dict) -> Optional[str]:
    """
    Generate a location map exhibit for the given AOI geometry
    
    Args:
        geometry: GeoJSON geometry dict
        bounds: Bounds dictionary with minx, miny, maxx, maxy
        
    Returns:
        Path to generated location map PDF, or None if failed
    """
    try:
        # Create temporary GeoDataFrame from geometry
        from shapely.geometry import shape
        
        # Convert geometry dict to shapely geometry
        shapely_geom = shape(geometry)
        
        # Create GeoDataFrame
        aoi_gdf = gpd.GeoDataFrame([1], geometry=[shapely_geom], crs='EPSG:4326')
        
        # Get project info from session state with smart defaults
        import streamlit as st
        
        # Smart defaults
        default_project_name = "Geospatial Data Analysis"
        default_project_number = f"GDA-{datetime.now().strftime('%Y%m%d')}"
        default_client = "Data User"
        default_drawn_by = "Auto-Generated"
        
        # Use user input or defaults
        project_info = {
            'name': st.session_state.get('project_name') or default_project_name,
            'number': st.session_state.get('project_number') or default_project_number,
            'client': st.session_state.get('client_name') or default_client,
            'date': datetime.now().strftime('%m/%d/%Y'),
            'drawn_by': st.session_state.get('drawn_by') or default_drawn_by
        }
        
        # Create output path in a temp directory or session-specific location
        output_dir = tempfile.gettempdir()
        output_filename = f"location_map_exhibit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = os.path.join(output_dir, output_filename)
        
        # Generate location map
        map_generator = LocationMapGenerator()
        success = map_generator.generate_location_map(
            site_boundary=aoi_gdf,
            project_info=project_info,
            output_path=output_path,
            base_map_type="satellite",
            include_vicinity=True
        )
        
        if success and os.path.exists(output_path):
            logger.info(f"Location map exhibit generated: {output_path}")
            return output_path
        else:
            logger.warning("Location map exhibit generation failed")
            return None
            
    except Exception as e:
        logger.error(f"Error generating location map exhibit: {e}")
        return None


class UnifiedMapInterface:
    """Unified map interface combining viewing and drawing functionality"""
    
    def __init__(self):
        self.default_center = [39.8283, -98.5795]  # Geographic center of USA
        self.default_zoom = 4
        
    def create_unified_map(self, aoi_data=None, mode="view", allow_drawing=True) -> folium.Map:
        """
        Create unified map with both viewing and drawing capabilities
        
        Args:
            aoi_data: Existing AOI data to display
            mode: "view" or "draw" mode
            allow_drawing: Whether to enable drawing tools (enforces single AOI policy)
            
        Returns:
            folium.Map: Unified map with appropriate tools
        """
        # Determine map center and zoom
        if aoi_data and 'bounds' in aoi_data:
            bounds = aoi_data['bounds']
            center_lat = (bounds['miny'] + bounds['maxy']) / 2
            center_lon = (bounds['minx'] + bounds['maxx']) / 2
            zoom = 10
        else:
            center_lat, center_lon = self.default_center
            zoom = self.default_zoom
        
        # Create base map with OpenStreetMap as default
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom,
            tiles='OpenStreetMap'
        )
        
        # Add multiple tile layers
        self._add_tile_layers(m)
        
        # Add drawing tools only if in draw mode AND drawing is allowed (no existing AOI)
        if mode == "draw" and allow_drawing:
            self._add_drawing_tools(m)
        
        # Add measurement and position tools
        self._add_utility_tools(m)
        
        # Add existing AOI if provided
        if aoi_data:
            self._add_aoi_to_map(m, aoi_data)
        
        # Add layer control
        folium.LayerControl(position='topright').add_to(m)
        
        return m
    
    def _add_tile_layers(self, m: folium.Map):
        """Add multiple tile layer options"""
        # Satellite imagery
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satellite',
            overlay=False,
            control=True
        ).add_to(m)
        
        # Topographic
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Topographic',
            overlay=False,
            control=True
        ).add_to(m)
        
    
    def _add_drawing_tools(self, m: folium.Map):
        """Add interactive drawing tools - only when no AOI exists"""
        draw = Draw(
            export=True,
            position='topleft',
            draw_options={
                'polyline': False,  # Disable line drawing
                'polygon': True,
                'circle': True, 
                'rectangle': True,
                'marker': False,  # Disable markers
                'circlemarker': False,
            },
            edit_options={
                'poly': False,  # Disable editing existing shapes
                'remove': False,  # Disable removing shapes 
                'edit': False   # Disable all editing
            }
        )
        draw.add_to(m)
    
    def _add_utility_tools(self, m: folium.Map):
        """Add measurement and coordinate display tools"""
        # Measurement tool
        measure_control = MeasureControl(
            position='topleft',
            primary_length_unit='kilometers',
            secondary_length_unit='miles',
            primary_area_unit='sqkilometers',
            secondary_area_unit='acres'
        )
        measure_control.add_to(m)
        
        # Mouse position display
        MousePosition(
            position='bottomleft',
            separator='|',
            empty_string='No coordinates',
            lng_first=True,
            num_digits=20,
            prefix='Coordinates:',
            lat_formatter="function(num) {return L.Util.formatNum(num, 6) + ' °';}",
            lng_formatter="function(num) {return L.Util.formatNum(num, 6) + ' °';}"
        ).add_to(m)
    
    def _add_aoi_to_map(self, m: folium.Map, aoi_data: Dict):
        """Add existing AOI to map"""
        if 'geojson' in aoi_data:
            # Shapefile AOI
            folium.GeoJson(
                aoi_data['geojson'],
                style_function=lambda x: {
                    'fillColor': '#3388ff',
                    'color': '#ff0000',
                    'weight': 3,
                    'fillOpacity': 0.2,
                    'opacity': 0.8
                },
                popup=folium.Popup(
                    f"<b>Current AOI</b><br>"
                    f"Features: {aoi_data.get('feature_count', 'N/A')}<br>"
                    f"Area: {aoi_data.get('total_area_km2', 'N/A')} km²",
                    max_width=200
                ),
                tooltip="Current Area of Interest"
            ).add_to(m)
            
            # Fit bounds to AOI
            bounds = aoi_data['bounds']
            sw = [bounds['miny'], bounds['minx']]
            ne = [bounds['maxy'], bounds['maxx']]
            m.fit_bounds([sw, ne])
            
        elif 'bounds' in aoi_data:
            # Bounding box AOI
            bounds = aoi_data['bounds']
            folium.Rectangle(
                bounds=[[bounds['miny'], bounds['minx']], [bounds['maxy'], bounds['maxx']]],
                color='#ff0000',
                fill=True,
                fillColor='#3388ff',
                fillOpacity=0.2,
                weight=3,
                popup="<b>Current AOI</b><br>Bounding Box"
            ).add_to(m)
            
            # Fit bounds
            sw = [bounds['miny'], bounds['minx']]
            ne = [bounds['maxy'], bounds['maxx']]
            m.fit_bounds([sw, ne])
    
    def process_map_interactions(self, map_data: Dict) -> Tuple[Optional[Dict], Optional[Dict], Optional[str]]:
        """
        Process map interactions and extract AOI geometry
        
        Args:
            map_data: Data returned from st_folium
            
        Returns:
            Tuple of (geometry_dict, bounds_dict, error_message)
        """
        try:
            if not map_data or 'all_drawings' not in map_data:
                return None, None, None
            
            drawings = map_data['all_drawings']
            if not drawings:
                return None, None, None
            
            # Get the most recent drawing (user may have drawn multiple shapes)
            # Filter out any deleted drawings and take the last valid one
            valid_drawings = [d for d in drawings if d.get('geometry') is not None]
            if not valid_drawings:
                return None, None, None
                
            last_drawing = valid_drawings[-1]
            
            if 'geometry' not in last_drawing:
                return None, None, "Invalid drawing data"
            
            geometry = last_drawing['geometry']
            geom_type = geometry.get('type', '')
            
            # Validate geometry type
            if geom_type not in ['Polygon', 'Rectangle', 'Circle']:
                return None, None, f"Unsupported geometry type: {geom_type}"
            
            # Convert circle to polygon if needed
            if geom_type == 'Circle':
                geometry = self._circle_to_polygon(geometry)
            
            # Calculate bounds
            bounds = self._calculate_bounds(geometry)
            
            return geometry, bounds, None
            
        except Exception as e:
            logger.error(f"Error processing map interactions: {e}")
            return None, None, f"Error processing drawing: {str(e)}"
    
    def _circle_to_polygon(self, circle_geom: Dict) -> Dict:
        """Convert circle geometry to polygon approximation"""
        try:
            from math import cos, sin, radians
            
            # Extract center and radius
            center = circle_geom.get('coordinates', [0, 0])
            radius_m = circle_geom.get('radius', 1000)
            
            # Convert radius from meters to degrees (rough approximation)
            radius_deg = radius_m / 111000  # Rough conversion
            
            # Create polygon with 36 points
            points = []
            for i in range(36):
                angle = radians(i * 10)
                lat = center[1] + radius_deg * cos(angle)
                lon = center[0] + radius_deg * sin(angle)
                points.append([lon, lat])
            
            # Close polygon
            points.append(points[0])
            
            return {
                'type': 'Polygon',
                'coordinates': [points]
            }
            
        except Exception as e:
            logger.warning(f"Error converting circle: {e}")
            # Fallback to square
            buffer = 0.01
            return {
                'type': 'Polygon',
                'coordinates': [[
                    [center[0] - buffer, center[1] - buffer],
                    [center[0] + buffer, center[1] - buffer],
                    [center[0] + buffer, center[1] + buffer],
                    [center[0] - buffer, center[1] + buffer],
                    [center[0] - buffer, center[1] - buffer]
                ]]
            }
    
    def _calculate_bounds(self, geometry: Dict) -> Dict:
        """Calculate bounding box from geometry"""
        coords = self._extract_coordinates(geometry)
        if not coords:
            return {}
        
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        
        return {
            'minx': min(lons),
            'miny': min(lats),
            'maxx': max(lons),
            'maxy': max(lats)
        }
    
    def _extract_coordinates(self, geometry: Dict) -> List[List[float]]:
        """Extract all coordinate pairs from geometry"""
        coords = []
        geom_type = geometry.get('type', '')
        coordinates = geometry.get('coordinates', [])
        
        if geom_type == 'Point':
            coords = [coordinates]
        elif geom_type in ['LineString', 'MultiPoint']:
            coords = coordinates
        elif geom_type in ['Polygon', 'MultiLineString']:
            for ring in coordinates:
                coords.extend(ring)
        elif geom_type == 'MultiPolygon':
            for poly in coordinates:
                for ring in poly:
                    coords.extend(ring)
        
        return coords


def display_unified_map_interface() -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Display unified map interface with mode switching
    
    Returns:
        Tuple of (aoi_geometry, aoi_bounds)
    """
    map_interface = UnifiedMapInterface()
    
    # Mode selection
    col1, col2, col3 = st.columns([1, 1, 2])
    
    # Check if clear button was clicked
    clear_clicked = False
    
    # Initialize map mode in session state if not exists
    if 'map_mode' not in st.session_state:
        st.session_state.map_mode = "View"
    
    with col2:
        if st.button("🗑️ Clear AOI"):
            # Clear all AOI data
            aoi_keys = ['aoi_geometry', 'aoi_bounds', 'uploaded_aoi', 'aoi_drawn']
            for key in aoi_keys:
                if key in st.session_state:
                    del st.session_state[key]
            
            # CRITICAL: Increment map refresh counter to force new map component
            if 'map_refresh_counter' not in st.session_state:
                st.session_state.map_refresh_counter = 0
            st.session_state.map_refresh_counter += 1
            
            # Reset radio button to View mode
            st.session_state.map_mode = "View"
            
            st.success("✅ AOI cleared! Switch to Draw mode to create a new AOI.")
            st.rerun()
    
    with col1:
        # Radio button controlled by session state
        map_mode = st.radio(
            "Map Mode", 
            ["View", "Draw"],
            index=0 if st.session_state.map_mode == "View" else 1,
            help="Switch between viewing existing AOI and drawing new AOI",
            horizontal=True,
            key="map_mode_radio"
        )
        
        # Update session state when radio changes
        st.session_state.map_mode = map_mode
    
    with col3:
        if map_mode == "Draw":
            # Check if AOI already exists (must have actual values, not just None)
            has_existing_aoi = (
                (st.session_state.get('aoi_geometry') is not None) or 
                (st.session_state.get('aoi_bounds') is not None) or 
                (st.session_state.get('uploaded_aoi') is not None)
            )
            
            if has_existing_aoi:
                st.warning("⚠️ **AOI Already Exists**: Drawing tools are disabled. Click '🗑️ Clear AOI' to draw a new area.")
            else:
                st.info("🖊️ **Draw AOI**: Use the drawing tools on the map to define your area of interest")
        else:
            st.info("👀 **View Mode**: Upload shapefile or enter coordinates in sidebar")
    
    # Get current AOI data
    current_aoi = None
    if 'uploaded_aoi' in st.session_state and st.session_state.uploaded_aoi:
        current_aoi = st.session_state.uploaded_aoi
    elif 'aoi_bounds' in st.session_state and st.session_state.aoi_bounds:
        current_aoi = {'bounds': st.session_state.aoi_bounds}
    
    # Create and display map
    mode = "draw" if map_mode == "Draw" else "view"
    
    # Determine if drawing should be allowed (single AOI policy)
    has_existing_aoi = (
        (st.session_state.get('aoi_geometry') is not None) or 
        (st.session_state.get('aoi_bounds') is not None) or 
        (st.session_state.get('uploaded_aoi') is not None) or
        (st.session_state.get('aoi_drawn', False) is True)  # Explicit drawing flag
    )
    allow_drawing = not has_existing_aoi
    
    unified_map = map_interface.create_unified_map(
        aoi_data=current_aoi, 
        mode=mode, 
        allow_drawing=allow_drawing
    )
    
    # Initialize map refresh counter if not exists
    if 'map_refresh_counter' not in st.session_state:
        st.session_state.map_refresh_counter = 0
    
    # Display map with appropriate height
    # Only return drawing data if drawing is allowed
    returned_objects = ["all_drawings", "last_clicked"] if (mode == "draw" and allow_drawing) else ["last_clicked"]
    
    # CRITICAL: Use refresh counter as key to force fresh map component when cleared
    map_data = st_folium(
        unified_map,
        width=None,  # Use full width
        height=600,  # Larger height for better usability
        returned_objects=returned_objects,
        key=f"unified_map_{st.session_state.map_refresh_counter}_{mode}_{allow_drawing}"
    )
    
    # Process drawing interactions only if in draw mode AND drawing is allowed
    if mode == "draw" and allow_drawing and map_data:
        geometry, bounds, error = map_interface.process_map_interactions(map_data)
        
        if error:
            st.error(f"❌ {error}")
            return None, None
        
        if geometry and bounds:
            # Validate and display AOI information
            area_info = calculate_aoi_info(geometry)
            if area_info:
                # Validate AOI size limits
                area_km2 = area_info['area_km2']
                area_acres = area_info['area_acres']
                
                # Size limits
                MIN_AREA_ACRES = 0.1  # 0.1 acre minimum
                MAX_AREA_KM2 = 10000  # 10,000 km² maximum
                
                min_area_km2 = MIN_AREA_ACRES / 247.105  # Convert acres to km²
                
                # Check size limits
                if area_km2 < min_area_km2:
                    st.error(f"❌ **AOI too small!** Minimum area: {MIN_AREA_ACRES} acres ({min_area_km2:.6f} km²). Current: {area_acres:.3f} acres.")
                    return None, None
                    
                if area_km2 > MAX_AREA_KM2:
                    st.error(f"❌ **AOI too large!** Maximum area: {MAX_AREA_KM2:,} km². Current: {area_km2:.1f} km².")
                    return None, None
                
                # Show success message with area-based warnings
                st.success("✅ **AOI Created!** Your area of interest has been defined.")
                
                # Add smart warnings based on area size
                if area_km2 >= 2000:
                    st.warning("🚨 **Very large area** - DEM downloads may take 1+ hours. Consider a smaller area for faster processing.")
                elif area_km2 >= 500:
                    st.warning("⚠️ **Large area** - DEM downloads may take 30-60 minutes.")
                elif area_km2 >= 100:
                    st.info("⏱️ **Medium area** - DEM downloads may take 10-20 minutes.")
                else:
                    st.info("✅ **Small to medium area** - Fast downloads expected (1-5 minutes).")
                
                # Display consistent AOI metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Area", f"{area_info['area_km2']:.3f} km²")
                with col2:
                    st.metric("Area", f"{area_info['area_acres']:.1f} acres")
                with col3:
                    st.metric("Perimeter", f"{area_info['perimeter_km']:.2f} km")
                with col4:
                    st.metric("Center", f"{area_info['center_lat']:.4f}, {area_info['center_lon']:.4f}")
                
                # Set flag to prevent further drawings
                st.session_state.aoi_drawn = True
                
                return geometry, bounds
    
    # If in draw mode but drawing not allowed, show clear message
    elif mode == "draw" and not allow_drawing:
        st.warning("🚫 **Drawing Disabled**: An AOI already exists. Use the '🗑️ Clear AOI' button above to draw a new area.")
    
    return None, None


def calculate_aoi_info(geometry: Dict) -> Optional[Dict]:
    """Calculate detailed AOI information"""
    try:
        from shapely.geometry import shape
        import geopandas as gpd
        
        # Create geometry object
        geom_obj = shape(geometry)
        gdf = gpd.GeoDataFrame([1], geometry=[geom_obj], crs='EPSG:4326')
        
        # Reproject for accurate area calculation
        gdf_proj = gdf.to_crs('EPSG:3857')  # Web Mercator
        area_m2 = gdf_proj.geometry.area.iloc[0]
        area_km2 = area_m2 / 1_000_000
        
        # Calculate perimeter
        perimeter_m = gdf_proj.geometry.length.iloc[0]
        perimeter_km = perimeter_m / 1000
        
        # Get bounds and center
        bounds = gdf.total_bounds
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
        
        return {
            'area_km2': area_km2,
            'area_acres': area_km2 * 247.105,
            'perimeter_km': perimeter_km,
            'center_lat': center_lat,
            'center_lon': center_lon,
            'bounds': {
                'minx': bounds[0],
                'miny': bounds[1],
                'maxx': bounds[2],
                'maxy': bounds[3]
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating AOI info: {e}")
        return None