"""USGS LiDAR/DEM downloader plugin."""
import os
import json
import zipfile
import logging
from typing import Dict, Tuple, Optional, Any, List

from src.core.base_downloader import BaseDownloader, LayerInfo, DownloadResult
from src.utils.download_utils import DownloadSession, validate_response_content
from src.utils.spatial_utils import safe_file_name, dem_to_contours, clip_raster_to_aoi


class USGSLidarDownloader(BaseDownloader):
    """Downloader for USGS 3DEP LiDAR DEM data."""

    DEM_LAYER = LayerInfo(
        id="dem",
        name="Digital Elevation Model",
        description="USGS 3DEP DEM clipped to AOI",
        geometry_type="Raster",
        data_type="Raster",
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = "https://tnmaccess.nationalmap.gov/api/v1/products"
        self.session = DownloadSession(
            max_retries=self.config.get("max_retries", 3),
            timeout=self.config.get("timeout", 300),  # Reduced to 5 minutes - better UX
        )
        
        # Enhanced configuration options
        self.preferred_resolution = self.config.get("preferred_resolution", "1m")
        self.generate_contours = self.config.get("generate_contours", True)
        self.contour_interval = self.config.get("contour_interval", 5)  # Default 5 feet
        self.export_formats = self.config.get("export_formats", ["shapefile", "dxf"])
        self.cleanup_intermediate = self.config.get("cleanup_intermediate", True)

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
        if not self._validate_layer_id(layer_id):
            return self._create_error_result(layer_id, f"Unsupported layer {layer_id}")

        minx, miny, maxx, maxy = aoi_bounds
        # Enhanced dataset selection with user preferences
        datasets = self._get_prioritized_datasets()
        
        self.logger.info(f"Searching for elevation data with preferred resolution: {self.preferred_resolution}")
        
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
            return self._create_error_result(layer_id, "No DEM available for AOI in any dataset")
        
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
                return self._create_error_result(layer_id, "Download URL not found")
            
            # Determine if this is LiDAR point cloud data
            format_type = best_item.get('format', '').upper()
            is_lidar = format_type in ['LAS', 'LAZ'] or 'lidar' in dataset_used.lower() or 'lpc' in dataset_used.lower()
            logger.info(f"Data type detected: {'LiDAR Point Cloud' if is_lidar else 'DEM Raster'}")
            
        except Exception as e:
            return self._create_error_result(layer_id, f"Invalid API response: {e}")

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
            return self._create_error_result(layer_id, "DEM download failed")

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
                return self._create_error_result(layer_id, f"Error extracting data: {e}")

        # Handle LiDAR point cloud files
        if file_type == 'lidar':
            lidar_files = [f for f in os.listdir(output_path) if f.lower().endswith((".las", ".laz"))]
            if not lidar_files:
                return self._create_error_result(layer_id, "No LiDAR file found after download")
            
            lidar_path = os.path.join(output_path, lidar_files[0])
            logger.info(f"LiDAR file ready: {lidar_path} ({os.path.getsize(lidar_path) / (1024*1024):.1f} MB)")
            logger.info("Note: LiDAR point cloud data downloaded. Consider converting to DEM for contour generation.")
            
            metadata = {
                "lidar_path": lidar_path,
                "data_type": "lidar_point_cloud",
                "note": "Raw LiDAR point cloud data - highest resolution available"
            }
            
            file_size = os.path.getsize(lidar_path) if os.path.exists(lidar_path) else None
            return self._create_success_result(
                layer_id=layer_id,
                file_path=lidar_path,
                feature_count=0,  # Point cloud feature count not applicable
                file_size_bytes=file_size,
                metadata=metadata
            )
        
        # Handle raster DEM files
        else:
            dem_files = [f for f in os.listdir(output_path) if f.lower().endswith((".tif", ".tiff", ".img"))]
            if not dem_files:
                return self._create_error_result(layer_id, "No DEM file found after download")

            dem_path = os.path.join(output_path, dem_files[0])
            logger.info(f"DEM file ready: {dem_path} ({os.path.getsize(dem_path) / (1024*1024):.1f} MB)")
            
            # Check units and convert if needed, then clip to AOI
            processed_dem_path = self._process_dem(dem_path, output_path, **kwargs)
            if not processed_dem_path:
                return self._create_error_result(layer_id, "Failed to process DEM (clipping or unit conversion)")
            
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

            # Enhanced contour generation with multiple formats
            if self.generate_contours and self.contour_interval:
                contour_results = self._generate_enhanced_contours(
                    final_dem_path, shapefile_folder, dxf_folder, metadata
                )
                metadata.update(contour_results)

            # Enhanced cleanup with user control
            if self.cleanup_intermediate:
                self._cleanup_intermediate_files(output_path, final_dem_path)
            else:
                logger.info("Keeping intermediate files as requested")

            file_size = os.path.getsize(final_dem_path) if os.path.exists(final_dem_path) else None
            return self._create_success_result(
                layer_id=layer_id,
                file_path=final_dem_path,
                feature_count=0,  # Raster data doesn't have discrete features
                file_size_bytes=file_size,
                metadata=metadata
            )

    def _process_dem(self, dem_path: str, output_path: str, **kwargs) -> Optional[str]:
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

    def _cleanup_intermediate_files(self, output_path: str, final_dem_path: str) -> None:
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
    
    def _get_prioritized_datasets(self) -> List[str]:
        """
        Get prioritized list of datasets based on user preferences
        
        Returns:
            List of dataset names in priority order
        """
        # Base datasets organized by resolution
        datasets_by_resolution = {
            "sub_meter": [
                "DEM Source (OPR)",  # Original Product Resolution DEMs
                "Seamless 1-meter DEM (Limited Availability)",
            ],
            "1m": [
                "Digital Elevation Model (DEM) 1 meter",
                "1-meter DEM",
                "3DEP Elevation: DEM (1 meter)",
            ],
            "3m": [
                "1/9 arc-second DEM",
            ],
            "10m": [
                "1/3 arc-second DEM",
                "3DEP Elevation: DEM (1/3 arc-second)",
                "National Elevation Dataset (NED) 1/3 arc-second",
            ],
            "30m": [
                "1 arc-second DEM",
                "3DEP Elevation: DEM (1 arc-second)",
                "National Elevation Dataset (NED) 1 arc-second",
            ],
            "lidar": [
                "Lidar Point Cloud (LPC)",
            ]
        }
        
        # Build priority list based on user preference
        preferred_datasets = []
        
        # Start with preferred resolution
        if self.preferred_resolution in datasets_by_resolution:
            preferred_datasets.extend(datasets_by_resolution[self.preferred_resolution])
        
        # Add other resolutions in order of quality
        resolution_order = ["sub_meter", "1m", "3m", "10m", "30m", "lidar"]
        for res in resolution_order:
            if res != self.preferred_resolution and res in datasets_by_resolution:
                preferred_datasets.extend(datasets_by_resolution[res])
        
        return preferred_datasets
    
    def _generate_enhanced_contours(self, dem_path: str, shapefile_folder: str, 
                                   dxf_folder: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate contours with enhanced options and multiple formats
        
        Args:
            dem_path: Path to DEM file
            shapefile_folder: Directory for shapefile output
            dxf_folder: Directory for DXF output
            metadata: Existing metadata dictionary
            
        Returns:
            Dictionary with contour generation results
        """
        contour_results = {}
        
        try:
            # Create output directories
            os.makedirs(shapefile_folder, exist_ok=True)
            if "dxf" in self.export_formats:
                os.makedirs(dxf_folder, exist_ok=True)
            
            # Generate shapefile contours
            if "shapefile" in self.export_formats:
                contour_name = f"contours_{safe_file_name(str(self.contour_interval))}_ft.shp"
                contour_path = os.path.join(shapefile_folder, contour_name)
                
                self.logger.info(f"Generating contours at {self.contour_interval} ft intervals...")
                success = dem_to_contours(dem_path, contour_path, self.contour_interval)
                
                if success:
                    contour_results["contour_shapefile_path"] = contour_path
                    self.logger.info(f"Generated contour shapefile: {contour_path}")
                    
                    # Generate DXF if requested and shapefile was successful
                    if "dxf" in self.export_formats:
                        dxf_results = self._convert_shapefile_to_dxf_enhanced(
                            contour_path, dxf_folder
                        )
                        contour_results.update(dxf_results)
                else:
                    self.logger.warning(f"Failed to generate contours at {self.contour_interval} ft")
                    contour_results["contour_error"] = "Contour generation failed"
            
        except Exception as e:
            self.logger.error(f"Error in enhanced contour generation: {e}")
            contour_results["contour_error"] = str(e)
        
        return contour_results
    
    def _convert_shapefile_to_dxf_enhanced(self, shapefile_path: str, dxf_folder: str) -> Dict[str, Any]:
        """
        Enhanced DXF conversion with fallback options and better error handling
        
        Args:
            shapefile_path: Path to input shapefile
            dxf_folder: Directory for DXF output
            
        Returns:
            Dictionary with conversion results
        """
        results = {}
        
        dxf_name = f"contours_{safe_file_name(str(self.contour_interval))}_ft.dxf"
        dxf_path = os.path.join(dxf_folder, dxf_name)
        
        # Try enhanced DXF conversion
        try:
            success = self._convert_to_dxf_with_ezdxf(shapefile_path, dxf_path)
            if success:
                results["contour_dxf_path"] = dxf_path
                self.logger.info(f"Created enhanced DXF: {dxf_path}")
                return results
        except Exception as e:
            self.logger.warning(f"Enhanced DXF conversion failed: {e}")
        
        # Fallback: Simple text-based DXF
        try:
            success = self._convert_to_simple_dxf(shapefile_path, dxf_path)
            if success:
                results["contour_dxf_path"] = dxf_path
                results["dxf_format"] = "simple"
                self.logger.info(f"Created simple DXF: {dxf_path}")
            else:
                results["dxf_error"] = "All DXF conversion methods failed"
        except Exception as e:
            self.logger.error(f"Simple DXF conversion failed: {e}")
            results["dxf_error"] = str(e)
        
        return results
    
    def _convert_to_dxf_with_ezdxf(self, shapefile_path: str, dxf_path: str) -> bool:
        """
        Convert using ezdxf library (enhanced version)
        
        Args:
            shapefile_path: Path to input shapefile
            dxf_path: Path for output DXF file
            
        Returns:
            True if conversion successful, False otherwise
        """
        try:
            import ezdxf
            import geopandas as gpd
            
            # Read shapefile
            gdf = gpd.read_file(shapefile_path)
            
            if gdf.empty:
                self.logger.warning("No contour features found in shapefile")
                return False
            
            # Create new DXF document with enhanced settings
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            
            # Create contour layer with enhanced attributes
            layer = doc.layers.new(
                name='CONTOURS',
                dxfattribs={
                    'color': 3,  # Green
                    'lineweight': 25,  # 0.25mm line weight
                    'description': f'Contours at {self.contour_interval} ft intervals'
                }
            )
            
            # Add text style for elevation labels
            doc.styles.new('ELEVATION_TEXT', dxfattribs={'height': 2.0})
            
            contour_count = 0
            
            # Process each contour line with enhanced attributes
            for idx, row in gdf.iterrows():
                geom = row.geometry
                elevation = row.get('ELEV', row.get('elevation', row.get('value', 0)))
                
                # Enhanced elevation value handling
                try:
                    elev_value = float(elevation)
                except (ValueError, TypeError):
                    elev_value = 0.0
                    self.logger.warning(f"Invalid elevation value at index {idx}: {elevation}")
                
                if geom.geom_type == 'LineString':
                    points = [(x, y, elev_value) for x, y in geom.coords]
                    
                    if len(points) >= 2:  # Ensure valid polyline
                        msp.add_polyline3d(
                            points=points,
                            dxfattribs={
                                'layer': 'CONTOURS',
                                'color': 3,
                                'elevation': elev_value
                            }
                        )
                        contour_count += 1
                
                elif geom.geom_type == 'MultiLineString':
                    for line in geom.geoms:
                        points = [(x, y, elev_value) for x, y in line.coords]
                        if len(points) >= 2:
                            msp.add_polyline3d(
                                points=points,
                                dxfattribs={
                                    'layer': 'CONTOURS',
                                    'color': 3,
                                    'elevation': elev_value
                                }
                            )
                            contour_count += 1
            
            # Save DXF file
            doc.saveas(dxf_path)
            self.logger.info(f"Successfully converted {contour_count} contour features to enhanced DXF")
            return True
            
        except ImportError:
            self.logger.warning("ezdxf library not available for enhanced DXF conversion")
            return False
        except Exception as e:
            self.logger.error(f"Error in enhanced DXF conversion: {e}")
            return False
    
    def _convert_to_simple_dxf(self, shapefile_path: str, dxf_path: str) -> bool:
        """
        Fallback: Create simple DXF using basic text format
        
        Args:
            shapefile_path: Path to input shapefile
            dxf_path: Path for output DXF file
            
        Returns:
            True if conversion successful, False otherwise
        """
        try:
            import geopandas as gpd
            
            gdf = gpd.read_file(shapefile_path)
            
            if gdf.empty:
                return False
            
            # Create simple DXF header and entities
            with open(dxf_path, 'w') as f:
                # Write minimal DXF header
                f.write("0\nSECTION\n2\nHEADER\n0\nENDSEC\n")
                f.write("0\nSECTION\n2\nTABLES\n0\nENDSEC\n")
                f.write("0\nSECTION\n2\nENTITIES\n")
                
                # Write contour lines as POLYLINE entities
                for idx, row in gdf.iterrows():
                    geom = row.geometry
                    elevation = row.get('ELEV', row.get('elevation', row.get('value', 0)))
                    
                    try:
                        elev_value = float(elevation)
                    except (ValueError, TypeError):
                        elev_value = 0.0
                    
                    if geom.geom_type == 'LineString':
                        coords = list(geom.coords)
                        if len(coords) >= 2:
                            f.write(f"0\nPOLYLINE\n8\nCONTOURS\n62\n3\n70\n8\n")
                            for x, y in coords:
                                f.write(f"0\nVERTEX\n8\nCONTOURS\n10\n{x:.6f}\n20\n{y:.6f}\n30\n{elev_value:.2f}\n")
                            f.write("0\nSEQEND\n")
                
                f.write("0\nENDSEC\n0\nEOF\n")
            
            self.logger.info(f"Created simple DXF with {len(gdf)} contour features")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating simple DXF: {e}")
            return False
