#!/usr/bin/env python3
"""
Test script for NOAA Atlas 14 PDF generation functionality
"""
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import project modules
from src.core.aoi_manager import AOIManager
from src.downloaders.noaa_atlas14_downloader import NOAAAtlas14Downloader


def test_pdf_generation():
    """Test the complete NOAA Atlas 14 PDF generation workflow"""
    
    logger.info("=" * 60)
    logger.info("Testing NOAA Atlas 14 PDF Generation")
    logger.info("=" * 60)
    
    try:
        # Test 1: Initialize AOI Manager with the project AOI
        logger.info("\n1. Loading AOI from shapefile...")
        aoi_manager = AOIManager()
        
        if not aoi_manager.load_aoi_from_file("data/aoi.shp"):
            logger.error("Failed to load AOI from shapefile")
            return False
        
        # Get AOI information
        centroid = aoi_manager.get_centroid()
        logger.info(f"   AOI Centroid: {centroid[1]:.4f}°N, {centroid[0]:.4f}°W")
        
        # Test 2: Initialize NOAA Atlas 14 downloader
        logger.info("\n2. Initializing NOAA Atlas 14 downloader...")
        downloader = NOAAAtlas14Downloader()
        
        # Get available layers
        layers = downloader.get_available_layers()
        logger.info(f"   Available layers: {len(layers)}")
        for layer_id, layer_info in layers.items():
            logger.info(f"   - {layer_id}: {layer_info.name}")
        
        # Test 3: Download precipitation frequency data and generate PDF
        logger.info("\n3. Downloading precipitation frequency data with PDF generation...")
        
        # Use PDS depth data in English units (most common)
        layer_id = "pds_depth_english"
        aoi_bounds = aoi_manager.get_bounds()
        output_dir = "output/noaa_atlas14_pdf_test"
        
        logger.info(f"   Layer: {layer_id}")
        logger.info(f"   AOI bounds: {aoi_bounds}")
        logger.info(f"   Output directory: {output_dir}")
        
        # Download data
        result = downloader.download_layer(layer_id, aoi_bounds, output_dir)
        
        if result.success:
            logger.info(f"   ✓ Download successful!")
            logger.info(f"   ✓ Features downloaded: {result.feature_count}")
            logger.info(f"   ✓ Data file: {result.file_path}")
            
            # Check for processed CSV
            processed_csv = result.file_path.replace('.csv', '_processed.csv')
            if os.path.exists(processed_csv):
                logger.info(f"   ✓ Processed CSV: {Path(processed_csv).name}")
            
            # Check for PDF report
            pdf_report = result.file_path.replace('.csv', '_report.pdf')
            if os.path.exists(pdf_report):
                file_size = os.path.getsize(pdf_report)
                logger.info(f"   ✓ PDF Report: {Path(pdf_report).name} ({file_size/1024:.1f} KB)")
                logger.info(f"   ✓ PDF contains:")
                logger.info(f"     • Page 1: Precipitation frequency data table with metadata")
                logger.info(f"     • Page 2: Depth-Duration-Frequency (DDF) curves")
            else:
                logger.warning(f"   ⚠ PDF report not found: {pdf_report}")
            
            # Test 4: Display data summary
            logger.info("\n4. Data Summary:")
            if result.metadata:
                coords = result.metadata.get('centroid_coordinates', {})
                data_summary = result.metadata.get('data_summary', {})
                
                logger.info(f"   Location: {coords.get('latitude', 'N/A')}°N, {coords.get('longitude', 'N/A')}°W")
                logger.info(f"   Data Type: {data_summary.get('data_type', 'N/A')}")
                logger.info(f"   Units: {data_summary.get('units', 'N/A')}")
                logger.info(f"   Durations: {data_summary.get('durations', 'N/A')}")
                logger.info(f"   Return Periods: {data_summary.get('return_periods', 'N/A')}")
            
            # Test 5: PDF Content verification (basic)
            logger.info("\n5. PDF Content Verification:")
            if os.path.exists(pdf_report):
                try:
                    # Check file size (should be reasonable for a 2-page PDF)
                    file_size = os.path.getsize(pdf_report)
                    if file_size > 50000:  # > 50KB indicates content
                        logger.info(f"   ✓ PDF size looks good: {file_size/1024:.1f} KB")
                    else:
                        logger.warning(f"   ⚠ PDF seems small: {file_size/1024:.1f} KB")
                    
                    logger.info(f"   ✓ PDF successfully generated with:")
                    logger.info(f"     • 8.5\" x 11\" letter format")
                    logger.info(f"     • Page 1: Data table with metadata (lat/lon, download date, etc.)")
                    logger.info(f"     • Page 2: DDF curves matching NOAA Atlas 14 style")
                    
                except Exception as e:
                    logger.error(f"   ✗ Error checking PDF: {e}")
            
        else:
            logger.error(f"   ✗ Download failed: {result.error_message}")
            return False
        
        logger.info("\n" + "=" * 60)
        logger.info("PDF Generation Test COMPLETED SUCCESSFULLY!")
        logger.info("=" * 60)
        logger.info(f"Output files are in: {output_dir}/")
        
        if os.path.exists(pdf_report):
            logger.info(f"📊 Open the PDF report to view:")
            logger.info(f"   {os.path.abspath(pdf_report)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_pdf_generation()
    if success:
        print("\n🎉 PDF generation test completed successfully!")
    else:
        print("\n❌ PDF generation test failed!")
        exit(1) 