"""
Enhanced Map Functionality for Geospatial Data Downloader
=========================================================

This module provides advanced map capabilities including:
- Interactive AOI drawing tools
- Coordinate system validation
- Enhanced map visualizations
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon, box
import pyproj
from pyproj import CRS, Transformer
import json
from typing import Dict, List, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)


class EnhancedMapManager:
    """Manages enhanced map functionality including drawing tools and CRS validation"""
    
    def __init__(self):
        self.default_center = [39.8283, -98.5795]  # Geographic center of USA
        self.default_zoom = 4
        
    def create_drawing_map(self, center: List[float] = None, zoom: int = None) -> folium.Map:
        """
        Create a Folium map with drawing tools enabled
        
        Args:
            center: Map center coordinates [lat, lon]
            zoom: Initial zoom level
            
        Returns:
            folium.Map: Map with drawing tools
        """
        if center is None:
            center = self.default_center
        if zoom is None:
            zoom = self.default_zoom
            
        # Create base map
        m = folium.Map(
            location=center,
            zoom_start=zoom,
            tiles='OpenStreetMap'
        )
        
        # Add additional tile layers
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satellite',
            overlay=False,
            control=True
        ).add_to(m)
        
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Topographic',
            overlay=False,
            control=True
        ).add_to(m)
        
        # Add drawing tools
        from folium.plugins import Draw
        draw = Draw(
            export=True,
            position='topleft',
            draw_options={
                'polyline': True,
                'polygon': True,
                'circle': True,
                'rectangle': True,
                'marker': True,
                'circlemarker': False,
            },
            edit_options={
                'poly': True,
                'remove': True
            }
        )
        draw.add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        return m
    
    def process_drawn_features(self, map_data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Process features drawn on the map and extract AOI geometry
        
        Args:
            map_data: Data returned from st_folium
            
        Returns:
            Tuple of (geometry_dict, error_message)
        """
        try:
            if not map_data or 'all_drawings' not in map_data:
                return None, "No drawings found on map"
            
            drawings = map_data['all_drawings']
            if not drawings:
                return None, "No areas drawn on map"
            
            # Get the last drawn feature (most recent)
            last_drawing = drawings[-1]
            
            # Extract geometry
            if 'geometry' in last_drawing:
                geometry = last_drawing['geometry']
                
                # Validate geometry type
                geom_type = geometry.get('type', '')
                if geom_type not in ['Polygon', 'Rectangle', 'Circle']:
                    return None, f"Unsupported geometry type: {geom_type}. Please draw a polygon, rectangle, or circle."
                
                # For circles, convert to polygon approximation
                if geom_type == 'Circle':
                    geometry = self._circle_to_polygon(geometry)
                
                return geometry, None
            else:
                return None, "Invalid drawing data - no geometry found"
                
        except Exception as e:
            logger.error(f"Error processing drawn features: {e}")
            return None, f"Error processing drawing: {str(e)}"
    
    def _circle_to_polygon(self, circle_geom: Dict) -> Dict:
        """Convert a circle geometry to a polygon approximation"""
        try:
            from geopy.distance import distance
            from math import cos, sin, radians
            
            # Extract center and radius
            center = circle_geom['coordinates']
            radius_m = circle_geom.get('radius', 1000)  # Default 1km radius
            
            # Create polygon approximation (36 points = 10 degree increments)
            points = []
            for i in range(36):
                angle = radians(i * 10)
                # Calculate point at distance and bearing
                lat = center[1] + (radius_m / 111000) * cos(angle)  # Rough conversion
                lon = center[0] + (radius_m / (111000 * cos(radians(center[1])))) * sin(angle)
                points.append([lon, lat])
            
            # Close the polygon
            points.append(points[0])
            
            return {
                'type': 'Polygon',
                'coordinates': [points]
            }
            
        except Exception as e:
            logger.warning(f"Error converting circle to polygon: {e}")
            # Fallback: create a simple square
            buffer = 0.01  # Rough 1km buffer in degrees
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
    
    def validate_and_display_aoi(self, geometry: Dict) -> Tuple[bool, str, Dict]:
        """
        Validate AOI geometry and display information
        
        Args:
            geometry: GeoJSON geometry dictionary
            
        Returns:
            Tuple of (is_valid, message, info_dict)
        """
        try:
            # Create GeoDataFrame from geometry
            from shapely.geometry import shape
            geom_obj = shape(geometry)
            gdf = gpd.GeoDataFrame([1], geometry=[geom_obj], crs='EPSG:4326')
            
            # Calculate area and bounds
            # Reproject to equal-area projection for accurate area calculation
            gdf_proj = gdf.to_crs('EPSG:3857')  # Web Mercator
            area_m2 = gdf_proj.geometry.area.iloc[0]
            area_km2 = area_m2 / 1_000_000
            
            # Get bounds
            bounds = gdf.total_bounds
            
            # Validate size
            max_area_km2 = 10000  # 10,000 km² limit
            if area_km2 > max_area_km2:
                return False, f"AOI too large ({area_km2:.1f} km²). Maximum allowed: {max_area_km2} km²", {}
            
            min_area_km2 = 0.001  # 0.001 km² minimum (1000 m²)
            if area_km2 < min_area_km2:
                return False, f"AOI too small ({area_km2:.6f} km²). Minimum required: {min_area_km2} km²", {}
            
            # Create info dictionary
            info = {
                'area_km2': round(area_km2, 3),
                'area_acres': round(area_km2 * 247.105, 1),  # km² to acres
                'bounds': {
                    'minx': round(bounds[0], 6),
                    'miny': round(bounds[1], 6),
                    'maxx': round(bounds[2], 6),
                    'maxy': round(bounds[3], 6)
                },
                'center': {
                    'lat': round((bounds[1] + bounds[3]) / 2, 6),
                    'lon': round((bounds[0] + bounds[2]) / 2, 6)
                }
            }
            
            return True, f"Valid AOI: {area_km2:.3f} km² ({info['area_acres']} acres)", info
            
        except Exception as e:
            logger.error(f"Error validating AOI: {e}")
            return False, f"Error validating AOI: {str(e)}", {}


class CRSValidator:
    """Handles coordinate reference system validation and conversion"""
    
    def __init__(self):
        self.common_crs = {
            'WGS84': 'EPSG:4326',
            'Web Mercator': 'EPSG:3857',
            'NAD83': 'EPSG:4269',
            'NAD27': 'EPSG:4267',
            'State Plane (example)': 'EPSG:2278'  # Texas South Central
        }
    
    def detect_crs_from_geometry(self, geometry: Dict, hint_location: str = None) -> Tuple[str, float]:
        """
        Attempt to detect the most likely CRS for a geometry
        
        Args:
            geometry: GeoJSON geometry
            hint_location: Optional location hint (state, country, etc.)
            
        Returns:
            Tuple of (suggested_epsg, confidence_score)
        """
        try:
            coords = self._extract_coordinates(geometry)
            if not coords:
                return 'EPSG:4326', 0.5
            
            # Analyze coordinate ranges
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            
            min_lon, max_lon = min(lons), max(lons)
            min_lat, max_lat = min(lats), max(lats)
            
            # Check if coordinates are in typical geographic ranges
            if -180 <= min_lon <= 180 and -90 <= min_lat <= 90:
                # Likely geographic coordinates
                if hint_location and 'north america' in hint_location.lower():
                    return 'EPSG:4269', 0.8  # NAD83
                else:
                    return 'EPSG:4326', 0.9  # WGS84
            
            # Check for projected coordinates (large numbers)
            elif abs(min_lon) > 1000 or abs(min_lat) > 1000:
                # Likely projected coordinates
                if hint_location:
                    return self._suggest_projected_crs(hint_location), 0.7
                else:
                    return 'EPSG:3857', 0.6  # Default to Web Mercator
            
            else:
                return 'EPSG:4326', 0.3  # Low confidence default
                
        except Exception as e:
            logger.error(f"Error detecting CRS: {e}")
            return 'EPSG:4326', 0.1
    
    def _extract_coordinates(self, geometry: Dict) -> List[List[float]]:
        """Extract coordinate pairs from geometry"""
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
    
    def _suggest_projected_crs(self, location_hint: str) -> str:
        """Suggest projected CRS based on location"""
        location_lower = location_hint.lower()
        
        # Simple location-based suggestions
        if any(state in location_lower for state in ['texas', 'tx']):
            return 'EPSG:3081'  # Texas Centric Mapping System
        elif any(state in location_lower for state in ['california', 'ca']):
            return 'EPSG:3310'  # California Albers
        elif any(state in location_lower for state in ['florida', 'fl']):
            return 'EPSG:3086'  # Florida GDL Albers
        elif 'utm' in location_lower:
            return 'EPSG:32633'  # UTM Zone 33N (example)
        else:
            return 'EPSG:3857'  # Default Web Mercator
    
    def validate_crs_transformation(self, geometry: Dict, from_crs: str, to_crs: str = 'EPSG:4326') -> Tuple[bool, str, Dict]:
        """
        Validate that a CRS transformation is reasonable
        
        Args:
            geometry: Input geometry
            from_crs: Source CRS
            to_crs: Target CRS
            
        Returns:
            Tuple of (is_valid, message, transformed_geometry)
        """
        try:
            # Create transformer
            transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)
            
            # Transform a sample point to check validity
            coords = self._extract_coordinates(geometry)
            if coords:
                sample_x, sample_y = coords[0]
                transformed_x, transformed_y = transformer.transform(sample_x, sample_y)
                
                # Check if transformed coordinates are reasonable for target CRS
                if to_crs == 'EPSG:4326':  # Geographic
                    if not (-180 <= transformed_x <= 180 and -90 <= transformed_y <= 90):
                        return False, f"Transformation results in invalid geographic coordinates: ({transformed_x:.2f}, {transformed_y:.2f})", {}
                
                # Transform the full geometry
                transformed_geom = self._transform_geometry(geometry, transformer)
                
                return True, f"Successfully transformed from {from_crs} to {to_crs}", transformed_geom
            
            else:
                return False, "No coordinates found in geometry", {}
                
        except Exception as e:
            logger.error(f"CRS transformation error: {e}")
            return False, f"CRS transformation failed: {str(e)}", {}
    
    def _transform_geometry(self, geometry: Dict, transformer: Transformer) -> Dict:
        """Transform geometry coordinates using transformer"""
        def transform_coords(coords):
            if isinstance(coords[0], (int, float)):
                # Single coordinate pair
                return list(transformer.transform(coords[0], coords[1]))
            else:
                # List of coordinate pairs
                return [list(transformer.transform(x, y)) for x, y in coords]
        
        geom_type = geometry['type']
        coordinates = geometry['coordinates']
        
        if geom_type == 'Point':
            new_coords = transform_coords(coordinates)
        elif geom_type in ['LineString', 'MultiPoint']:
            new_coords = transform_coords(coordinates)
        elif geom_type in ['Polygon', 'MultiLineString']:
            new_coords = [transform_coords(ring) for ring in coordinates]
        elif geom_type == 'MultiPolygon':
            new_coords = [[transform_coords(ring) for ring in poly] for poly in coordinates]
        else:
            new_coords = coordinates  # Fallback
        
        return {
            'type': geom_type,
            'coordinates': new_coords
        }


def display_aoi_drawing_interface() -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Display the AOI drawing interface and return geometry and bounds
    
    Returns:
        Tuple of (aoi_geometry, aoi_bounds)
    """
    st.subheader("📍 Define Area of Interest (AOI)")
    
    # Initialize managers
    map_manager = EnhancedMapManager()
    crs_validator = CRSValidator()
    
    # Create tabs for different input methods
    tab1, tab2, tab3 = st.tabs(["🗺️ Draw on Map", "📁 Upload Shapefile", "📋 Enter Coordinates"])
    
    with tab1:
        st.write("Use the drawing tools on the map to define your area of interest:")
        
        # Create map with drawing tools
        drawing_map = map_manager.create_drawing_map()
        
        # Display map
        map_data = st_folium(
            drawing_map,
            width=700,
            height=500,
            returned_objects=["all_drawings", "last_object_clicked"]
        )
        
        # Process drawn features
        if map_data:
            geometry, error = map_manager.process_drawn_features(map_data)
            
            if error:
                if "No drawings found" not in error and "No areas drawn" not in error:
                    st.error(error)
                return None, None
            
            if geometry:
                # Validate AOI
                is_valid, message, info = map_manager.validate_and_display_aoi(geometry)
                
                if is_valid:
                    st.success(message)
                    
                    # Display AOI information
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Area", f"{info['area_km2']} km²")
                    with col2:
                        st.metric("Area", f"{info['area_acres']} acres")
                    with col3:
                        st.metric("Center", f"{info['center']['lat']:.3f}, {info['center']['lon']:.3f}")
                    
                    # Convert to bounds format
                    bounds = info['bounds']
                    aoi_bounds = {
                        'minx': bounds['minx'],
                        'miny': bounds['miny'],
                        'maxx': bounds['maxx'],
                        'maxy': bounds['maxy']
                    }
                    
                    return geometry, aoi_bounds
                else:
                    st.error(message)
                    return None, None
    
    with tab2:
        st.write("Upload a shapefile to define your AOI:")
        # Keep existing shapefile upload functionality
        uploaded_files = st.file_uploader(
            "Upload Shapefile Components",
            type=['shp', 'shx', 'dbf', 'prj'],
            accept_multiple_files=True,
            help="Upload .shp, .shx, .dbf, and .prj files"
        )
        
        if uploaded_files and len(uploaded_files) >= 3:
            # Process uploaded shapefile (existing logic)
            # This would integrate with existing shapefile processing
            st.info("Shapefile upload processing (integrate with existing logic)")
            return None, None
    
    with tab3:
        st.write("Enter bounding box coordinates:")
        
        col1, col2 = st.columns(2)
        with col1:
            min_lon = st.number_input("Minimum Longitude", value=-180.0, min_value=-180.0, max_value=180.0, step=0.001, format="%.6f")
            min_lat = st.number_input("Minimum Latitude", value=-90.0, min_value=-90.0, max_value=90.0, step=0.001, format="%.6f")
        
        with col2:
            max_lon = st.number_input("Maximum Longitude", value=180.0, min_value=-180.0, max_value=180.0, step=0.001, format="%.6f")
            max_lat = st.number_input("Maximum Latitude", value=90.0, min_value=-90.0, max_value=90.0, step=0.001, format="%.6f")
        
        if st.button("Create AOI from Coordinates"):
            if min_lon >= max_lon or min_lat >= max_lat:
                st.error("Invalid coordinates: minimum values must be less than maximum values")
                return None, None
            
            # Create polygon from bounds
            geometry = {
                'type': 'Polygon',
                'coordinates': [[
                    [min_lon, min_lat],
                    [max_lon, min_lat],
                    [max_lon, max_lat],
                    [min_lon, max_lat],
                    [min_lon, min_lat]
                ]]
            }
            
            # Validate AOI
            is_valid, message, info = map_manager.validate_and_display_aoi(geometry)
            
            if is_valid:
                st.success(message)
                
                aoi_bounds = {
                    'minx': min_lon,
                    'miny': min_lat,
                    'maxx': max_lon,
                    'maxy': max_lat
                }
                
                return geometry, aoi_bounds
            else:
                st.error(message)
                return None, None
    
    return None, None