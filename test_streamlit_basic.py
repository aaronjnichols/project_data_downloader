"""
Basic Test Script for Streamlit Application
==========================================

This script performs basic structural tests without requiring
all dependencies to be installed.
"""

import sys
from pathlib import Path

def test_file_structure():
    """Test that all required files exist"""
    print("Testing file structure...")
    
    required_files = [
        'streamlit_app.py',
        'api_client.py', 
        'streamlit_config.py',
        'requirements_streamlit.txt',
        'STREAMLIT_README.md'
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

def test_streamlit_app_syntax():
    """Test that the Streamlit app has valid Python syntax"""
    print("\nTesting Streamlit app syntax...")
    
    try:
        app_file = Path("streamlit_app.py")
        if not app_file.exists():
            print("[FAIL] streamlit_app.py not found")
            return False
        
        # Read and check syntax
        content = app_file.read_text(encoding='utf-8')
        
        # Try to compile the code (syntax check)
        compile(content, 'streamlit_app.py', 'exec')
        print("[PASS] streamlit_app.py has valid syntax")
        
        # Check for key functions
        required_functions = [
            'def init_session_state',
            'def create_header', 
            'def validate_shapefile_upload',
            'def process_shapefile_upload',
            'def create_map',
            'def load_data_sources',
            'def display_data_source_selection',
            'def create_download_job',
            'def monitor_job_progress',
            'def display_job_results',
            'def main'
        ]
        
        missing_functions = []
        for func in required_functions:
            if func not in content:
                missing_functions.append(func)
        
        if missing_functions:
            print(f"[FAIL] Missing functions: {missing_functions}")
            return False
        
        print("[PASS] All required functions found")
        
        # Check for key imports (basic check)
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
        
        print("[PASS] All required imports found")
        return True
        
    except SyntaxError as e:
        print(f"[FAIL] Syntax error in streamlit_app.py: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Error testing streamlit_app.py: {e}")
        return False

def test_api_client_syntax():
    """Test that the API client has valid Python syntax"""
    print("\nTesting API client syntax...")
    
    try:
        client_file = Path("api_client.py")
        if not client_file.exists():
            print("[FAIL] api_client.py not found")
            return False
        
        # Read and check syntax
        content = client_file.read_text(encoding='utf-8')
        
        # Try to compile the code (syntax check)
        compile(content, 'api_client.py', 'exec')
        print("[PASS] api_client.py has valid syntax")
        
        # Check for key classes and methods
        if 'class GeospatialAPIClient' not in content:
            print("[FAIL] GeospatialAPIClient class not found")
            return False
        
        if 'class APIClientError' not in content:
            print("[FAIL] APIClientError class not found")
            return False
        
        key_methods = [
            'def health_check',
            'def get_downloaders',
            'def create_job',
            'def get_job_status',
            'def download_job_result'
        ]
        
        missing_methods = []
        for method in key_methods:
            if method not in content:
                missing_methods.append(method)
        
        if missing_methods:
            print(f"[FAIL] Missing methods: {missing_methods}")
            return False
        
        print("[PASS] All required classes and methods found")
        return True
        
    except SyntaxError as e:
        print(f"[FAIL] Syntax error in api_client.py: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Error testing api_client.py: {e}")
        return False

def test_config_syntax():
    """Test that the config has valid Python syntax"""
    print("\nTesting config syntax...")
    
    try:
        config_file = Path("streamlit_config.py")
        if not config_file.exists():
            print("[FAIL] streamlit_config.py not found")
            return False
        
        # Read and check syntax
        content = config_file.read_text(encoding='utf-8')
        
        # Try to compile the code (syntax check)
        compile(content, 'streamlit_config.py', 'exec')
        print("[PASS] streamlit_config.py has valid syntax")
        
        # Check for key classes
        required_classes = [
            'class Config',
            'class StyleConfig',
            'class EnvironmentConfig'
        ]
        
        missing_classes = []
        for cls in required_classes:
            if cls not in content:
                missing_classes.append(cls)
        
        if missing_classes:
            print(f"[FAIL] Missing classes: {missing_classes}")
            return False
        
        print("[PASS] All required classes found")
        return True
        
    except SyntaxError as e:
        print(f"[FAIL] Syntax error in streamlit_config.py: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Error testing streamlit_config.py: {e}")
        return False

def test_requirements():
    """Test that requirements file exists and has expected content"""
    print("\nTesting requirements...")
    
    try:
        req_file = Path("requirements_streamlit.txt")
        if not req_file.exists():
            print("[FAIL] requirements_streamlit.txt not found")
            return False
        
        content = req_file.read_text(encoding='utf-8')
        
        # Check for key dependencies
        required_deps = [
            'streamlit',
            'streamlit-folium',
            'geopandas',
            'folium',
            'requests'
        ]
        
        missing_deps = []
        for dep in required_deps:
            if dep not in content:
                missing_deps.append(dep)
        
        if missing_deps:
            print(f"[FAIL] Missing dependencies: {missing_deps}")
            return False
        
        print("[PASS] All required dependencies found")
        return True
        
    except Exception as e:
        print(f"[FAIL] Error testing requirements: {e}")
        return False

def run_basic_tests():
    """Run all basic tests"""
    print("=" * 60)
    print("STREAMLIT APPLICATION BASIC TESTS")
    print("=" * 60)
    
    tests = [
        test_file_structure,
        test_streamlit_app_syntax,
        test_api_client_syntax,
        test_config_syntax,
        test_requirements
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
        print(f"[SUCCESS] ALL BASIC TESTS PASSED ({passed}/{total})")
        print("\nYour Streamlit application structure is correct!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements_streamlit.txt")
        print("2. Start the FastAPI backend: python start_api.py")
        print("3. Start Streamlit: streamlit run streamlit_app.py")
        print("4. Run full integration tests: python test_streamlit_integration.py")
        return True
    else:
        print(f"[FAIL] SOME BASIC TESTS FAILED ({passed}/{total})")
        print("\nPlease fix the failing tests before proceeding.")
        return False

if __name__ == "__main__":
    success = run_basic_tests()
    sys.exit(0 if success else 1)