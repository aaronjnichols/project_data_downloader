"""
Streamlit Application Startup Script
====================================

This script helps start the Streamlit geospatial data downloader application
with proper configuration and error checking.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    print("Checking dependencies...")
    
    required_packages = [
        'streamlit',
        'geopandas', 
        'folium',
        'streamlit_folium',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"[OK] {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"[MISSING] {package}")
    
    if missing_packages:
        print(f"\nMissing packages: {missing_packages}")
        print("\nTo install missing packages, run:")
        print("pip install -r requirements_streamlit.txt")
        return False
    
    print("All dependencies are installed!")
    return True

def check_api_server():
    """Check if FastAPI server is running"""
    print("\nChecking API server...")
    
    try:
        import requests
        
        # Try different common URLs
        api_urls = [
            "http://localhost:8000",
            "http://127.0.0.1:8000"
        ]
        
        for url in api_urls:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code == 200:
                    print(f"[OK] API server is running at {url}")
                    return True
            except:
                continue
        
        print("[WARNING] API server not detected")
        print("The Streamlit app will work but cannot download data without the API.")
        print("\nTo start the API server:")
        print("python start_api.py")
        print("or")
        print("uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload")
        
        return False
        
    except ImportError:
        print("[ERROR] Cannot check API server - requests not installed")
        return False

def start_streamlit():
    """Start the Streamlit application"""
    print("\nStarting Streamlit application...")
    
    # Check if streamlit_app.py exists
    app_file = Path("streamlit_app.py")
    if not app_file.exists():
        print("[ERROR] streamlit_app.py not found in current directory")
        print("Please run this script from the project root directory")
        return False
    
    try:
        # Start Streamlit
        cmd = [
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ]
        
        print("Running command:", " ".join(cmd))
        print("\nStreamlit will start in a few seconds...")
        print("The application will be available at: http://localhost:8501")
        print("\nPress Ctrl+C to stop the application")
        
        # Run Streamlit
        subprocess.run(cmd)
        
    except FileNotFoundError:
        print("[ERROR] Streamlit not found. Please install it:")
        print("pip install streamlit")
        return False
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to start Streamlit: {e}")
        return False

def main():
    """Main startup function"""
    print("=" * 60)
    print("STREAMLIT GEOSPATIAL DATA DOWNLOADER")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        print("\nPlease install missing dependencies and try again.")
        return 1
    
    # Check API server (warning only)
    check_api_server()
    
    # Offer to start Streamlit
    print("\n" + "-" * 40)
    response = input("Start Streamlit application? (y/n): ").lower().strip()
    
    if response in ['y', 'yes', '']:
        if start_streamlit():
            return 0
        else:
            return 1
    else:
        print("Startup cancelled by user")
        return 0

if __name__ == "__main__":
    sys.exit(main())