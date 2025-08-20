"""
Test script for Streamlit Geospatial Data Downloader Integration
===============================================================

This script tests the integration between the Streamlit frontend
and the FastAPI backend to ensure all components work together.

Run this script to verify:
- API client connectivity
- Configuration loading
- Module imports
- Basic functionality
"""

import sys
import traceback
from pathlib import Path

def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    
    try:
        import streamlit as st
        print("[PASS] Streamlit imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import Streamlit: {e}")
        return False
    
    try:
        import geopandas as gpd
        print("[PASS] GeoPandas imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import GeoPandas: {e}")
        return False
    
    try:
        import folium
        print("[PASS] Folium imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import Folium: {e}")
        return False
    
    try:
        from streamlit_folium import st_folium
        print("[PASS] Streamlit-Folium imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import Streamlit-Folium: {e}")
        return False
    
    try:
        import requests
        print("[PASS] Requests imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import Requests: {e}")
        return False
    
    return True

def test_custom_modules():
    """Test custom module imports"""
    print("\nTesting custom modules...")
    
    try:
        from api_client import GeospatialAPIClient, APIClientError
        print("[PASS] API Client imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import API Client: {e}")
        return False
    
    try:
        from streamlit_config import Config, StyleConfig, EnvironmentConfig
        print("[PASS] Configuration imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import Configuration: {e}")
        return False
    
    return True

def test_configuration():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from streamlit_config import Config
        
        # Test basic config values
        assert hasattr(Config, 'API_BASE_URL')
        assert hasattr(Config, 'APP_NAME')
        assert hasattr(Config, 'DATA_SOURCES')
        
        print(f"[PASS] API Base URL: {Config.API_BASE_URL}")
        print(f"[PASS] App Name: {Config.APP_NAME}")
        print(f"[PASS] Data Sources: {list(Config.DATA_SOURCES.keys())}")
        
        # Test configuration methods
        fema_info = Config.get_data_source_info('fema')
        assert fema_info is not None
        print(f"[PASS] FEMA data source info loaded: {fema_info['name']}")
        
        # Test bounds validation
        valid_bounds = {'minx': -105.3, 'miny': 39.9, 'maxx': -105.1, 'maxy': 40.1}
        is_valid, message = Config.validate_aoi_bounds(valid_bounds)
        assert is_valid
        print(f"[PASS] Bounds validation working: {message}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Configuration test failed: {e}")
        traceback.print_exc()
        return False

def test_api_client():
    """Test API client functionality"""
    print("\nTesting API client...")
    
    try:
        from api_client import GeospatialAPIClient, APIClientError
        from streamlit_config import Config
        
        # Create client
        client = GeospatialAPIClient(Config.API_BASE_URL)
        print(f"[PASS] API Client created for: {Config.API_BASE_URL}")
        
        # Test basic connectivity (this will fail if API is not running, which is expected)
        try:
            health = client.health_check()
            print(f"[PASS] API Health Check successful: {health}")
            
            # If API is running, test more endpoints
            try:
                downloaders = client.get_downloaders()
                print(f"[PASS] Downloaded available sources: {list(downloaders.keys())}")
            except APIClientError as e:
                print(f"[WARN] Could not get downloaders: {e}")
                
        except APIClientError as e:
            print(f"[WARN] API not reachable (expected if not running): {e}")
        
        client.close()
        print("[PASS] API Client closed successfully")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] API Client test failed: {e}")
        traceback.print_exc()
        return False

def test_streamlit_app_structure():
    """Test that the Streamlit app file has the expected structure"""
    print("\nTesting Streamlit app structure...")
    
    try:
        app_file = Path("streamlit_app.py")
        if not app_file.exists():
            print("[FAIL] streamlit_app.py not found")
            return False
        
        # Read and check for key functions
        content = app_file.read_text(encoding='utf-8')
        
        required_functions = [
            'init_session_state',
            'create_header', 
            'validate_shapefile_upload',
            'process_shapefile_upload',
            'create_map',
            'load_data_sources',
            'display_data_source_selection',
            'create_download_job',
            'monitor_job_progress',
            'display_job_results',
            'main'
        ]
        
        missing_functions = []
        for func in required_functions:
            if f"def {func}" not in content:
                missing_functions.append(func)
        
        if missing_functions:
            print(f"[FAIL] Missing functions: {missing_functions}")
            return False
        
        print("[PASS] All required functions found in streamlit_app.py")
        
        # Check for key imports
        required_imports = [
            'import streamlit as st',
            'import geopandas as gpd',
            'import folium',
            'from streamlit_folium import st_folium',
            'from api_client import GeospatialAPIClient',
            'from streamlit_config import Config'
        ]
        
        missing_imports = []
        for imp in required_imports:
            if imp not in content:
                missing_imports.append(imp)
        
        if missing_imports:
            print(f"[FAIL] Missing imports: {missing_imports}")
            return False
        
        print("[PASS] All required imports found in streamlit_app.py")
        return True
        
    except Exception as e:
        print(f"[FAIL] App structure test failed: {e}")
        traceback.print_exc()
        return False

def test_file_structure():
    """Test that all required files exist"""
    print("\nTesting file structure...")
    
    required_files = [
        'streamlit_app.py',
        'api_client.py', 
        'streamlit_config.py',
        'requirements_streamlit.txt'
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = Path(file_name)
        if not file_path.exists():
            missing_files.append(file_name)
        else:
            print(f"[PASS] {file_name} exists")
    
    if missing_files:
        print(f"[FAIL] Missing files: {missing_files}")
        return False
    
    print("[PASS] All required files exist")
    return True

def run_all_tests():
    """Run all tests and return overall success"""
    print("=" * 60)
    print("STREAMLIT GEOSPATIAL DATA DOWNLOADER INTEGRATION TEST")
    print("=" * 60)
    
    tests = [
        test_file_structure,
        test_imports,
        test_custom_modules,
        test_configuration,
        test_api_client,
        test_streamlit_app_structure
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"[FAIL] Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"[SUCCESS] ALL TESTS PASSED ({passed}/{total})")
        print("\nYour Streamlit application is ready to run!")
        print("\nTo start the application:")
        print("1. Install dependencies: pip install -r requirements_streamlit.txt")
        print("2. Start the FastAPI backend: python start_api.py")
        print("3. Start Streamlit: streamlit run streamlit_app.py")
        return True
    else:
        print(f"[FAIL] SOME TESTS FAILED ({passed}/{total})")
        print("\nPlease fix the failing tests before running the application.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)