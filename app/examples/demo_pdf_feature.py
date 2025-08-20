#!/usr/bin/env python3
"""
Demonstration of PDF generation feature for NOAA Atlas 14 precipitation frequency data
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


def demonstrate_pdf_feature():
    """Demonstrate the PDF generation feature for NOAA Atlas 14 data"""
    
    print("🎨 NOAA Atlas 14 PDF Report Generation Demo")
    print("=" * 50)
    
    # Step 1: Load AOI
    print("\n📍 Step 1: Loading AOI...")
    aoi_manager = AOIManager()
    
    if not aoi_manager.load_aoi_from_file("data/aoi.shp"):
        print("❌ Failed to load AOI")
        return False
    
    centroid = aoi_manager.get_centroid()
    print(f"✅ AOI loaded - Centroid: {centroid[1]:.4f}°N, {centroid[0]:.4f}°W")
    
    # Step 2: Download with PDF generation
    print("\n📊 Step 2: Downloading precipitation data with PDF generation...")
    downloader = NOAAAtlas14Downloader()
    
    result = downloader.download_layer(
        layer_id="pds_depth_english",
        aoi_bounds=aoi_manager.get_bounds(),
        output_path="output/demo_pdf"
    )
    
    if not result.success:
        print(f"❌ Download failed: {result.error_message}")
        return False
    
    print("✅ Download successful!")
    
    # Step 3: Show generated files
    print("\n📁 Step 3: Generated files:")
    base_name = Path(result.file_path).stem
    output_dir = Path(result.file_path).parent
    
    files_info = []
    
    # Raw CSV
    if os.path.exists(result.file_path):
        size = os.path.getsize(result.file_path) / 1024
        files_info.append(f"  • {Path(result.file_path).name} ({size:.1f} KB) - Raw NOAA data")
    
    # Processed CSV
    processed_csv = result.file_path.replace('.csv', '_processed.csv')
    if os.path.exists(processed_csv):
        size = os.path.getsize(processed_csv) / 1024
        files_info.append(f"  • {Path(processed_csv).name} ({size:.1f} KB) - Clean data table")
    
    # Metadata JSON
    metadata_json = result.file_path.replace('.csv', '_metadata.json')
    if os.path.exists(metadata_json):
        size = os.path.getsize(metadata_json) / 1024
        files_info.append(f"  • {Path(metadata_json).name} ({size:.1f} KB) - Metadata")
    
    # PDF Report
    pdf_report = result.file_path.replace('.csv', '_report.pdf')
    if os.path.exists(pdf_report):
        size = os.path.getsize(pdf_report) / 1024
        files_info.append(f"  • {Path(pdf_report).name} ({size:.1f} KB) - PDF REPORT 📄")
    
    for file_info in files_info:
        print(file_info)
    
    # Step 4: PDF Content Description
    if os.path.exists(pdf_report):
        print("\n📄 Step 4: PDF Report Contents:")
        print("  📋 Page 1: Precipitation Frequency Data Table")
        print("     • Complete precipitation frequency estimates")
        print("     • Location information (lat/lon)")
        print("     • Download timestamp")
        print("     • Data source and version info")
        print("     • Analysis parameters")
        
        print("\n  📈 Page 2: Depth-Duration-Frequency (DDF) Curves")
        print("     • Top plot: Precipitation depth vs duration (for different return periods)")
        print("     • Bottom plot: Precipitation depth vs return period (for different durations)")
        print("     • Professional styling matching NOAA Atlas 14 format")
        print("     • Color-coded legend with 10 return periods")
        
        print(f"\n🎉 PDF report successfully generated!")
        print(f"📂 Open: {os.path.abspath(pdf_report)}")
        
        # Step 5: Usage examples
        print("\n💡 Step 5: How to use the PDF:")
        print("  • Share with engineers and hydrologists")
        print("  • Include in technical reports and proposals")
        print("  • Use for design storm analysis")
        print("  • Archive for project documentation")
        
        return True
    else:
        print("❌ PDF report was not generated")
        return False


def main():
    """Main function"""
    success = demonstrate_pdf_feature()
    
    if success:
        print("\n" + "=" * 50)
        print("🎊 PDF Generation Demo Complete!")
        print("The NOAA Atlas 14 integration now automatically generates")
        print("professional PDF reports with every data download.")
        print("=" * 50)
        return 0
    else:
        print("\n❌ Demo failed")
        return 1


if __name__ == "__main__":
    exit(main()) 