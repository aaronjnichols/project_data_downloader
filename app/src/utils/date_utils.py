"""
Date utility functions for geospatial data processing.

This module provides utilities for handling date/time conversions commonly
encountered in geospatial data sources, particularly Unix timestamps from
ArcGIS services and other web APIs.
"""

import datetime
import pandas as pd
import numpy as np
from typing import Union, Optional
import logging

logger = logging.getLogger(__name__)


def convert_unix_timestamp(timestamp: Union[int, float, str, None], 
                          unit: str = 'ms',
                          format_string: str = '%Y-%m-%d') -> Optional[str]:
    """
    Convert Unix timestamp to readable date string
    
    Args:
        timestamp: Unix timestamp (can be int, float, string, or None)
        unit: Time unit - 'ms' for milliseconds, 's' for seconds, 'auto' for auto-detect
        format_string: Output date format (default: YYYY-MM-DD)
        
    Returns:
        Formatted date string or None if conversion fails
    """
    
    if timestamp is None or pd.isna(timestamp):
        return None
    
    try:
        # Convert to numeric if string
        if isinstance(timestamp, str):
            timestamp = float(timestamp)
        
        # Auto-detect timestamp format based on magnitude
        if unit == 'auto':
            if timestamp > 1e12:  # Larger than 1e12 suggests microseconds
                unit = 'us'
            elif timestamp > 1e9:  # Between 1e9 and 1e12 suggests milliseconds
                unit = 'ms'
            else:  # Smaller suggests seconds
                unit = 's'
        
        # Convert to seconds
        if unit == 'ms':
            timestamp = timestamp / 1000.0
        elif unit == 'us':
            timestamp = timestamp / 1000000.0
        # unit == 's' needs no conversion
        
        # Convert to datetime
        dt = datetime.datetime.fromtimestamp(timestamp)
        
        # Format as string
        return dt.strftime(format_string)
        
    except (ValueError, OSError, OverflowError) as e:
        logger.warning(f"Could not convert timestamp {timestamp}: {e}")
        return None


def convert_esri_date(timestamp: Union[int, float, str, None]) -> Optional[str]:
    """
    Convert ESRI/ArcGIS date (Unix timestamp) to readable date.
    Auto-detects whether timestamp is in seconds, milliseconds, or microseconds.
    
    Args:
        timestamp: ESRI timestamp (auto-detects format)
        
    Returns:
        Formatted date string (YYYY-MM-DD) or None if conversion fails
    """
    
    return convert_unix_timestamp(timestamp, unit='auto', format_string='%Y-%m-%d')


def convert_esri_datetime(timestamp: Union[int, float, str, None]) -> Optional[str]:
    """
    Convert ESRI/ArcGIS date to readable datetime string
    
    Args:
        timestamp: ESRI timestamp (typically milliseconds since epoch)
        
    Returns:
        Formatted datetime string (YYYY-MM-DD HH:MM:SS) or None if conversion fails
    """
    
    return convert_unix_timestamp(timestamp, unit='ms', format_string='%Y-%m-%d %H:%M:%S')


def add_readable_date_columns(gdf, date_columns: dict) -> None:
    """
    Add readable date columns to a GeoDataFrame
    
    Args:
        gdf: GeoDataFrame to modify
        date_columns: Dict mapping {original_column: new_column_name}
    
    Example:
        date_columns = {'EFF_DATE': 'effective_date', 'PRE_DATE': 'preliminary_date'}
    """
    
    for original_col, new_col in date_columns.items():
        if original_col in gdf.columns:
            logger.info(f"Converting {original_col} to readable dates in {new_col}")
            gdf[new_col] = gdf[original_col].apply(convert_esri_date)
        else:
            logger.warning(f"Column {original_col} not found in data")


def validate_esri_timestamp(timestamp: Union[int, float, str]) -> bool:
    """
    Validate if a value looks like a reasonable ESRI timestamp
    
    Args:
        timestamp: Value to validate
        
    Returns:
        True if appears to be valid ESRI timestamp
    """
    
    try:
        if pd.isna(timestamp):
            return False
            
        # Convert to numeric
        if isinstance(timestamp, str):
            timestamp = float(timestamp)
        
        # ESRI timestamps are typically 13 digits (milliseconds since epoch)
        # Range check: 1970 to 2050 (reasonable for FIRM effective dates)
        min_timestamp = 0  # 1970-01-01
        max_timestamp = 2524608000000  # 2050-01-01 in milliseconds
        
        return min_timestamp <= timestamp <= max_timestamp and len(str(int(timestamp))) >= 10
        
    except (ValueError, TypeError):
        return False


def get_date_statistics(gdf, date_column: str) -> dict:
    """
    Get statistics about dates in a GeoDataFrame column
    
    Args:
        gdf: GeoDataFrame with date data
        date_column: Column name containing dates
        
    Returns:
        Dictionary with date statistics
    """
    
    if date_column not in gdf.columns:
        return {'error': f'Column {date_column} not found'}
    
    # Convert to readable dates for analysis
    readable_dates = gdf[date_column].apply(convert_esri_date)
    valid_dates = readable_dates.dropna()
    
    if len(valid_dates) == 0:
        return {'error': 'No valid dates found'}
    
    # Convert to datetime for statistics
    dt_dates = pd.to_datetime(valid_dates)
    
    return {
        'total_records': len(gdf),
        'valid_dates': len(valid_dates),
        'invalid_dates': len(gdf) - len(valid_dates),
        'earliest_date': dt_dates.min().strftime('%Y-%m-%d'),
        'latest_date': dt_dates.max().strftime('%Y-%m-%d'),
        'unique_dates': len(dt_dates.unique()),
        'date_range_years': (dt_dates.max() - dt_dates.min()).days / 365.25
    }