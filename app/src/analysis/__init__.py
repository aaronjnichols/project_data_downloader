"""
Analysis module for geospatial data calculations and dashboard support.

This module provides the core analysis engine for calculating:
- FEMA flood hazard area statistics
- Elevation and terrain analysis
- Precipitation data processing
- AOI-based spatial analysis
"""

from .flood_analyzer import FloodAnalyzer, FloodAnalysisResult, FloodZoneStats
from .dashboard_calculator import DashboardCalculator, AnalysisInputs, DashboardAnalysisResult

__all__ = [
    'FloodAnalyzer', 
    'FloodAnalysisResult', 
    'FloodZoneStats',
    'DashboardCalculator', 
    'AnalysisInputs', 
    'DashboardAnalysisResult'
]