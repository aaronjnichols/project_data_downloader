"""
Data processing functionality for the multi-source geospatial downloader.
Handles clipping, validation, format conversion, and output organization.
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import geopandas as gpd
from pathlib import Path
import logging

from core.aoi_manager import AOIManager
from core.base_downloader import DownloadResult
from utils.spatial_utils import clip_vector_to_aoi, clip_raster_to_aoi, validate_geometry, safe_file_name

logger = logging.getLogger(__name__)


class DataProcessor:
    """Handles data processing operations for downloaded geospatial data"""
    
    def __init__(self, output_base_path: str):
        """
        Initialize data processor
        
        Args:
            output_base_path: Base directory for all output files
        """
        self.output_base_path = Path(output_base_path)
        self.download_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def create_output_structure(self, project_name: str = None) -> Dict[str, Path]:
        """
        Create organized output directory structure
        
        Args:
            project_name: Optional project name for organization
            
        Returns:
            Dictionary mapping structure names to paths
        """
        if project_name:
            base_dir = self.output_base_path / safe_file_name(project_name)
        else:
            base_dir = self.output_base_path / f"download_{self.download_session_id}"
        
        structure = {
            'base': base_dir,
            'fema': base_dir / 'fema',
            'usgs_lidar': base_dir / 'usgs_lidar',
            'nlcd': base_dir / 'nlcd', 
            'nrcs_soils': base_dir / 'nrcs_soils',
            'metadata': base_dir / 'metadata',
            'logs': base_dir / 'logs'
        }
        
        # Create all directories
        for path in structure.values():
            path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created output structure at: {base_dir}")
        return structure
    
    def process_download_result(self, result: DownloadResult, source_name: str,
                              aoi_manager: AOIManager, output_structure: Dict[str, Path]) -> bool:
        """
        Process a download result - validate, clip, and organize
        
        Args:
            result: Download result from a downloader
            source_name: Name of the data source
            aoi_manager: AOI manager for clipping operations
            output_structure: Output directory structure
            
        Returns:
            True if processing successful, False otherwise
        """
        if not result.success:
            logger.warning(f"Skipping failed download: {result.error_message}")
            return False
        
        try:
            # Get appropriate output directory
            source_dir = output_structure.get(source_name.lower(), output_structure['base'])
            
            # For vector data, perform additional validation and clipping
            if result.file_path and result.file_path.endswith('.shp'):
                return self._process_vector_file(result, aoi_manager, source_dir)
            
            # For raster data
            elif result.file_path and any(result.file_path.endswith(ext) for ext in ['.tif', '.tiff']):
                return self._process_raster_file(result, aoi_manager, source_dir)
            
            # For other file types, just move to appropriate directory
            else:
                return self._process_other_file(result, source_dir)
                
        except Exception as e:
            logger.error(f"Error processing download result for {result.layer_id}: {e}")
            return False
    
    def _process_vector_file(self, result: DownloadResult, aoi_manager: AOIManager, 
                           output_dir: Path) -> bool:
        """Process vector file (shapefile)"""
        try:
            # Read the vector file
            gdf = gpd.read_file(result.file_path)
            
            # Validate geometries
            gdf = validate_geometry(gdf, fix_invalid=True)
            
            # Additional clipping if needed
            if aoi_manager.is_loaded():
                aoi_gdf = aoi_manager.get_geometry()
                clipped_gdf = clip_vector_to_aoi(gdf, aoi_gdf)
                
                if clipped_gdf is not None and len(clipped_gdf) > 0:
                    gdf = clipped_gdf
                else:
                    logger.warning(f"No features remain after clipping for {result.layer_id}")
                    return False
            
            # Save to organized location
            output_file = output_dir / Path(result.file_path).name
            gdf.to_file(output_file)
            
            # Update result with new path
            result.file_path = str(output_file)
            result.feature_count = len(gdf)
            
            logger.info(f"Processed vector file: {output_file} ({len(gdf)} features)")
            return True
            
        except Exception as e:
            logger.error(f"Error processing vector file {result.file_path}: {e}")
            return False
    
    def _process_raster_file(self, result: DownloadResult, aoi_manager: AOIManager,
                           output_dir: Path) -> bool:
        """Process raster file"""
        try:
            output_file = output_dir / Path(result.file_path).name
            
            # If AOI clipping is needed
            if aoi_manager.is_loaded():
                aoi_gdf = aoi_manager.get_geometry()
                success = clip_raster_to_aoi(result.file_path, aoi_gdf, str(output_file))
                
                if not success:
                    # If clipping failed, just copy the file
                    import shutil
                    shutil.copy2(result.file_path, output_file)
            else:
                # Just copy the file to organized location
                import shutil
                shutil.copy2(result.file_path, output_file)
            
            # Update result with new path
            result.file_path = str(output_file)
            
            logger.info(f"Processed raster file: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing raster file {result.file_path}: {e}")
            return False
    
    def _process_other_file(self, result: DownloadResult, output_dir: Path) -> bool:
        """Process other file types"""
        try:
            output_file = output_dir / Path(result.file_path).name
            
            # Copy file to organized location
            import shutil
            shutil.copy2(result.file_path, output_file)
            
            # Update result with new path
            result.file_path = str(output_file)
            
            logger.info(f"Processed file: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing file {result.file_path}: {e}")
            return False
    
    def generate_download_summary(self, results: List[DownloadResult], 
                                output_structure: Dict[str, Path],
                                aoi_manager: AOIManager = None) -> str:
        """
        Generate a comprehensive download summary
        
        Args:
            results: List of download results
            output_structure: Output directory structure
            aoi_manager: Optional AOI manager for area information
            
        Returns:
            Path to generated summary file
        """
        try:
            summary_data = {
                "download_session": {
                    "id": self.download_session_id,
                    "timestamp": datetime.now().isoformat(),
                    "total_layers_attempted": len(results),
                    "successful_downloads": sum(1 for r in results if r.success),
                    "failed_downloads": sum(1 for r in results if not r.success)
                },
                "aoi_information": {},
                "downloads": [],
                "statistics": {}
            }
            
            # Add AOI information if available
            if aoi_manager and aoi_manager.is_loaded():
                bounds = aoi_manager.get_bounds()
                area_km2 = aoi_manager.get_area_km2()
                summary_data["aoi_information"] = {
                    "bounds": bounds,
                    "area_km2": area_km2,
                    "source_file": aoi_manager.source_file
                }
            
            # Process each download result
            total_features = 0
            source_stats = {}
            
            for result in results:
                download_info = {
                    "layer_id": result.layer_id,
                    "success": result.success,
                    "feature_count": result.feature_count,
                    "file_path": result.file_path,
                    "error_message": result.error_message,
                    "metadata": result.metadata
                }
                summary_data["downloads"].append(download_info)
                
                if result.success:
                    total_features += result.feature_count or 0
                    
                    # Extract source from layer_id or file_path
                    source = self._identify_source(result)
                    if source not in source_stats:
                        source_stats[source] = {"layers": 0, "features": 0}
                    source_stats[source]["layers"] += 1
                    source_stats[source]["features"] += result.feature_count or 0
            
            summary_data["statistics"] = {
                "total_features_downloaded": total_features,
                "by_source": source_stats
            }
            
            # Save summary to JSON file
            summary_file = output_structure['metadata'] / f"download_summary_{self.download_session_id}.json"
            with open(summary_file, 'w') as f:
                json.dump(summary_data, f, indent=2)
            
            # Also create a human-readable text summary
            text_summary_file = output_structure['metadata'] / f"download_summary_{self.download_session_id}.txt"
            self._create_text_summary(summary_data, text_summary_file)
            
            logger.info(f"Generated download summary: {summary_file}")
            return str(summary_file)
            
        except Exception as e:
            logger.error(f"Error generating download summary: {e}")
            return ""
    
    def _identify_source(self, result: DownloadResult) -> str:
        """Identify data source from download result"""
        if result.file_path:
            if 'fema' in result.file_path.lower():
                return 'fema'
            elif 'usgs' in result.file_path.lower() or 'lidar' in result.file_path.lower():
                return 'usgs_lidar'
            elif 'nlcd' in result.file_path.lower():
                return 'nlcd'
            elif 'soil' in result.file_path.lower() or 'ssurgo' in result.file_path.lower():
                return 'nrcs_soils'
        
        return 'unknown'
    
    def _create_text_summary(self, summary_data: Dict, output_file: Path) -> None:
        """Create human-readable text summary"""
        with open(output_file, 'w') as f:
            f.write("MULTI-SOURCE GEOSPATIAL DATA DOWNLOAD SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            
            session = summary_data["download_session"]
            f.write(f"Download Session: {session['id']}\n")
            f.write(f"Timestamp: {session['timestamp']}\n")
            f.write(f"Total Layers Attempted: {session['total_layers_attempted']}\n")
            f.write(f"Successful Downloads: {session['successful_downloads']}\n")
            f.write(f"Failed Downloads: {session['failed_downloads']}\n\n")
            
            # AOI Information
            aoi_info = summary_data.get("aoi_information", {})
            if aoi_info:
                f.write("AREA OF INTEREST (AOI)\n")
                f.write("-" * 30 + "\n")
                if "bounds" in aoi_info:
                    bounds = aoi_info["bounds"]
                    f.write(f"Bounds: {bounds[0]:.6f}, {bounds[1]:.6f}, {bounds[2]:.6f}, {bounds[3]:.6f}\n")
                if "area_km2" in aoi_info:
                    f.write(f"Area: {aoi_info['area_km2']:.2f} km²\n")
                if "source_file" in aoi_info:
                    f.write(f"Source File: {aoi_info['source_file']}\n")
                f.write("\n")
            
            # Statistics by source
            stats = summary_data.get("statistics", {})
            if "by_source" in stats:
                f.write("DOWNLOADS BY SOURCE\n")
                f.write("-" * 30 + "\n")
                for source, source_stats in stats["by_source"].items():
                    f.write(f"{source.upper()}: {source_stats['layers']} layers, {source_stats['features']:,} features\n")
                f.write(f"\nTOTAL FEATURES: {stats.get('total_features_downloaded', 0):,}\n\n")
            
            # Detailed download results
            f.write("DETAILED DOWNLOAD RESULTS\n")
            f.write("-" * 30 + "\n")
            for download in summary_data["downloads"]:
                status = "✓" if download["success"] else "✗"
                f.write(f"{status} {download['layer_id']}: ")
                if download["success"]:
                    f.write(f"{download.get('feature_count', 0):,} features")
                    if download.get('file_path'):
                        f.write(f" -> {Path(download['file_path']).name}")
                else:
                    f.write(f"FAILED - {download.get('error_message', 'Unknown error')}")
                f.write("\n") 