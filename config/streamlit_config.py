"""
Configuration settings for the Streamlit Geospatial Data Downloader
==================================================================

This module contains configuration settings and constants used throughout
the Streamlit application for the geospatial data downloader.

Features:
- Environment-based configuration
- API endpoint settings
- Application defaults
- Display preferences
- File handling settings
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import streamlit as st

class Config:
    """
    Configuration class for the Streamlit application
    
    This class manages all configuration settings for the application,
    including API endpoints, file paths, and UI preferences.
    """
    
    # API Configuration
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
    API_RETRIES = int(os.getenv("API_RETRIES", "3"))
    
    # Application Information
    APP_NAME = "Geospatial Data Downloader"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "Professional geospatial data acquisition from FEMA, USGS, and NOAA sources"
    
    # Page Configuration
    PAGE_TITLE = "🗺️ Geospatial Data Downloader"
    PAGE_ICON = "🗺️"
    LAYOUT = "wide"
    INITIAL_SIDEBAR_STATE = "expanded"
    
    # File Upload Settings
    MAX_UPLOAD_SIZE_MB = 50
    ALLOWED_SHAPEFILE_EXTENSIONS = ['shp', 'shx', 'dbf', 'prj', 'cpg']
    REQUIRED_SHAPEFILE_EXTENSIONS = ['shp', 'shx', 'dbf']
    
    # Map Configuration
    DEFAULT_MAP_CENTER = [39.8283, -98.5795]  # Continental US center
    DEFAULT_MAP_ZOOM = 4
    AOI_MAP_ZOOM = 10
    MAP_WIDTH = 700
    MAP_HEIGHT = 500
    PREVIEW_MAP_HEIGHT = 400
    
    # Data Source Information
    DATA_SOURCES = {
        'fema': {
            'name': 'FEMA NFHL',
            'full_name': 'Federal Emergency Management Agency - National Flood Hazard Layer',
            'description': 'Flood hazard mapping data including Special Flood Hazard Areas (SFHA), Base Flood Elevations (BFE), and regulatory floodway information.',
            'color': '#007bff',
            'icon': '🌊'
        },
        'usgs_lidar': {
            'name': 'USGS LiDAR',
            'full_name': 'U.S. Geological Survey - 3D Elevation Program',
            'description': 'High-resolution digital elevation models derived from LiDAR data, with optional contour generation.',
            'color': '#28a745',
            'icon': '⛰️'
        },
        'noaa_atlas14': {
            'name': 'NOAA Atlas 14',
            'full_name': 'National Oceanic and Atmospheric Administration - Precipitation Frequency Atlas',
            'description': 'Precipitation frequency data with depth-duration-frequency curves and statistical analysis.',
            'color': '#6f42c1',
            'icon': '🌧️'
        }
    }
    
    # Job Status Configuration
    JOB_STATUS_COLORS = {
        'pending': '#ffc107',      # Yellow
        'running': '#17a2b8',      # Blue
        'completed': '#28a745',    # Green
        'failed': '#dc3545'        # Red
    }
    
    JOB_STATUS_ICONS = {
        'pending': '⏳',
        'running': '🔄',
        'completed': '✅',
        'failed': '❌'
    }
    
    # Progress Monitoring
    JOB_POLL_INTERVAL = 1  # seconds
    MAX_JOB_WAIT_TIME = 300  # 5 minutes
    PROGRESS_UPDATE_INTERVAL = 0.5  # seconds
    
    # File Download Settings
    DOWNLOAD_CHUNK_SIZE = 8192
    TEMP_DIR = Path(os.getenv("TEMP_DIR", Path.cwd() / "temp"))
    
    # UI Preferences
    SUCCESS_MESSAGE_DURATION = 3  # seconds
    ERROR_MESSAGE_DURATION = 5  # seconds
    INFO_MESSAGE_DURATION = 3  # seconds
    
    # Feature Limits
    PREVIEW_MAX_FEATURES = 100
    MAP_MAX_FEATURES = 1000
    TABLE_MAX_ROWS = 500
    
    # Coordinate System Settings
    DEFAULT_CRS = 'EPSG:4326'  # WGS84
    DISPLAY_CRS = 'EPSG:4326'
    
    # Validation Settings
    MIN_AOI_AREA_KM2 = 0.001  # Minimum AOI area in km²
    MAX_AOI_AREA_KM2 = 10000  # Maximum AOI area in km²
    
    # Development Settings
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def get_data_source_info(cls, source_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific data source
        
        Args:
            source_id: ID of the data source
            
        Returns:
            Data source information dictionary or None if not found
        """
        return cls.DATA_SOURCES.get(source_id)
    
    @classmethod
    def get_status_color(cls, status: str) -> str:
        """
        Get color for job status
        
        Args:
            status: Job status string
            
        Returns:
            Color code for the status
        """
        return cls.JOB_STATUS_COLORS.get(status, '#6c757d')
    
    @classmethod
    def get_status_icon(cls, status: str) -> str:
        """
        Get icon for job status
        
        Args:
            status: Job status string
            
        Returns:
            Icon emoji for the status
        """
        return cls.JOB_STATUS_ICONS.get(status, '❓')
    
    @classmethod
    def ensure_temp_dir(cls) -> Path:
        """
        Ensure temporary directory exists
        
        Returns:
            Path to temporary directory
        """
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        return cls.TEMP_DIR
    
    @classmethod
    def validate_aoi_bounds(cls, bounds: Dict[str, float]) -> tuple[bool, str]:
        """
        Validate AOI bounds
        
        Args:
            bounds: Dictionary with minx, miny, maxx, maxy keys
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            minx, miny, maxx, maxy = bounds['minx'], bounds['miny'], bounds['maxx'], bounds['maxy']
            
            # Check coordinate validity
            if not (-180 <= minx <= 180) or not (-180 <= maxx <= 180):
                return False, "Longitude must be between -180 and 180"
            
            if not (-90 <= miny <= 90) or not (-90 <= maxy <= 90):
                return False, "Latitude must be between -90 and 90"
            
            # Check bounds order
            if minx >= maxx:
                return False, "Minimum longitude must be less than maximum longitude"
            
            if miny >= maxy:
                return False, "Minimum latitude must be less than maximum latitude"
            
            # Calculate approximate area
            width = maxx - minx
            height = maxy - miny
            area_km2 = width * height * 111.32 * 111.32  # Rough conversion to km²
            
            if area_km2 < cls.MIN_AOI_AREA_KM2:
                return False, f"AOI too small (minimum: {cls.MIN_AOI_AREA_KM2} km²)"
            
            if area_km2 > cls.MAX_AOI_AREA_KM2:
                return False, f"AOI too large (maximum: {cls.MAX_AOI_AREA_KM2} km²)"
            
            return True, "Valid AOI bounds"
            
        except KeyError as e:
            return False, f"Missing required bound: {e}"
        except Exception as e:
            return False, f"Invalid bounds: {str(e)}"

class StyleConfig:
    """
    CSS and styling configuration for the Streamlit application
    """
    
    # Custom CSS styles
    CUSTOM_CSS = """
    <style>
        /* Main header styling */
        .main-header {
            font-size: 2.5rem;
            font-weight: 700;
            color: #1f1f1f;
            margin-bottom: 0.5rem;
            text-align: center;
        }
        
        /* Sub-header styling */
        .sub-header {
            font-size: 1.1rem;
            color: #555;
            margin-bottom: 2rem;
            text-align: center;
        }
        
        /* Status message styling */
        .status-success {
            color: #28a745;
            font-weight: 600;
        }
        
        .status-error {
            color: #dc3545;
            font-weight: 600;
        }
        
        .status-warning {
            color: #ffc107;
            font-weight: 600;
        }
        
        .status-info {
            color: #17a2b8;
            font-weight: 600;
        }
        
        /* Metric card styling */
        .metric-card {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #007bff;
            margin: 0.5rem 0;
        }
        
        /* Progress container styling */
        .progress-container {
            background-color: #f8f9fa;
            padding: 1.5rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
            border: 1px solid #dee2e6;
        }
        
        /* Data source card styling */
        .data-source-card {
            background-color: #ffffff;
            padding: 1.2rem;
            border-radius: 0.5rem;
            border: 1px solid #dee2e6;
            margin: 0.5rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* AOI info card styling */
        .aoi-info-card {
            background-color: #e3f2fd;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #2196f3;
            margin: 1rem 0;
        }
        
        /* Job status card styling */
        .job-status-card {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
            border: 1px solid #dee2e6;
        }
        
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Sidebar styling */
        .css-1d391kg {
            background-color: #f8f9fa;
        }
        
        /* Button styling */
        .stButton > button {
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 0.25rem;
            padding: 0.5rem 1rem;
            font-weight: 500;
        }
        
        .stButton > button:hover {
            background-color: #0056b3;
            border: none;
        }
        
        /* File uploader styling */
        .uploadedFile {
            background-color: #e8f5e8;
            border: 1px solid #28a745;
            border-radius: 0.25rem;
        }
        
        /* Map container styling */
        .map-container {
            border: 1px solid #dee2e6;
            border-radius: 0.5rem;
            padding: 0.5rem;
            background-color: #ffffff;
        }
    </style>
    """
    
    # Color palette
    COLORS = {
        'primary': '#007bff',
        'secondary': '#6c757d',
        'success': '#28a745',
        'danger': '#dc3545',
        'warning': '#ffc107',
        'info': '#17a2b8',
        'light': '#f8f9fa',
        'dark': '#343a40'
    }
    
    # Icon mappings
    ICONS = {
        'upload': '📁',
        'map': '🗺️',
        'download': '💾',
        'process': '⚙️',
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️',
        'refresh': '🔄',
        'preview': '👁️',
        'delete': '🗑️',
        'export': '📤'
    }

class EnvironmentConfig:
    """
    Environment-specific configuration settings
    """
    
    @staticmethod
    def is_development() -> bool:
        """Check if running in development mode"""
        return os.getenv("STREAMLIT_ENV", "development") == "development"
    
    @staticmethod
    def is_production() -> bool:
        """Check if running in production mode"""
        return os.getenv("STREAMLIT_ENV", "development") == "production"
    
    @staticmethod
    def get_api_url() -> str:
        """Get API URL based on environment"""
        if EnvironmentConfig.is_production():
            return os.getenv("PROD_API_URL", "https://project-data-downloader.onrender.com")
        else:
            return os.getenv("DEV_API_URL", "http://localhost:8000")
    
    @staticmethod
    def configure_logging():
        """Configure logging based on environment"""
        import logging
        
        if EnvironmentConfig.is_development():
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        else:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )

# Update Config class to use environment-based API URL
Config.API_BASE_URL = EnvironmentConfig.get_api_url()

# Export commonly used configurations
__all__ = [
    'Config',
    'StyleConfig', 
    'EnvironmentConfig'
]