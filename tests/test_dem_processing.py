#!/usr/bin/env python3
"""Test script to verify DEM processing (clipping and unit conversion)"""

import logging
import sys
import os
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_processor import DataProcessor
from utils.spatial_utils import create_contours

def test_dem_processing():
    """Test DEM processing with a smaller dataset"""
    import yaml
    from core.aoi_manager import AOIManager
    from downloaders.usgs_lidar_downloader import USGSLidarDownloader
    
    logger = logging.getLogger(__name__)
    
    # Load project config
    with open('my_project.yaml', 'r') as f:
        project_config = yaml.safe_load(f)
    
    # Load AOI
    aoi_manager = AOIManager()
    aoi_file = project_config['project']['aoi_file']
    
    if not aoi_manager.load_aoi_from_file(aoi_file):
        logger.error(f"Failed to load AOI from {aoi_file}")
        return False
    
    logger.info(f"AOI loaded: {aoi_manager.aoi_gdf.shape[0]} features")
    logger.info(f"AOI bounds: {aoi_manager.get_bounds()}")
    
    # Create USGS downloader with smaller interval for testing
    config = {
        'contour_interval': 20  # Use 20ft interval for faster testing
    }
    downloader = USGSLidarDownloader(config)
    
    # Test download and processing
    output_dir = "./output/test_dem_processing"
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("Testing USGS DEM download with clipping and unit conversion...")
    
    result = downloader.download_layer(
        layer_id="dem",
        aoi_bounds=aoi_manager.get_bounds(),
        output_path=output_dir,
        aoi_gdf=aoi_manager.aoi_gdf
    )
    
    if result.success:
        logger.info("✓ DEM processing test successful!")
        logger.info(f"  DEM file: {result.file_path}")
        
        if result.metadata and 'contour_path' in result.metadata:
            logger.info(f"  Contours file: {result.metadata['contour_path']}")
            
            # Check contour data
            contours = gpd.read_file(result.metadata['contour_path'])
            logger.info(f"  Generated {len(contours)} contour lines")
            
            if len(contours) > 0:
                elevations = contours['elevation'].unique()
                logger.info(f"  Elevation range: {elevations.min():.1f} - {elevations.max():.1f} feet")
        
        # Check if files exist and have reasonable size
        if os.path.exists(result.file_path):
            size_mb = os.path.getsize(result.file_path) / (1024*1024)
            logger.info(f"  DEM file size: {size_mb:.1f} MB")
        
        return True
    else:
        logger.error(f"✗ DEM processing test failed: {result.error_message}")
        return False

if __name__ == '__main__':
    success = test_dem_processing()
    sys.exit(0 if success else 1) 