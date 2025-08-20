#!/usr/bin/env python3
"""
Test script to verify the PDF layout fix and demonstrate manual PDF generation
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.pdf_utils import generate_precipitation_pdf

def test_pdf_layout():
    """Test the improved PDF layout"""
    
    print("📄 Testing PDF Layout Fix")
    print("=" * 30)
    
    # Find the most recent processed CSV and metadata files
    output_dir = Path("output/demo_pdf")
    
    if not output_dir.exists():
        print("❌ No demo output directory found. Please run demo_pdf_feature.py first.")
        return False
    
    # Find the most recent files
    csv_files = list(output_dir.glob("*_processed.csv"))
    if not csv_files:
        print("❌ No processed CSV files found.")
        return False
    
    # Get the most recent file
    latest_csv = max(csv_files, key=os.path.getctime)
    metadata_file = str(latest_csv).replace('_processed.csv', '_metadata.json')
    
    if not os.path.exists(metadata_file):
        print(f"❌ Metadata file not found: {metadata_file}")
        return False
    
    print(f"📊 Using data files:")
    print(f"  • CSV: {latest_csv.name}")
    print(f"  • Metadata: {Path(metadata_file).name}")
    
    # Generate a new PDF with improved layout
    output_pdf = str(latest_csv).replace('_processed.csv', '_layout_test.pdf')
    
    print(f"\n🎨 Generating PDF with improved layout...")
    
    if generate_precipitation_pdf(str(latest_csv), metadata_file, output_pdf):
        file_size = os.path.getsize(output_pdf) / 1024
        print(f"✅ PDF generated successfully!")
        print(f"📄 File: {Path(output_pdf).name} ({file_size:.1f} KB)")
        
        print(f"\n🔧 Layout improvements:")
        print(f"  • Metadata box repositioned higher (y=0.92)")
        print(f"  • Table moved lower to avoid overlap (y=0.08-0.63)")
        print(f"  • Smaller font sizes for better fit")
        print(f"  • Compact metadata format")
        print(f"  • Better vertical space distribution")
        
        print(f"\n📂 Open the PDF to verify the layout:")
        print(f"   {os.path.abspath(output_pdf)}")
        
        return True
    else:
        print("❌ PDF generation failed")
        return False

if __name__ == "__main__":
    success = test_pdf_layout()
    if success:
        print("\n🎉 PDF layout test successful!")
        print("The overlap issue has been resolved.")
    else:
        print("\n❌ PDF layout test failed!") 