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

logger = logging.getLogger(__name__)


class UnifiedMapInterface:
    """Unified map interface combining viewing and drawing functionality"""
    
    def __init__(self):
        self.default_center = [39.8283, -98.5795]  # Geographic center of USA
        self.default_zoom = 4
        
    def create_unified_map(self, aoi_data=None, mode="view") -> folium.Map:
        """
        Create unified map with both viewing and drawing capabilities
        
        Args:
            aoi_data: Existing AOI data to display
            mode: "view" or "draw" mode
            
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
        
        # Create base map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom,
            tiles='OpenStreetMap'
        )
        
        # Add multiple tile layers
        self._add_tile_layers(m)
        
        # Add drawing tools if in draw mode
        if mode == "draw":
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
        
        # Terrain
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Terrain',
            overlay=False,
            control=True
        ).add_to(m)
    
    def _add_drawing_tools(self, m: folium.Map):
        """Add interactive drawing tools"""
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
                'poly': True,
                'remove': True,
                'edit': True
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
            
            # Get the last drawn feature
            last_drawing = drawings[-1]
            
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
    
    with col1:
        map_mode = st.radio(
            "Map Mode",
            ["View", "Draw"],
            help="Switch between viewing existing AOI and drawing new AOI",
            horizontal=True
        )
    
    with col2:
        if st.button("🔄 Reset Map"):
            # Clear any existing AOI
            if 'aoi_geometry' in st.session_state:
                del st.session_state.aoi_geometry
            if 'aoi_bounds' in st.session_state:
                del st.session_state.aoi_bounds
            if 'uploaded_aoi' in st.session_state:
                del st.session_state.uploaded_aoi
            st.rerun()
    
    with col3:
        if map_mode == "Draw":
            st.info("🖊️ Use the drawing tools on the map to define your AOI")
        else:
            st.info("👀 Viewing mode - upload shapefile or enter coordinates in sidebar")
    
    # Get current AOI data
    current_aoi = None
    if 'uploaded_aoi' in st.session_state and st.session_state.uploaded_aoi:
        current_aoi = st.session_state.uploaded_aoi
    elif 'aoi_bounds' in st.session_state and st.session_state.aoi_bounds:
        current_aoi = {'bounds': st.session_state.aoi_bounds}
    
    # Create and display map
    mode = "draw" if map_mode == "Draw" else "view"
    unified_map = map_interface.create_unified_map(aoi_data=current_aoi, mode=mode)
    
    # Display map with appropriate height
    map_data = st_folium(
        unified_map,
        width=None,  # Use full width
        height=600,  # Larger height for better usability
        returned_objects=["all_drawings", "last_clicked"] if mode == "draw" else ["last_clicked"]
    )
    
    # Process drawing interactions if in draw mode
    if mode == "draw" and map_data:
        geometry, bounds, error = map_interface.process_map_interactions(map_data)
        
        if error:
            st.error(f"❌ {error}")
            return None, None
        
        if geometry and bounds:
            # Check if this is the same as what we already have to prevent loops
            current_geometry = st.session_state.get('aoi_geometry')
            if current_geometry and current_geometry == geometry:
                # Same geometry, don't process again
                return None, None
            
            # Validate AOI size
            area_info = calculate_aoi_info(geometry)
            if area_info:
                # Display AOI information
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Area", f"{area_info['area_km2']:.3f} km²")
                with col2:
                    st.metric("Area", f"{area_info['area_acres']:.1f} acres")
                with col3:
                    st.metric("Perimeter", f"{area_info['perimeter_km']:.2f} km")
                with col4:
                    st.metric("Center", f"{area_info['center_lat']:.4f}, {area_info['center_lon']:.4f}")
                
                # Success message
                st.success(f"✅ AOI defined successfully! Area: {area_info['area_km2']:.3f} km²")
                
                return geometry, bounds
    
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