"""USGS LiDAR/DEM downloader plugin."""
import os
import json
import zipfile
import logging
from typing import Dict, Tuple

from core.base_downloader import BaseDownloader, LayerInfo, DownloadResult
from utils.download_utils import DownloadSession, validate_response_content
from utils.spatial_utils import safe_file_name, dem_to_contours, clip_raster_to_aoi


class USGSLidarDownloader(BaseDownloader):
    """Downloader for USGS 3DEP LiDAR DEM data."""

    DEM_LAYER = LayerInfo(
        id="dem",
        name="Digital Elevation Model",
        description="USGS 3DEP DEM clipped to AOI",
        geometry_type="Raster",
        data_type="Raster",
    )

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.base_url = "https://tnmaccess.nationalmap.gov/api/v1/products"
        self.session = DownloadSession(
            max_retries=self.config.get("max_retries", 3),
            timeout=self.config.get("timeout", 600),  # 10 minutes for large DEM downloads
        )

    @property
    def source_name(self) -> str:
        return "USGS 3DEP LiDAR"

    @property
    def source_description(self) -> str:
        return (
            "U.S. Geological Survey 3D Elevation Program LiDAR and DEM downloads"
        )

    def get_available_layers(self) -> Dict[str, LayerInfo]:
        return {"dem": self.DEM_LAYER}

    def download_layer(
        self, layer_id: str, aoi_bounds: Tuple[float, float, float, float], output_path: str, **kwargs
    ) -> DownloadResult:
        if layer_id != "dem":
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message=f"Unsupported layer {layer_id}",
            )

        minx, miny, maxx, maxy = aoi_bounds
        # Try different DEM datasets in order of preference (highest resolution DEMs first)
        # Prioritizing DEM raster formats over raw LiDAR point clouds
        datasets = [
            "DEM Source (OPR)",  # Original Product Resolution DEMs (sub-meter)
            "Digital Elevation Model (DEM) 1 meter",  # Current 3DEP name
            "1-meter DEM",  # Alternative current name
            "Seamless 1-meter DEM (Limited Availability)",
            "1/9 arc-second DEM",  # ~3m resolution (was missing)
            "3DEP Elevation: DEM (1 meter)",  # Legacy name fallback
            "1/3 arc-second DEM",  # Current name
            "3DEP Elevation: DEM (1/3 arc-second)",  # Legacy name
            "1 arc-second DEM",  # Current name  
            "3DEP Elevation: DEM (1 arc-second)",  # Legacy name
            "National Elevation Dataset (NED) 1/3 arc-second",  # Legacy fallback
            "National Elevation Dataset (NED) 1 arc-second",  # Legacy fallback
            "Lidar Point Cloud (LPC)",  # Raw LiDAR data - fallback option
        ]
        
        items = []
        dataset_used = None
        
        for dataset in datasets:
            params = {
                "bbox": f"{minx},{miny},{maxx},{maxy}",
                "datasets": dataset,
                "prodFormats": "GeoTIFF,IMG,LAS,LAZ",  # Prioritize raster formats (GeoTIFF, IMG) over LiDAR (LAS, LAZ)
                "outputFormat": "JSON",
                "max": 50,  # Increased to find more options and better coverage
            }
            
            response = self.session.get(self.base_url, params=params)
            if validate_response_content(response, ["application/json"]):
                try:
                    data = response.json()
                    items = data.get("items", [])
                    if items:
                        dataset_used = dataset
                        break
                except:
                    continue

        if not items:
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message="No DEM available for AOI in any dataset",
            )
        
        # Log which dataset was found
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Found elevation data using dataset: {dataset_used}")
        logger.info(f"Title: {items[0].get('title', 'N/A')}")
        logger.info(f"Format: {items[0].get('format', 'N/A')}")
        logger.info(f"Source Date: {items[0].get('dateCreated', 'N/A')}")
        
        # Find the best resolution item if multiple available
        best_item = items[0]
        if len(items) > 1:
            # Sort by size (larger files typically higher resolution) or date (newer typically better)
            items_with_size = [item for item in items if item.get('sizeInBytes')]
            if items_with_size:
                best_item = max(items_with_size, key=lambda x: x.get('sizeInBytes', 0))
                logger.info(f"Selected highest resolution item: {best_item.get('title', 'N/A')} ({best_item.get('sizeInBytes', 0) / (1024*1024):.1f} MB)")
        
        try:
            download_url = best_item.get("downloadURL") or best_item.get("urls", {}).get("downloadURL")
            if not download_url:
                return DownloadResult(
                    success=False,
                    layer_id=layer_id,
                    error_message="Download URL not found",
                )
            
            # Determine if this is LiDAR point cloud data
            format_type = best_item.get('format', '').upper()
            is_lidar = format_type in ['LAS', 'LAZ'] or 'lidar' in dataset_used.lower() or 'lpc' in dataset_used.lower()
            logger.info(f"Data type detected: {'LiDAR Point Cloud' if is_lidar else 'DEM Raster'}")
            
        except Exception as e:
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message=f"Invalid API response: {e}",
            )

        os.makedirs(output_path, exist_ok=True)
        
        # Determine file extension and type from URL or format
        url_lower = download_url.lower()
        if url_lower.endswith('.las'):
            download_path = os.path.join(output_path, "usgs_lidar.las")
            is_zip = False
            file_type = 'lidar'
        elif url_lower.endswith('.laz'):
            download_path = os.path.join(output_path, "usgs_lidar.laz")
            is_zip = False
            file_type = 'lidar'
        elif url_lower.endswith('.tif') or url_lower.endswith('.tiff'):
            download_path = os.path.join(output_path, "usgs_dem.tif")
            is_zip = False
            file_type = 'raster'
        elif url_lower.endswith('.img'):
            download_path = os.path.join(output_path, "usgs_dem.img")
            is_zip = False
            file_type = 'raster'
        else:
            # Default to ZIP for unknown extensions
            if is_lidar:
                download_path = os.path.join(output_path, "usgs_lidar.zip")
                file_type = 'lidar'
            else:
                download_path = os.path.join(output_path, "usgs_dem.zip")
                file_type = 'raster'
            is_zip = True

        if not self.session.download_file(download_url, download_path):
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message="DEM download failed",
            )

        # Handle ZIP files
        if is_zip:
            try:
                with zipfile.ZipFile(download_path) as zf:
                    zf.extractall(output_path)
                os.remove(download_path)  # Clean up ZIP file
            except zipfile.BadZipFile:
                # File might be a direct file despite .zip extension
                if file_type == 'lidar':
                    logger.info("Downloaded file is not a ZIP, treating as direct LiDAR file")
                    lidar_path = os.path.join(output_path, "usgs_lidar.las")
                    os.rename(download_path, lidar_path)
                else:
                    logger.info("Downloaded file is not a ZIP, treating as direct raster")
                    tiff_path = os.path.join(output_path, "usgs_dem.tif")
                    os.rename(download_path, tiff_path)
                is_zip = False
            except Exception as e:
                return DownloadResult(
                    success=False,
                    layer_id=layer_id,
                    error_message=f"Error extracting data: {e}",
                )

        # Handle LiDAR point cloud files
        if file_type == 'lidar':
            lidar_files = [f for f in os.listdir(output_path) if f.lower().endswith((".las", ".laz"))]
            if not lidar_files:
                return DownloadResult(
                    success=False,
                    layer_id=layer_id,
                    error_message="No LiDAR file found after download",
                )
            
            lidar_path = os.path.join(output_path, lidar_files[0])
            logger.info(f"LiDAR file ready: {lidar_path} ({os.path.getsize(lidar_path) / (1024*1024):.1f} MB)")
            logger.info("Note: LiDAR point cloud data downloaded. Consider converting to DEM for contour generation.")
            
            metadata = {
                "lidar_path": lidar_path,
                "data_type": "lidar_point_cloud",
                "note": "Raw LiDAR point cloud data - highest resolution available"
            }
            
            return DownloadResult(success=True, layer_id=layer_id, file_path=lidar_path, metadata=metadata)
        
        # Handle raster DEM files
        else:
            dem_files = [f for f in os.listdir(output_path) if f.lower().endswith((".tif", ".tiff", ".img"))]
            if not dem_files:
                return DownloadResult(
                    success=False,
                    layer_id=layer_id,
                    error_message="No DEM file found after download",
                )

            dem_path = os.path.join(output_path, dem_files[0])
            logger.info(f"DEM file ready: {dem_path} ({os.path.getsize(dem_path) / (1024*1024):.1f} MB)")
            
            # Check units and convert if needed, then clip to AOI
            processed_dem_path = self._process_dem(dem_path, output_path, **kwargs)
            if not processed_dem_path:
                return DownloadResult(
                    success=False,
                    layer_id=layer_id,
                    error_message="Failed to process DEM (clipping or unit conversion)",
                )
            
            # Create organized folder structure
            dem_folder = os.path.join(output_path, "DEM")
            shapefile_folder = os.path.join(output_path, "Shapefile")
            dxf_folder = os.path.join(output_path, "DXF")
            
            os.makedirs(dem_folder, exist_ok=True)
            
            # Move DEM to DEM folder
            final_dem_name = f"usgs_dem_{safe_file_name(str(self.config.get('contour_interval', 'raw')))}_ft.tif"
            final_dem_path = os.path.join(dem_folder, final_dem_name)
            
            # Move/rename the DEM file
            import shutil
            shutil.move(processed_dem_path, final_dem_path)
            
            metadata = {
                "dem_path": final_dem_path,
                "data_type": "raster_dem", 
                "dataset_used": dataset_used,
                "organized_folders": True
            }

            # Generate contours if requested
            interval = self.config.get("contour_interval")
            if interval:
                os.makedirs(shapefile_folder, exist_ok=True)
                os.makedirs(dxf_folder, exist_ok=True)
                
                # Generate shapefile contours
                contour_name = f"contours_{safe_file_name(str(interval))}_ft.shp"
                contour_path = os.path.join(shapefile_folder, contour_name)
                
                success = dem_to_contours(final_dem_path, contour_path, interval)
                if success:
                    metadata["contour_shapefile_path"] = contour_path
                    
                    # Automatically generate DXF file from shapefile
                    dxf_name = f"contours_{safe_file_name(str(interval))}_ft.dxf" 
                    dxf_path = os.path.join(dxf_folder, dxf_name)
                    
                    try:
                        # Convert shapefile to DXF using ogr2ogr (more reliable for DXF)
                        import subprocess
                        
                        # Use ogr2ogr command to convert shapefile to DXF
                        cmd = [
                            'ogr2ogr',
                            '-f', 'DXF',
                            dxf_path,
                            contour_path
                        ]
                        
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                        
                        if result.returncode == 0:
                            metadata["contour_dxf_path"] = dxf_path
                            logger.info(f"Created contour DXF: {dxf_path}")
                        else:
                            logger.warning(f"ogr2ogr failed: {result.stderr}")
                            
                    except subprocess.TimeoutExpired:
                        logger.warning("DXF conversion timed out")
                    except Exception as e:
                        logger.warning(f"Failed to create DXF file: {e}")

            # Clean up intermediate files - only keep final organized products
            self._cleanup_intermediate_files(output_path, final_dem_path)

            return DownloadResult(success=True, layer_id=layer_id, file_path=final_dem_path, metadata=metadata)

    def _process_dem(self, dem_path: str, output_path: str, **kwargs) -> str:
        """
        Process DEM: convert units from meters to feet if needed, then clip to AOI
        
        Args:
            dem_path: Path to original DEM file
            output_path: Output directory
            **kwargs: Additional arguments including aoi_gdf
            
        Returns:
            Path to processed DEM file, or None if processing failed
        """
        import rasterio
        import numpy as np
        
        logger = logging.getLogger(__name__)
        
        try:
            # Get AOI geometry from kwargs
            aoi_gdf = kwargs.get('aoi_gdf')
            if aoi_gdf is None:
                logger.warning("No AOI geometry provided, skipping clipping")
                return dem_path
            
            # Read DEM to check units and properties
            with rasterio.open(dem_path) as src:
                # Check if units are in meters (need conversion to feet)
                # Most USGS DEMs are in meters
                units = src.crs.to_dict().get('units', 'unknown')
                logger.info(f"DEM units: {units}, CRS: {src.crs}")
                
                # Assume meters if units are unknown (common for USGS data)
                needs_conversion = units in ['m', 'meter', 'metre', 'unknown'] or 'utm' in str(src.crs).lower()
                
                if needs_conversion:
                    logger.info("Converting DEM from meters to feet...")
                    
                    # Read the data
                    dem_data = src.read(1)
                    profile = src.profile.copy()
                    
                    # Convert meters to feet (1 meter = 3.28084 feet)
                    dem_data_ft = dem_data * 3.28084
                    
                    # Handle nodata values
                    if src.nodata is not None:
                        nodata_mask = dem_data == src.nodata
                        dem_data_ft[nodata_mask] = src.nodata * 3.28084 if src.nodata != -9999 else -9999
                        profile['nodata'] = src.nodata * 3.28084 if src.nodata != -9999 else -9999
                    
                    # Save converted DEM
                    converted_path = os.path.join(output_path, "usgs_dem_feet.tif")
                    with rasterio.open(converted_path, 'w', **profile) as dst:
                        dst.write(dem_data_ft, 1)
                    
                    logger.info(f"DEM converted to feet: {converted_path}")
                    dem_path = converted_path
                else:
                    logger.info("DEM already in feet or appropriate units")
            
            # Clip DEM to AOI
            clipped_path = os.path.join(output_path, "usgs_dem_clipped.tif")
            success = clip_raster_to_aoi(dem_path, aoi_gdf, clipped_path)
            
            if success:
                logger.info(f"DEM clipped to AOI: {clipped_path}")
                
                # Check if clipped DEM has data
                with rasterio.open(clipped_path) as src:
                    data = src.read(1)
                    valid_pixels = np.sum(~np.isnan(data) & (data != src.nodata) if src.nodata else ~np.isnan(data))
                    
                if valid_pixels > 0:
                    logger.info(f"Clipped DEM has {valid_pixels:,} valid elevation pixels")
                    return clipped_path
                else:
                    logger.warning("Clipped DEM has no valid data, using original")
                    return dem_path
            else:
                logger.warning("DEM clipping failed, using original")
                return dem_path
                
        except Exception as e:
            logger.error(f"Error processing DEM: {e}")
            return dem_path  # Return original on error

    def _cleanup_intermediate_files(self, output_path: str, final_dem_path: str):
        """
        Clean up intermediate DEM files, keeping only final products
        
        Args:
            output_path: Output directory containing files
            final_dem_path: Path to the final processed DEM file to keep
        """
        logger = logging.getLogger(__name__)
        
        try:
            # List of intermediate files to remove
            intermediate_patterns = [
                "usgs_dem.tif",          # Original downloaded DEM (meters, unclipped)
                "usgs_dem_feet.tif",     # Converted DEM (feet, unclipped)
                "usgs_dem.img",          # Original downloaded DEM in IMG format
                "usgs_lidar.las",        # LiDAR point cloud files (if any)
                "usgs_lidar.laz"         # Compressed LiDAR point cloud files
            ]
            
            # Get the final file name to avoid deleting it
            final_filename = os.path.basename(final_dem_path)
            
            files_removed = 0
            for filename in os.listdir(output_path):
                file_path = os.path.join(output_path, filename)
                
                # Skip if this is the final DEM file we want to keep
                if filename == final_filename:
                    continue
                    
                # Skip if this is a contour shapefile (keep all contour files)
                if filename.startswith("contours_") and filename.endswith((".shp", ".shx", ".dbf", ".prj", ".cpg")):
                    continue
                
                # Remove intermediate files
                if filename in intermediate_patterns:
                    try:
                        os.remove(file_path)
                        logger.info(f"Removed intermediate file: {filename}")
                        files_removed += 1
                    except Exception as e:
                        logger.warning(f"Could not remove intermediate file {filename}: {e}")
            
            if files_removed > 0:
                logger.info(f"Cleaned up {files_removed} intermediate files, keeping only final products")
            else:
                logger.info("No intermediate files found to clean up")
                
        except Exception as e:
            logger.warning(f"Error during file cleanup: {e}")
