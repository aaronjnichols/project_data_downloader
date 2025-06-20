#!/usr/bin/env python3
"""
Demonstration script for NOAA Atlas 14 integration
Shows how to download precipitation frequency data for any AOI
"""
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.aoi_manager import AOIManager
from downloaders.noaa_atlas14_downloader import NOAAAtlas14Downloader

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def download_noaa_precipitation_data(aoi_file_path: str, output_dir: str = "output/noaa_atlas14"):
    """
    Download NOAA Atlas 14 precipitation frequency data for an AOI
    
    Args:
        aoi_file_path: Path to AOI shapefile
        output_dir: Directory to save downloaded data
    """
    logger.info("🌧️  NOAA Atlas 14 Precipitation Frequency Data Downloader")
    logger.info("=" * 60)
    
    # Step 1: Load and validate AOI
    logger.info("Step 1: Loading AOI...")
    aoi_manager = AOIManager()
    
    if not aoi_manager.load_aoi_from_file(aoi_file_path):
        logger.error(f"❌ Failed to load AOI from {aoi_file_path}")
        return False
    
    # Get AOI information
    bounds = aoi_manager.get_bounds()
    centroid = aoi_manager.get_centroid()
    area_km2 = aoi_manager.get_area_km2()
    
    logger.info(f"✅ AOI loaded successfully")
    if centroid:
        logger.info(f"   📍 Centroid: {centroid[1]:.6f}°N, {centroid[0]:.6f}°W")
    if area_km2:
        logger.info(f"   📐 Area: {area_km2:.2f} km²")
    
    # Step 2: Initialize NOAA downloader
    logger.info("\nStep 2: Initializing NOAA Atlas 14 downloader...")
    config = {
        'timeout': 30,
        'max_retries': 3
    }
    noaa_downloader = NOAAAtlas14Downloader(config)
    
    # Validate AOI coverage
    if not noaa_downloader.validate_aoi(bounds):
        logger.error("❌ AOI centroid is outside NOAA Atlas 14 coverage area")
        return False
    
    logger.info("✅ AOI is within NOAA Atlas 14 coverage area")
    
    # Step 3: Download precipitation frequency data
    logger.info("\nStep 3: Downloading precipitation frequency data...")
    
    # Available layer types
    layers_to_download = [
        ("pds_depth_english", "📊 PDS Precipitation Depths (inches)"),
        ("pds_intensity_english", "⚡ PDS Precipitation Intensities (in/hr)"),
        ("ams_depth_english", "📈 AMS Precipitation Depths (inches)")
    ]
    
    os.makedirs(output_dir, exist_ok=True)
    successful_downloads = []
    
    for layer_id, description in layers_to_download:
        logger.info(f"\n   Downloading: {description}")
        
        result = noaa_downloader.download_layer(
            layer_id=layer_id,
            aoi_bounds=bounds,
            output_path=output_dir
        )
        
        if result.success:
            logger.info(f"   ✅ Downloaded: {result.file_path}")
            logger.info(f"   📋 Data: {result.feature_count} durations, {result.metadata['data_summary']['return_periods']} return periods")
            successful_downloads.append(result)
        else:
            logger.error(f"   ❌ Failed: {result.error_message}")
    
    # Step 4: Display summary
    logger.info("\n" + "=" * 60)
    logger.info(f"📊 DOWNLOAD SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total downloads: {len(successful_downloads)}/{len(layers_to_download)}")
    
    if successful_downloads:
        logger.info(f"\n📁 Output directory: {output_dir}")
        logger.info("\n📋 Downloaded files:")
        
        for result in successful_downloads:
            file_name = os.path.basename(result.file_path)
            logger.info(f"   • {file_name}")
            
            # Check for processed file
            processed_file = result.file_path.replace('.csv', '_processed.csv')
            if os.path.exists(processed_file):
                logger.info(f"   • {os.path.basename(processed_file)} (processed table)")
            
            # Check for metadata file
            metadata_file = result.file_path.replace('.csv', '_metadata.json')
            if os.path.exists(metadata_file):
                logger.info(f"   • {os.path.basename(metadata_file)} (metadata)")
        
        # Show example of how to use the data
        logger.info("\n💡 Usage Example:")
        first_result = successful_downloads[0]
        processed_file = first_result.file_path.replace('.csv', '_processed.csv')
        
        if os.path.exists(processed_file):
            logger.info("   To analyze the precipitation frequency data:")
            logger.info(f"   >>> import pandas as pd")
            logger.info(f"   >>> df = pd.read_csv('{processed_file}')")
            logger.info(f"   >>> print(df.head())")
            
            # Show a sample of the data
            try:
                import pandas as pd
                df = pd.read_csv(processed_file)
                logger.info(f"\n📋 Sample precipitation data (first 5 durations):")
                logger.info(df.head().to_string(index=False))
                
                logger.info(f"\n🎯 Key insights from your AOI:")
                logger.info(f"   • 100-year 24-hour precipitation: {df[df['Duration'] == '24-hr']['100_year'].iloc[0]} inches")
                logger.info(f"   • 10-year 1-hour precipitation: {df[df['Duration'] == '60-min']['10_year'].iloc[0]} inches")
                logger.info(f"   • 2-year 6-hour precipitation: {df[df['Duration'] == '6-hr']['2_year'].iloc[0]} inches")
                
            except Exception as e:
                logger.warning(f"Could not display sample data: {e}")
        
        logger.info(f"\n🎉 Successfully downloaded NOAA Atlas 14 precipitation frequency data!")
        return True
    else:
        logger.error("❌ No data was successfully downloaded")
        return False


def main():
    """Main demonstration function"""
    # Use the existing AOI file
    aoi_file = "data/aoi.shp"
    
    if not os.path.exists(aoi_file):
        logger.error(f"AOI file not found: {aoi_file}")
        return 1
    
    success = download_noaa_precipitation_data(aoi_file)
    
    if success:
        logger.info("\n✨ Integration complete! Your AOI now has precipitation frequency data.")
        return 0
    else:
        logger.error("\n❌ Integration failed. Please check the logs above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 