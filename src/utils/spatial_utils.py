"""
Spatial utility functions for coordinate system handling, clipping, and transformations.

Enhanced features:
- Advanced geometric operations and analysis
- Multi-resolution processing capabilities
- Spatial quality assessment and optimization
- Comprehensive CRS handling and transformation
"""
import os
from typing import Optional, Tuple, Union, List, Dict, Any
import geopandas as gpd
from shapely.geometry import Point, Polygon, box, LineString, MultiPolygon
from shapely.ops import unary_union, transform as shapely_transform
import rasterio
from rasterio.mask import mask
from rasterio.warp import transform_bounds, reproject, Resampling
from rasterio.enums import Resampling as ResamplingMethod
import numpy as np
import logging
from functools import partial
import pyproj

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


def analyze_spatial_distribution(gdf: gpd.GeoDataFrame, aoi_bounds: Tuple[float, float, float, float]) -> Dict[str, Any]:
    """
    Analyze spatial distribution of features within AOI
    
    Args:
        gdf: GeoDataFrame containing spatial features
        aoi_bounds: Bounds of the area of interest
        
    Returns:
        Dictionary with spatial analysis metrics
    """
    try:
        if gdf.empty:
            return {'feature_count': 0, 'coverage_ratio': 0.0, 'density': 0.0}
        
        # Create AOI polygon for analysis
        aoi_polygon = bounds_to_polygon(aoi_bounds)
        aoi_gdf = gpd.GeoDataFrame([1], geometry=[aoi_polygon], crs=gdf.crs)
        
        # Calculate basic metrics
        total_features = len(gdf)
        aoi_area = aoi_gdf.geometry.area.iloc[0]
        
        # Calculate coverage ratio (for polygon features)
        if gdf.geometry.geom_type.iloc[0] in ['Polygon', 'MultiPolygon']:
            total_feature_area = gdf.geometry.area.sum()
            coverage_ratio = min(total_feature_area / aoi_area, 1.0) if aoi_area > 0 else 0.0
        else:
            coverage_ratio = 0.0
        
        # Calculate spatial density (features per unit area)
        density = total_features / aoi_area if aoi_area > 0 else 0.0
        
        # Calculate centroid distribution
        centroids = gdf.geometry.centroid
        
        # Calculate spatial extent metrics
        feature_bounds = gdf.total_bounds
        extent_coverage = {
            'width_ratio': (feature_bounds[2] - feature_bounds[0]) / (aoi_bounds[2] - aoi_bounds[0]),
            'height_ratio': (feature_bounds[3] - feature_bounds[1]) / (aoi_bounds[3] - aoi_bounds[1])
        }
        
        return {
            'feature_count': total_features,
            'coverage_ratio': coverage_ratio,
            'density': density,
            'aoi_area': aoi_area,
            'extent_coverage': extent_coverage,
            'feature_bounds': feature_bounds.tolist(),
            'geometry_types': gdf.geometry.geom_type.value_counts().to_dict()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing spatial distribution: {e}")
        return {'error': str(e)}


def optimize_feature_density(gdf: gpd.GeoDataFrame, target_density: float = 1000, 
                           method: str = 'random') -> gpd.GeoDataFrame:
    """
    Optimize feature density by sampling or aggregating features
    
    Args:
        gdf: Input GeoDataFrame
        target_density: Target number of features
        method: Optimization method ('random', 'systematic', 'cluster')
        
    Returns:
        Optimized GeoDataFrame
    """
    try:
        if len(gdf) <= target_density:
            return gdf
        
        logger.info(f"Optimizing feature density from {len(gdf)} to {target_density} using {method} method")
        
        if method == 'random':
            return gdf.sample(n=int(target_density), random_state=42)
        
        elif method == 'systematic':
            # Systematic sampling - take every nth feature
            step = len(gdf) // int(target_density)
            indices = range(0, len(gdf), step)[:int(target_density)]
            return gdf.iloc[indices]
        
        elif method == 'cluster':
            # Cluster-based sampling (simplified clustering by spatial proximity)
            # Use k-means clustering on centroid coordinates
            try:
                from sklearn.cluster import KMeans
                
                # Get centroids for clustering
                centroids = np.array([[geom.centroid.x, geom.centroid.y] for geom in gdf.geometry])
                
                # Perform clustering
                kmeans = KMeans(n_clusters=int(target_density), random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(centroids)
                
                # Select one representative feature from each cluster
                selected_indices = []
                for cluster_id in range(int(target_density)):
                    cluster_mask = cluster_labels == cluster_id
                    if cluster_mask.any():
                        # Select the feature closest to cluster center
                        cluster_indices = np.where(cluster_mask)[0]
                        cluster_center = kmeans.cluster_centers_[cluster_id]
                        
                        distances = np.sqrt(
                            (centroids[cluster_indices, 0] - cluster_center[0])**2 + 
                            (centroids[cluster_indices, 1] - cluster_center[1])**2
                        )
                        closest_idx = cluster_indices[np.argmin(distances)]
                        selected_indices.append(closest_idx)
                
                return gdf.iloc[selected_indices]
                
            except ImportError:
                logger.warning("scikit-learn not available for cluster sampling, using random sampling")
                return gdf.sample(n=int(target_density), random_state=42)
        
        else:
            logger.warning(f"Unknown optimization method '{method}', using random sampling")
            return gdf.sample(n=int(target_density), random_state=42)
            
    except Exception as e:
        logger.error(f"Error optimizing feature density: {e}")
        return gdf


def calculate_spatial_statistics(gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
    """
    Calculate comprehensive spatial statistics for a GeoDataFrame
    
    Args:
        gdf: Input GeoDataFrame
        
    Returns:
        Dictionary with spatial statistics
    """
    try:
        if gdf.empty:
            return {'error': 'Empty GeoDataFrame'}
        
        stats = {}
        
        # Basic statistics
        stats['feature_count'] = len(gdf)
        stats['geometry_types'] = gdf.geometry.geom_type.value_counts().to_dict()
        
        # Bounds and extent
        bounds = gdf.total_bounds
        stats['bounds'] = {
            'minx': bounds[0], 'miny': bounds[1],
            'maxx': bounds[2], 'maxy': bounds[3]
        }
        stats['extent'] = {
            'width': bounds[2] - bounds[0],
            'height': bounds[3] - bounds[1]
        }
        
        # CRS information
        stats['crs'] = str(gdf.crs) if gdf.crs else 'Unknown'
        
        # Geometric properties
        if gdf.geometry.geom_type.iloc[0] in ['Polygon', 'MultiPolygon']:
            areas = gdf.geometry.area
            stats['area_statistics'] = {
                'total_area': areas.sum(),
                'mean_area': areas.mean(),
                'median_area': areas.median(),
                'std_area': areas.std(),
                'min_area': areas.min(),
                'max_area': areas.max()
            }
        
        if gdf.geometry.geom_type.iloc[0] in ['LineString', 'MultiLineString']:
            lengths = gdf.geometry.length
            stats['length_statistics'] = {
                'total_length': lengths.sum(),
                'mean_length': lengths.mean(),
                'median_length': lengths.median(),
                'std_length': lengths.std(),
                'min_length': lengths.min(),
                'max_length': lengths.max()
            }
        
        # Centroid analysis
        centroids = gdf.geometry.centroid
        stats['centroid_center'] = {
            'x': centroids.x.mean(),
            'y': centroids.y.mean()
        }
        
        # Validity check
        valid_geometries = gdf.geometry.is_valid.sum()
        stats['geometry_validity'] = {
            'valid_count': valid_geometries,
            'invalid_count': len(gdf) - valid_geometries,
            'validity_ratio': valid_geometries / len(gdf)
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error calculating spatial statistics: {e}")
        return {'error': str(e)}


def create_spatial_index(gdf: gpd.GeoDataFrame, index_type: str = 'rtree') -> Optional[Any]:
    """
    Create spatial index for efficient spatial queries
    
    Args:
        gdf: Input GeoDataFrame
        index_type: Type of spatial index ('rtree', 'pygeos')
        
    Returns:
        Spatial index object or None if failed
    """
    try:
        if index_type == 'rtree':
            return gdf.sindex
        else:
            logger.warning(f"Unknown spatial index type: {index_type}")
            return gdf.sindex
            
    except Exception as e:
        logger.error(f"Error creating spatial index: {e}")
        return None


def multi_resolution_analysis(raster_path: str, resolutions: List[float], 
                            output_dir: str) -> Dict[str, str]:
    """
    Create multiple resolution versions of a raster for multi-scale analysis
    
    Args:
        raster_path: Path to input raster
        resolutions: List of target resolutions (in units of original raster)
        output_dir: Directory for output rasters
        
    Returns:
        Dictionary mapping resolutions to output file paths
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        output_files = {}
        
        base_name = os.path.splitext(os.path.basename(raster_path))[0]
        
        with rasterio.open(raster_path) as src:
            original_res = src.res[0]  # Assuming square pixels
            
            for target_res in resolutions:
                # Calculate scaling factor
                scale_factor = target_res / original_res
                
                # Calculate new dimensions
                new_width = int(src.width / scale_factor)
                new_height = int(src.height / scale_factor)
                
                # Create new transform
                new_transform = src.transform * src.transform.scale(
                    (src.width / new_width),
                    (src.height / new_height)
                )
                
                # Output file path
                output_file = os.path.join(output_dir, f"{base_name}_{target_res}m.tif")
                
                # Reproject/resample to new resolution
                with rasterio.open(
                    output_file, 'w',
                    driver='GTiff',
                    height=new_height,
                    width=new_width,
                    count=src.count,
                    dtype=src.dtype,
                    crs=src.crs,
                    transform=new_transform,
                    nodata=src.nodata
                ) as dst:
                    for i in range(1, src.count + 1):
                        reproject(
                            source=rasterio.band(src, i),
                            destination=rasterio.band(dst, i),
                            src_transform=src.transform,
                            src_crs=src.crs,
                            dst_transform=new_transform,
                            dst_crs=src.crs,
                            resampling=Resampling.bilinear
                        )
                
                output_files[f"{target_res}m"] = output_file
                logger.info(f"Created {target_res}m resolution raster: {output_file}")
        
        return output_files
        
    except Exception as e:
        logger.error(f"Error in multi-resolution analysis: {e}")
        return {}


def assess_data_quality(gdf: gpd.GeoDataFrame, aoi_bounds: Optional[Tuple[float, float, float, float]] = None) -> Dict[str, Any]:
    """
    Assess the quality of spatial data
    
    Args:
        gdf: Input GeoDataFrame
        aoi_bounds: Optional AOI bounds for coverage assessment
        
    Returns:
        Dictionary with quality assessment metrics
    """
    try:
        quality_metrics = {}
        
        # Basic completeness
        quality_metrics['completeness'] = {
            'total_features': len(gdf),
            'non_null_geometries': gdf.geometry.notna().sum(),
            'null_geometry_ratio': gdf.geometry.isna().sum() / len(gdf) if len(gdf) > 0 else 0
        }
        
        # Geometric validity
        if not gdf.empty:
            valid_geoms = gdf.geometry.is_valid
            quality_metrics['validity'] = {
                'valid_geometries': valid_geoms.sum(),
                'invalid_geometries': (~valid_geoms).sum(),
                'validity_ratio': valid_geoms.mean()
            }
            
            # Geometric complexity
            if gdf.geometry.geom_type.iloc[0] in ['Polygon', 'MultiPolygon']:
                # For polygons, check for holes and complexity
                has_holes = gdf.geometry.apply(lambda g: any(len(poly.interiors) > 0 for poly in (g.geoms if hasattr(g, 'geoms') else [g])))
                quality_metrics['complexity'] = {
                    'features_with_holes': has_holes.sum(),
                    'hole_ratio': has_holes.mean()
                }
        
        # Attribute completeness (if applicable)
        if not gdf.empty and len(gdf.columns) > 1:  # More than just geometry
            attr_columns = [col for col in gdf.columns if col != 'geometry']
            null_ratios = {}
            for col in attr_columns:
                null_ratio = gdf[col].isna().sum() / len(gdf)
                null_ratios[col] = null_ratio
            
            quality_metrics['attribute_completeness'] = {
                'attribute_columns': len(attr_columns),
                'null_ratios': null_ratios,
                'overall_completeness': 1 - np.mean(list(null_ratios.values()))
            }
        
        # Spatial coverage (if AOI provided)
        if aoi_bounds and not gdf.empty:
            coverage_analysis = analyze_spatial_distribution(gdf, aoi_bounds)
            quality_metrics['spatial_coverage'] = coverage_analysis
        
        # Overall quality score (0-1)
        validity_score = quality_metrics.get('validity', {}).get('validity_ratio', 1.0)
        completeness_score = 1 - quality_metrics['completeness']['null_geometry_ratio']
        attribute_score = quality_metrics.get('attribute_completeness', {}).get('overall_completeness', 1.0)
        
        overall_quality = np.mean([validity_score, completeness_score, attribute_score])
        quality_metrics['overall_quality_score'] = overall_quality
        
        # Quality rating
        if overall_quality >= 0.9:
            rating = 'Excellent'
        elif overall_quality >= 0.75:
            rating = 'Good'
        elif overall_quality >= 0.6:
            rating = 'Fair'
        else:
            rating = 'Poor'
        
        quality_metrics['quality_rating'] = rating
        
        return quality_metrics
        
    except Exception as e:
        logger.error(f"Error assessing data quality: {e}")
        return {'error': str(e)}


def smart_coordinate_transformation(gdf: gpd.GeoDataFrame, target_crs: Union[str, int], 
                                  preserve_area: bool = True) -> gpd.GeoDataFrame:
    """
    Intelligently transform coordinates with optimizations for different geometry types
    
    Args:
        gdf: Input GeoDataFrame
        target_crs: Target coordinate reference system
        preserve_area: Whether to use area-preserving transformations when possible
        
    Returns:
        Transformed GeoDataFrame
    """
    try:
        if gdf.crs == target_crs:
            return gdf
        
        logger.info(f"Smart transformation from {gdf.crs} to {target_crs}")
        
        # For geographic data, consider using appropriate projections
        if preserve_area and str(target_crs).upper() == 'AUTO':
            # Automatically determine best projection
            bounds = gdf.total_bounds
            utm_crs = estimate_utm_crs(bounds)
            logger.info(f"Auto-selected UTM CRS: {utm_crs}")
            target_crs = utm_crs
        
        # Perform transformation
        transformed_gdf = gdf.to_crs(target_crs)
        
        # Validate transformation quality
        original_bounds = gdf.total_bounds
        new_bounds = transformed_gdf.total_bounds
        
        # Log transformation metrics
        logger.info(f"Transformation completed:")
        logger.info(f"  Original extent: {original_bounds}")
        logger.info(f"  New extent: {new_bounds}")
        
        return transformed_gdf
        
    except Exception as e:
        logger.error(f"Error in coordinate transformation: {e}")
        return gdf


def create_processing_mask(gdf: gpd.GeoDataFrame, buffer_distance: float = 0) -> gpd.GeoDataFrame:
    """
    Create a processing mask from input geometries with optional buffer
    
    Args:
        gdf: Input GeoDataFrame
        buffer_distance: Buffer distance around geometries
        
    Returns:
        GeoDataFrame with unified mask geometry
    """
    try:
        if gdf.empty:
            return gdf
        
        # Ensure valid geometries
        gdf = validate_geometry(gdf, fix_invalid=True)
        
        # Apply buffer if requested
        if buffer_distance > 0:
            logger.info(f"Applying {buffer_distance} unit buffer to mask geometries")
            buffered_geoms = gdf.geometry.buffer(buffer_distance)
        else:
            buffered_geoms = gdf.geometry
        
        # Union all geometries into single mask
        unified_geometry = unary_union(buffered_geoms.values)
        
        # Create new GeoDataFrame with unified mask
        mask_gdf = gpd.GeoDataFrame(
            [{'mask_id': 1}], 
            geometry=[unified_geometry], 
            crs=gdf.crs
        )
        
        logger.info(f"Created unified processing mask from {len(gdf)} features")
        
        return mask_gdf
        
    except Exception as e:
        logger.error(f"Error creating processing mask: {e}")
        return gdf
