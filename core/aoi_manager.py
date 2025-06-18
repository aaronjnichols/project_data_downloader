"""
AOI (Area of Interest) management functionality.
Handles loading, validation, and processing of AOI shapefiles.
"""
import os
from typing import Tuple, Optional
import geopandas as gpd
from shapely.geometry import box
import logging

logger = logging.getLogger(__name__)


class AOIManager:
    """Manages Area of Interest (AOI) operations"""
    
    def __init__(self):
        self.aoi_gdf: Optional[gpd.GeoDataFrame] = None
        self.bounds: Optional[Tuple[float, float, float, float]] = None
        self.source_file: Optional[str] = None
    
    def load_aoi_from_file(self, file_path: str) -> bool:
        """
        Load AOI from a shapefile or other supported format
        
        Args:
            file_path: Path to the AOI file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"AOI file not found: {file_path}")
                return False
            
            logger.info(f"Loading AOI from: {file_path}")
            self.aoi_gdf = gpd.read_file(file_path)
            
            if len(self.aoi_gdf) == 0:
                logger.error("AOI file contains no features")
                return False
            
            # Ensure AOI is in WGS84 (EPSG:4326) for consistent processing
            if self.aoi_gdf.crs != 'EPSG:4326':
                logger.info(f"Reprojecting AOI from {self.aoi_gdf.crs} to EPSG:4326")
                self.aoi_gdf = self.aoi_gdf.to_crs('EPSG:4326')
            
            # Calculate bounds
            self.bounds = tuple(self.aoi_gdf.total_bounds)
            self.source_file = file_path
            
            logger.info(f"AOI loaded successfully:")
            logger.info(f"  Features: {len(self.aoi_gdf)}")
            logger.info(f"  CRS: {self.aoi_gdf.crs}")
            logger.info(f"  Bounds: {self.bounds}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading AOI file: {e}")
            return False
    
    def load_aoi_from_bounds(self, minx: float, miny: float, 
                           maxx: float, maxy: float, crs: str = "EPSG:4326") -> bool:
        """
        Create AOI from bounding box coordinates
        
        Args:
            minx, miny, maxx, maxy: Bounding box coordinates
            crs: Coordinate reference system (default: EPSG:4326)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create a bounding box geometry
            bbox_geom = box(minx, miny, maxx, maxy)
            
            # Create GeoDataFrame
            self.aoi_gdf = gpd.GeoDataFrame([1], geometry=[bbox_geom], crs=crs)
            
            # Ensure it's in WGS84
            if self.aoi_gdf.crs != 'EPSG:4326':
                self.aoi_gdf = self.aoi_gdf.to_crs('EPSG:4326')
            
            self.bounds = tuple(self.aoi_gdf.total_bounds)
            self.source_file = None
            
            logger.info(f"AOI created from bounds: {self.bounds}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating AOI from bounds: {e}")
            return False
    
    def get_bounds(self) -> Optional[Tuple[float, float, float, float]]:
        """
        Get the bounding box of the AOI in EPSG:4326
        
        Returns:
            Tuple of (minx, miny, maxx, maxy) or None if no AOI loaded
        """
        return self.bounds
    
    def get_bounds_string(self) -> Optional[str]:
        """
        Get bounds as a comma-separated string for API calls
        
        Returns:
            String in format "minx,miny,maxx,maxy,EPSG:4326" or None
        """
        if self.bounds:
            return f"{self.bounds[0]},{self.bounds[1]},{self.bounds[2]},{self.bounds[3]},EPSG:4326"
        return None
    
    def get_geometry(self) -> Optional[gpd.GeoDataFrame]:
        """
        Get the AOI geometry as a GeoDataFrame
        
        Returns:
            GeoDataFrame containing AOI geometry or None
        """
        return self.aoi_gdf
    
    def validate_aoi(self) -> bool:
        """
        Validate the current AOI
        
        Returns:
            True if AOI is valid, False otherwise
        """
        if self.aoi_gdf is None or self.bounds is None:
            logger.error("No AOI loaded")
            return False
        
        minx, miny, maxx, maxy = self.bounds
        
        # Check for valid bounds
        if minx >= maxx or miny >= maxy:
            logger.error("Invalid bounds: min values must be less than max values")
            return False
        
        # Check for reasonable geographic bounds (WGS84)
        if not (-180 <= minx <= 180 and -180 <= maxx <= 180):
            logger.error("Invalid longitude bounds: must be between -180 and 180")
            return False
        if not (-90 <= miny <= 90 and -90 <= maxy <= 90):
            logger.error("Invalid latitude bounds: must be between -90 and 90")
            return False
        
        # Check for reasonable size (not too small or too large)
        width = maxx - minx
        height = maxy - miny
        
        if width < 0.0001 or height < 0.0001:
            logger.warning("AOI is very small, may not intersect with data")
        
        if width > 10 or height > 10:
            logger.warning("AOI is very large, downloads may be slow or fail")
        
        return True
    
    def get_area_km2(self) -> Optional[float]:
        """
        Calculate the approximate area of the AOI in square kilometers
        
        Returns:
            Area in square kilometers or None if no AOI loaded
        """
        if self.aoi_gdf is None:
            return None
        
        try:
            # Reproject to an equal-area projection for area calculation
            # Use Mollweide projection (EPSG:54009) for global equal area
            aoi_projected = self.aoi_gdf.to_crs('EPSG:54009')
            area_m2 = aoi_projected.geometry.area.sum()
            area_km2 = area_m2 / 1_000_000  # Convert to km²
            return area_km2
        except Exception as e:
            logger.error(f"Error calculating area: {e}")
            return None
    
    def is_loaded(self) -> bool:
        """
        Check if an AOI is currently loaded
        
        Returns:
            True if AOI is loaded, False otherwise
        """
        return self.aoi_gdf is not None and self.bounds is not None 