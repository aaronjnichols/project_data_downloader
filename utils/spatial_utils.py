"""
Spatial utility functions for coordinate system handling, clipping, and transformations.
"""
import os
from typing import Optional, Tuple, Union
import geopandas as gpd
from shapely.geometry import Point, Polygon, box
import rasterio
from rasterio.mask import mask
from rasterio.warp import transform_bounds
import logging

logger = logging.getLogger(__name__)


def clip_vector_to_aoi(vector_gdf: gpd.GeoDataFrame, 
                      aoi_gdf: gpd.GeoDataFrame) -> Optional[gpd.GeoDataFrame]:
    """
    Clip vector data to AOI geometry
    
    Args:
        vector_gdf: Vector data to clip
        aoi_gdf: AOI geometry for clipping
        
    Returns:
        Clipped GeoDataFrame or None if error
    """
    try:
        # Ensure both datasets are in the same CRS
        if vector_gdf.crs != aoi_gdf.crs:
            logger.info(f"Reprojecting vector data from {vector_gdf.crs} to {aoi_gdf.crs}")
            vector_gdf = vector_gdf.to_crs(aoi_gdf.crs)
        
        # Perform the clip operation
        clipped_gdf = gpd.clip(vector_gdf, aoi_gdf)
        
        logger.info(f"Clipped vector data: {len(vector_gdf)} -> {len(clipped_gdf)} features")
        
        return clipped_gdf if len(clipped_gdf) > 0 else None
        
    except Exception as e:
        logger.error(f"Error clipping vector data: {e}")
        return vector_gdf  # Return original data if clipping fails


def clip_raster_to_aoi(raster_path: str, aoi_gdf: gpd.GeoDataFrame, 
                      output_path: str) -> bool:
    """
    Clip raster data to AOI geometry
    
    Args:
        raster_path: Path to input raster file
        aoi_gdf: AOI geometry for clipping
        output_path: Path for output clipped raster
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with rasterio.open(raster_path) as src:
            # Reproject AOI to match raster CRS if needed
            if aoi_gdf.crs != src.crs:
                aoi_reprojected = aoi_gdf.to_crs(src.crs)
            else:
                aoi_reprojected = aoi_gdf
            
            # Get geometries for masking
            geometries = aoi_reprojected.geometry.values
            
            # Clip the raster
            out_image, out_transform = mask(src, geometries, crop=True)
            out_meta = src.meta.copy()
            
            # Update metadata
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform
            })
            
            # Create output directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write clipped raster
            with rasterio.open(output_path, "w", **out_meta) as dest:
                dest.write(out_image)
            
            logger.info(f"Clipped raster saved to: {output_path}")
            return True
            
    except Exception as e:
        logger.error(f"Error clipping raster: {e}")
        return False


def reproject_gdf(gdf: gpd.GeoDataFrame, target_crs: Union[str, int]) -> gpd.GeoDataFrame:
    """
    Reproject GeoDataFrame to target CRS
    
    Args:
        gdf: Input GeoDataFrame
        target_crs: Target CRS (e.g., 'EPSG:4326' or 4326)
        
    Returns:
        Reprojected GeoDataFrame
    """
    try:
        if gdf.crs != target_crs:
            logger.info(f"Reprojecting from {gdf.crs} to {target_crs}")
            return gdf.to_crs(target_crs)
        return gdf
    except Exception as e:
        logger.error(f"Error reprojecting data: {e}")
        return gdf


def validate_geometry(gdf: gpd.GeoDataFrame, fix_invalid: bool = True) -> gpd.GeoDataFrame:
    """
    Validate and optionally fix invalid geometries
    
    Args:
        gdf: Input GeoDataFrame
        fix_invalid: Whether to attempt fixing invalid geometries
        
    Returns:
        GeoDataFrame with validated geometries
    """
    try:
        # Check for invalid geometries
        invalid_mask = ~gdf.geometry.is_valid
        invalid_count = invalid_mask.sum()
        
        if invalid_count > 0:
            logger.warning(f"Found {invalid_count} invalid geometries")
            
            if fix_invalid:
                logger.info("Attempting to fix invalid geometries")
                gdf.loc[invalid_mask, 'geometry'] = gdf.loc[invalid_mask, 'geometry'].buffer(0)
                
                # Check again after fixing
                still_invalid = ~gdf.geometry.is_valid
                still_invalid_count = still_invalid.sum()
                
                if still_invalid_count > 0:
                    logger.warning(f"Could not fix {still_invalid_count} geometries, removing them")
                    gdf = gdf[gdf.geometry.is_valid]
                else:
                    logger.info("All invalid geometries fixed")
        
        return gdf
        
    except Exception as e:
        logger.error(f"Error validating geometries: {e}")
        return gdf


def calculate_bounds_buffer(bounds: Tuple[float, float, float, float], 
                          buffer_percent: float = 10.0) -> Tuple[float, float, float, float]:
    """
    Add a buffer around bounding box
    
    Args:
        bounds: Original bounds (minx, miny, maxx, maxy)
        buffer_percent: Buffer size as percentage of dimensions
        
    Returns:
        Buffered bounds tuple
    """
    minx, miny, maxx, maxy = bounds
    
    width = maxx - minx
    height = maxy - miny
    
    buffer_x = width * (buffer_percent / 100.0)
    buffer_y = height * (buffer_percent / 100.0)
    
    return (
        minx - buffer_x,
        miny - buffer_y,
        maxx + buffer_x,
        maxy + buffer_y
    )


def bounds_to_polygon(bounds: Tuple[float, float, float, float]) -> Polygon:
    """
    Convert bounds tuple to Shapely Polygon
    
    Args:
        bounds: Bounds tuple (minx, miny, maxx, maxy)
        
    Returns:
        Shapely Polygon object
    """
    minx, miny, maxx, maxy = bounds
    return box(minx, miny, maxx, maxy)


def estimate_utm_crs(bounds: Tuple[float, float, float, float]) -> str:
    """
    Estimate appropriate UTM CRS for a given bounding box
    
    Args:
        bounds: Bounds in WGS84 (minx, miny, maxx, maxy)
        
    Returns:
        UTM CRS code (e.g., 'EPSG:32633')
    """
    minx, miny, maxx, maxy = bounds
    
    # Use center point for UTM zone calculation
    center_lon = (minx + maxx) / 2
    center_lat = (miny + maxy) / 2
    
    # Calculate UTM zone
    utm_zone = int((center_lon + 180) / 6) + 1
    
    # Determine hemisphere
    if center_lat >= 0:
        # Northern hemisphere
        epsg_code = 32600 + utm_zone
    else:
        # Southern hemisphere
        epsg_code = 32700 + utm_zone
    
    return f"EPSG:{epsg_code}"


def safe_file_name(name: str) -> str:
    """
    Create a safe filename by removing/replacing problematic characters
    
    Args:
        name: Original name
        
    Returns:
        Safe filename
    """
    # Replace problematic characters
    replacements = {
        ' ': '_',
        '/': '_',
        '\\': '_',
        ':': '_',
        '*': '_',
        '?': '_',
        '"': '_',
        '<': '_',
        '>': '_',
        '|': '_',
        '.': '_'
    }
    
    safe_name = name
    for old, new in replacements.items():
        safe_name = safe_name.replace(old, new)
    
    # Remove multiple underscores
    while '__' in safe_name:
        safe_name = safe_name.replace('__', '_')
    
    return safe_name.strip('_') 
def dem_to_contours(dem_path: str, output_path: str, interval: float) -> bool:
    """
    Convert a DEM raster to contour lines using pure Python libraries.
    
    Uses rasterio for raster I/O, skimage for contour generation, and 
    shapely/geopandas for geometry handling - no GDAL dependency required.
    
    Args:
        dem_path: Path to input DEM raster file
        output_path: Path for output contour shapefile
        interval: Contour interval in the same units as the DEM
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import numpy as np
        from skimage import measure
        from shapely.geometry import LineString
        import pandas as pd
        
        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        logger.info(f"Generating contours from {dem_path} with {interval} unit interval")
        
        # Read the DEM raster
        with rasterio.open(dem_path) as src:
            # Read the elevation data
            elevation = src.read(1)
            transform = src.transform
            crs = src.crs
            
            # Handle nodata values
            if src.nodata is not None:
                elevation = np.where(elevation == src.nodata, np.nan, elevation)
            
            # Get elevation range and create contour levels
            valid_elevations = elevation[~np.isnan(elevation)]
            if len(valid_elevations) == 0:
                logger.error("No valid elevation data found in DEM")
                return False
                
            min_elev = np.nanmin(valid_elevations)
            max_elev = np.nanmax(valid_elevations)
            
            # Create contour levels based on interval
            # Round to nearest interval and create levels
            start_level = np.ceil(min_elev / interval) * interval
            end_level = np.floor(max_elev / interval) * interval
            levels = np.arange(start_level, end_level + interval, interval)
            
            if len(levels) == 0:
                logger.warning(f"No contour levels found for interval {interval} between {min_elev:.2f} and {max_elev:.2f}")
                return False
            
            logger.info(f"Generating {len(levels)} contour levels from {start_level:.1f} to {end_level:.1f}")
            
            # Generate contours using skimage
            contours = []
            elevations = []
            
            for level in levels:
                try:
                    # Generate contour lines for this elevation
                    contour_lines = measure.find_contours(elevation, level)
                    
                    for contour in contour_lines:
                        # Convert pixel coordinates to geographic coordinates
                        # contour is in (row, col) format, need to convert to (x, y)
                        if len(contour) < 2:
                            continue  # Skip contours with too few points
                            
                        # Transform from pixel coordinates to geographic coordinates
                        geo_coords = []
                        for row, col in contour:
                            x, y = rasterio.transform.xy(transform, row, col)
                            geo_coords.append((x, y))
                        
                        # Create LineString geometry
                        if len(geo_coords) >= 2:
                            line = LineString(geo_coords)
                            contours.append(line)
                            elevations.append(level)
                            
                except Exception as e:
                    logger.warning(f"Error generating contour for level {level}: {e}")
                    continue
            
            if len(contours) == 0:
                logger.warning("No valid contours generated")
                return False
            
            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame({
                'elevation': elevations,
                'geometry': contours
            }, crs=crs)
            
            # Add additional attributes
            gdf['contour_id'] = range(len(gdf))
            gdf['interval'] = interval
            
            # Save to shapefile
            gdf.to_file(output_path)
            
            logger.info(f"Generated {len(contours)} contour lines saved to: {output_path}")
            logger.info(f"Elevation range: {min(elevations):.1f} to {max(elevations):.1f}")
            
            return True
            
    except ImportError as e:
        logger.error(f"Missing required library for contour generation: {e}")
        logger.error("Please install scikit-image: pip install scikit-image")
        return False
    except Exception as e:
        logger.error(f"Error generating contours: {e}")
        return False
