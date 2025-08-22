"""
Dashboard Calculator - Main Analysis Orchestrator

This module serves as the main orchestrator for all dashboard analyses.
It coordinates data loading, analysis execution, and result aggregation
for the geospatial data analysis dashboard.

Features:
- Orchestrates flood zone analysis using FloodAnalyzer
- Manages data loading from various sources
- Handles AOI processing and validation
- Provides unified interface for dashboard calculations
- Extensible architecture for future analysis modules
"""

import os
import logging
from typing import Dict, Optional, List, Any, Union
from pathlib import Path
import geopandas as gpd
from dataclasses import dataclass

from .flood_analyzer import FloodAnalyzer, FloodAnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class AnalysisInputs:
    """Container for analysis inputs"""
    aoi_gdf: gpd.GeoDataFrame
    fema_data_path: Optional[str] = None
    usgs_data_path: Optional[str] = None
    noaa_data_path: Optional[str] = None
    output_directory: Optional[str] = None


@dataclass
class DashboardAnalysisResult:
    """Complete dashboard analysis results"""
    flood_analysis: Optional[FloodAnalysisResult] = None
    analysis_summary: Optional[str] = None
    output_files: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class DashboardCalculator:
    """
    Main calculator for dashboard analyses
    
    This class orchestrates all analysis modules and provides a unified
    interface for performing geospatial data analysis within an AOI.
    """
    
    def __init__(self):
        """Initialize the DashboardCalculator"""
        self.flood_analyzer = FloodAnalyzer()
        
    def perform_flood_analysis(self, 
                             aoi_gdf: gpd.GeoDataFrame,
                             fema_data_path: str,
                             output_directory: Optional[str] = None) -> DashboardAnalysisResult:
        """
        Perform comprehensive flood analysis within AOI
        
        Args:
            aoi_gdf: GeoDataFrame containing the Area of Interest
            fema_data_path: Path to FEMA flood hazard zones shapefile
            output_directory: Optional directory to save analysis outputs
            
        Returns:
            DashboardAnalysisResult containing flood analysis results
        """
        
        logger.info(f"Starting flood analysis with FEMA data: {fema_data_path}")
        
        try:
            # Load FEMA flood hazard zones data
            fema_gdf = self._load_fema_data(fema_data_path)
            
            if fema_gdf is None or len(fema_gdf) == 0:
                logger.warning("No FEMA flood data loaded")
                return self._create_empty_result("No FEMA flood data available")
            
            # Perform flood zone analysis
            flood_result = self.flood_analyzer.analyze_flood_zones(aoi_gdf, fema_gdf)
            
            # Generate summary report
            summary_text = self.flood_analyzer.generate_summary_report(flood_result)
            
            # Save outputs if directory provided
            output_files = {}
            if output_directory:
                output_files = self._save_flood_analysis_outputs(
                    flood_result, summary_text, output_directory
                )
            
            # Create metadata
            metadata = {
                'analysis_type': 'flood_analysis',
                'fema_data_source': fema_data_path,
                'aoi_feature_count': len(aoi_gdf),
                'fema_feature_count': len(fema_gdf),
                'output_directory': output_directory
            }
            
            logger.info("Flood analysis completed successfully")
            
            return DashboardAnalysisResult(
                flood_analysis=flood_result,
                analysis_summary=summary_text,
                output_files=output_files,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error performing flood analysis: {str(e)}")
            return self._create_error_result(f"Flood analysis failed: {str(e)}")
    
    def perform_comprehensive_analysis(self, inputs: AnalysisInputs) -> DashboardAnalysisResult:
        """
        Perform comprehensive analysis using all available data sources
        
        Args:
            inputs: AnalysisInputs containing AOI and data source paths
            
        Returns:
            DashboardAnalysisResult with all available analyses
        """
        
        logger.info("Starting comprehensive dashboard analysis")
        
        results = DashboardAnalysisResult()
        output_files = {}
        metadata = {'analysis_type': 'comprehensive'}
        
        # Perform flood analysis if FEMA data is available
        if inputs.fema_data_path and os.path.exists(inputs.fema_data_path):
            logger.info("Performing flood zone analysis")
            flood_analysis = self.perform_flood_analysis(
                inputs.aoi_gdf, 
                inputs.fema_data_path, 
                inputs.output_directory
            )
            
            if flood_analysis.flood_analysis:
                results.flood_analysis = flood_analysis.flood_analysis
                if flood_analysis.output_files:
                    output_files.update(flood_analysis.output_files)
        
        # Future: Add terrain analysis
        # if inputs.usgs_data_path and os.path.exists(inputs.usgs_data_path):
        #     logger.info("Performing terrain analysis")
        #     # TODO: Implement terrain analysis
        
        # Future: Add precipitation analysis
        # if inputs.noaa_data_path and os.path.exists(inputs.noaa_data_path):
        #     logger.info("Performing precipitation analysis")
        #     # TODO: Implement precipitation analysis
        
        # Generate comprehensive summary
        summary_text = self._generate_comprehensive_summary(results)
        
        results.analysis_summary = summary_text
        results.output_files = output_files
        results.metadata = metadata
        
        logger.info("Comprehensive analysis completed")
        
        return results
    
    def analyze_from_job_results(self, job_results_path: str) -> DashboardAnalysisResult:
        """
        Perform analysis using data from a completed download job
        
        Args:
            job_results_path: Path to job results directory containing downloaded data
            
        Returns:
            DashboardAnalysisResult with analysis of available data
        """
        
        logger.info(f"Analyzing data from job results: {job_results_path}")
        
        # Find available data files in the job results
        data_files = self._discover_data_files(job_results_path)
        
        if not data_files:
            logger.warning("No analyzable data files found in job results")
            return self._create_empty_result("No analyzable data found in job results")
        
        # Load AOI from the first available shapefile (if any)
        aoi_gdf = self._load_aoi_from_data(data_files)
        
        if aoi_gdf is None:
            logger.error("Could not determine AOI from available data")
            return self._create_error_result("Could not determine AOI for analysis")
        
        # Create analysis inputs
        inputs = AnalysisInputs(
            aoi_gdf=aoi_gdf,
            fema_data_path=data_files.get('fema'),
            usgs_data_path=data_files.get('usgs'),
            noaa_data_path=data_files.get('noaa'),
            output_directory=job_results_path
        )
        
        return self.perform_comprehensive_analysis(inputs)
    
    def _load_fema_data(self, fema_data_path: str) -> Optional[gpd.GeoDataFrame]:
        """Load FEMA flood hazard zones data"""
        
        try:
            if not os.path.exists(fema_data_path):
                logger.error(f"FEMA data file not found: {fema_data_path}")
                return None
            
            # Load the shapefile
            fema_gdf = gpd.read_file(fema_data_path)
            
            # Validate required columns
            required_columns = ['FLD_ZONE', 'geometry']
            missing_columns = [col for col in required_columns if col not in fema_gdf.columns]
            
            if missing_columns:
                logger.error(f"FEMA data missing required columns: {missing_columns}")
                return None
            
            logger.info(f"Loaded FEMA data: {len(fema_gdf)} features from {fema_data_path}")
            return fema_gdf
            
        except Exception as e:
            logger.error(f"Error loading FEMA data from {fema_data_path}: {str(e)}")
            return None
    
    def _discover_data_files(self, job_results_path: str) -> Dict[str, str]:
        """Discover available data files in job results directory"""
        
        data_files = {}
        
        if not os.path.exists(job_results_path):
            return data_files
        
        # Look for FEMA flood hazard zones
        fema_patterns = ['*Flood_Hazard_Zones*.shp', '*flood*zone*.shp']
        for pattern in fema_patterns:
            matches = list(Path(job_results_path).glob(pattern))
            if matches:
                data_files['fema'] = str(matches[0])
                break
        
        # Look for USGS DEM files
        usgs_patterns = ['*dem*.tif', '*elevation*.tif', '*usgs*.tif']
        for pattern in usgs_patterns:
            matches = list(Path(job_results_path).glob(pattern))
            if matches:
                data_files['usgs'] = str(matches[0])
                break
        
        # Look for NOAA precipitation data
        noaa_patterns = ['*noaa*.csv', '*precipitation*.csv', '*atlas*.csv']
        for pattern in noaa_patterns:
            matches = list(Path(job_results_path).glob(pattern))
            if matches:
                data_files['noaa'] = str(matches[0])
                break
        
        logger.info(f"Discovered data files: {list(data_files.keys())}")
        return data_files
    
    def _load_aoi_from_data(self, data_files: Dict[str, str]) -> Optional[gpd.GeoDataFrame]:
        """Attempt to determine AOI from available data files"""
        
        # Try to use FEMA data extent as AOI proxy
        if 'fema' in data_files:
            try:
                fema_gdf = gpd.read_file(data_files['fema'])
                # Create a simple bounding box AOI from the data extent
                bounds = fema_gdf.total_bounds
                from shapely.geometry import box
                aoi_geom = box(*bounds)
                aoi_gdf = gpd.GeoDataFrame([1], geometry=[aoi_geom], crs=fema_gdf.crs)
                
                logger.info("Created AOI from FEMA data extent")
                return aoi_gdf
                
            except Exception as e:
                logger.error(f"Error creating AOI from FEMA data: {str(e)}")
        
        return None
    
    def _save_flood_analysis_outputs(self, 
                                   flood_result: FloodAnalysisResult,
                                   summary_text: str,
                                   output_directory: str) -> Dict[str, str]:
        """Save flood analysis outputs to files"""
        
        output_files = {}
        
        try:
            # Save summary text file
            summary_path = self.flood_analyzer.save_summary_to_file(
                flood_result, output_directory
            )
            output_files['flood_summary'] = summary_path
            
            # TODO: Save additional formats (CSV, JSON) if needed
            
        except Exception as e:
            logger.error(f"Error saving flood analysis outputs: {str(e)}")
        
        return output_files
    
    def _generate_comprehensive_summary(self, results: DashboardAnalysisResult) -> str:
        """Generate a comprehensive summary of all analyses"""
        
        summary_lines = []
        summary_lines.append("=" * 60)
        summary_lines.append("COMPREHENSIVE GEOSPATIAL ANALYSIS REPORT")
        summary_lines.append("=" * 60)
        summary_lines.append("")
        
        # Add flood analysis summary if available
        if results.flood_analysis:
            flood_summary = self.flood_analyzer.generate_summary_report(results.flood_analysis)
            summary_lines.append(flood_summary)
            summary_lines.append("")
        
        # TODO: Add other analysis summaries when implemented
        
        if not results.flood_analysis:
            summary_lines.append("No analysis results available.")
            summary_lines.append("Please ensure data sources are properly configured.")
        
        return "\n".join(summary_lines)
    
    def _create_empty_result(self, message: str) -> DashboardAnalysisResult:
        """Create an empty result with a message"""
        
        return DashboardAnalysisResult(
            analysis_summary=f"Analysis Status: {message}",
            metadata={'status': 'empty', 'message': message}
        )
    
    def _create_error_result(self, error_message: str) -> DashboardAnalysisResult:
        """Create an error result"""
        
        return DashboardAnalysisResult(
            analysis_summary=f"Analysis Error: {error_message}",
            metadata={'status': 'error', 'error': error_message}
        )