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
            timeout=self.config.get("timeout", 60),
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
        # Try different DEM datasets in order of preference (highest resolution first)
        datasets = [
            "3DEP Elevation: DEM (1 meter)",
            "3DEP Elevation: DEM (1/3 arc-second)",
            "National Elevation Dataset (NED) 1/3 arc-second",
            "3DEP Elevation: DEM (1 arc-second)", 
            "National Elevation Dataset (NED) 1 arc-second"
        ]
        
        items = []
        dataset_used = None
        
        for dataset in datasets:
            params = {
                "bbox": f"{minx},{miny},{maxx},{maxy}",
                "datasets": dataset,
                "prodFormats": "GeoTIFF", 
                "outputFormat": "JSON",
                "max": 1,
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
        logger.info(f"Found DEM data using dataset: {dataset_used}")
        logger.info(f"DEM title: {items[0].get('title', 'N/A')}")
        
        try:
            download_url = items[0].get("downloadURL") or items[0].get("urls", {}).get("downloadURL")
            if not download_url:
                return DownloadResult(
                    success=False,
                    layer_id=layer_id,
                    error_message="Download URL not found",
                )
        except Exception as e:
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message=f"Invalid API response: {e}",
            )

        os.makedirs(output_path, exist_ok=True)
        
        # Determine file extension from URL or content type
        if download_url.lower().endswith('.tif') or download_url.lower().endswith('.tiff'):
            download_path = os.path.join(output_path, "usgs_dem.tif")
            is_zip = False
        else:
            download_path = os.path.join(output_path, "usgs_dem.zip") 
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
                # File might be a direct TIFF despite .zip extension
                logger.info("Downloaded file is not a ZIP, treating as direct TIFF")
                tiff_path = os.path.join(output_path, "usgs_dem.tif")
                os.rename(download_path, tiff_path)
                is_zip = False
            except Exception as e:
                return DownloadResult(
                    success=False,
                    layer_id=layer_id,
                    error_message=f"Error extracting DEM: {e}",
                )

        # Find DEM files
        dem_files = [f for f in os.listdir(output_path) if f.lower().endswith((".tif", ".tiff"))]
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
        
        metadata = {"dem_path": processed_dem_path}

        interval = self.config.get("contour_interval")
        if interval:
            contour_name = f"contours_{safe_file_name(str(interval))}_ft.shp"
            contour_path = os.path.join(output_path, contour_name)
            success = dem_to_contours(processed_dem_path, contour_path, interval)
            if success:
                metadata["contour_path"] = contour_path

        return DownloadResult(success=True, layer_id=layer_id, file_path=processed_dem_path, metadata=metadata)

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
