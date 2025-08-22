"""
FEMA Flood Hazard Area Analysis Module

This module provides comprehensive analysis of FEMA flood hazard zones within
a given Area of Interest (AOI). It calculates areas, percentages, and provides
detailed statistics for flood risk assessment.

Key Features:
- Area calculations by flood zone (AE, X, VE, etc.)
- Percentage distribution of flood hazard areas
- FIRM panel identification
- Special Flood Hazard Area (SFHA) classification
- Base Flood Elevation (BFE) statistics
"""

import os
from typing import Dict, Optional, List, Tuple, Any, Union
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import box
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class FloodZoneStats:
    """Data class for flood zone statistics"""
    zone: str
    area_sqft: float
    area_acres: float
    percentage: float
    feature_count: int
    zone_description: str
    is_sfha: bool
    zone_subtype: Optional[str] = None
    bfe_min: Optional[float] = None
    bfe_max: Optional[float] = None
    bfe_avg: Optional[float] = None


@dataclass
class FirmPanelInfo:
    """Data class for FIRM panel information"""
    panel_id: str
    effective_date: Optional[str] = None
    preliminary_date: Optional[str] = None
    panel_type: Optional[str] = None


@dataclass
class FloodAnalysisResult:
    """Complete flood analysis results"""
    total_aoi_area_sqft: float
    total_aoi_area_acres: float
    sfha_area_sqft: float
    sfha_area_acres: float
    sfha_percentage: float
    zone_stats: List[FloodZoneStats]
    firm_panels: List[FirmPanelInfo]
    analysis_metadata: Dict[str, Any]


class FloodAnalyzer:
    """
    FEMA Flood Hazard Analysis Engine
    
    Analyzes FEMA flood hazard zones within an AOI and provides comprehensive
    statistics for flood risk assessment and engineering analysis.
    """
    
    # FEMA flood zone descriptions mapping
    FLOOD_ZONE_DESCRIPTIONS = {
        'AE': 'High Risk - 1% annual chance flood zone with Base Flood Elevations',
        'AO': 'High Risk - 1% annual chance flood zone with flood depths',
        'AH': 'High Risk - 1% annual chance flood zone with ponding',
        'A': 'High Risk - 1% annual chance flood zone (no BFE determined)',
        'VE': 'High Risk - Coastal high hazard area with velocity hazard',
        'V': 'High Risk - Coastal high hazard area (no BFE determined)',
        'X': 'Moderate/Low Risk - 0.2% annual chance flood hazard',
        'X500': 'Moderate Risk - 0.2% annual chance flood hazard',
        'OPEN WATER': 'Open Water - Water areas',
        'D': 'Undetermined Risk - Flood hazard undetermined',
        'AR': 'High Risk - 1% annual chance flood zone (restored)',
        'A99': 'High Risk - 1% annual chance flood zone with levee protection'
    }
    
    # Special Flood Hazard Area (SFHA) zones
    SFHA_ZONES = {'AE', 'AO', 'AH', 'A', 'VE', 'V', 'AR', 'A99'}
    
    def __init__(self):
        """Initialize the FloodAnalyzer"""
        pass
    
    def analyze_flood_zones(self, 
                          aoi_gdf: gpd.GeoDataFrame, 
                          fema_data_gdf: gpd.GeoDataFrame,
                          firm_panels_gdf: Optional[gpd.GeoDataFrame] = None) -> FloodAnalysisResult:
        """
        Analyze FEMA flood zones within the given AOI
        
        Args:
            aoi_gdf: GeoDataFrame containing the Area of Interest geometry
            fema_data_gdf: GeoDataFrame containing FEMA flood hazard zones
            firm_panels_gdf: Optional GeoDataFrame containing FEMA FIRM panels data
            
        Returns:
            FloodAnalysisResult: Comprehensive flood analysis results
        """
        
        logger.info(f"Starting flood zone analysis for AOI with {len(fema_data_gdf)} flood features")
        
        # Ensure both datasets are in the same CRS (preferably projected for area calculations)
        if aoi_gdf.crs != fema_data_gdf.crs:
            logger.info(f"Reprojecting FEMA data from {fema_data_gdf.crs} to {aoi_gdf.crs}")
            fema_data_gdf = fema_data_gdf.to_crs(aoi_gdf.crs)
        
        # Convert to a projected CRS for accurate area calculations if needed
        original_crs = aoi_gdf.crs
        if aoi_gdf.crs.is_geographic:
            # Use UTM zone based on AOI centroid
            utm_crs = self._get_utm_crs(aoi_gdf)
            logger.info(f"Converting to UTM CRS {utm_crs} for area calculations")
            aoi_gdf = aoi_gdf.to_crs(utm_crs)
            fema_data_gdf = fema_data_gdf.to_crs(utm_crs)
        
        # Calculate total AOI area
        total_aoi_area_sqft = aoi_gdf.geometry.area.sum() * 10.764  # m² to ft²
        total_aoi_area_acres = total_aoi_area_sqft / 43560  # ft² to acres
        
        # Perform intersection analysis
        intersections = gpd.overlay(aoi_gdf, fema_data_gdf, how='intersection', keep_geom_type=False)
        
        if len(intersections) == 0:
            logger.warning("No flood zone intersections found within AOI")
            return self._create_empty_result(total_aoi_area_sqft, total_aoi_area_acres)
        
        # Calculate areas for each intersection
        intersections['area_sqft'] = intersections.geometry.area * 10.764  # m² to ft²
        intersections['area_acres'] = intersections['area_sqft'] / 43560  # ft² to acres
        
        # Aggregate by flood zone
        zone_stats = self._calculate_zone_statistics(intersections, total_aoi_area_sqft)
        
        # Calculate SFHA statistics
        sfha_area_sqft, sfha_area_acres, sfha_percentage = self._calculate_sfha_stats(
            zone_stats, total_aoi_area_sqft
        )
        
        # Extract FIRM panel information from FIRM Panels layer if available, else from flood zones
        firm_panels = self._extract_firm_panels(firm_panels_gdf, fema_data_gdf)
        
        # Create analysis metadata
        metadata = {
            'analysis_crs': str(aoi_gdf.crs),
            'original_crs': str(original_crs),
            'total_flood_features': len(fema_data_gdf),
            'intersecting_features': len(intersections),
            'unique_flood_zones': len(zone_stats),
            'analysis_method': 'geometric_intersection'
        }
        
        logger.info(f"Flood analysis completed: {len(zone_stats)} zones analyzed")
        
        return FloodAnalysisResult(
            total_aoi_area_sqft=total_aoi_area_sqft,
            total_aoi_area_acres=total_aoi_area_acres,
            sfha_area_sqft=sfha_area_sqft,
            sfha_area_acres=sfha_area_acres,
            sfha_percentage=sfha_percentage,
            zone_stats=zone_stats,
            firm_panels=firm_panels,
            analysis_metadata=metadata
        )
    
    def _calculate_zone_statistics(self, 
                                 intersections: gpd.GeoDataFrame, 
                                 total_aoi_area_sqft: float) -> List[FloodZoneStats]:
        """Calculate statistics for each flood zone"""
        
        # Group by flood zone and zone subtype for more detailed analysis
        group_cols = ['FLD_ZONE']
        agg_dict = {
            'area_sqft': 'sum',
            'area_acres': 'sum',
            'OBJECTID': 'count',  # Feature count
            'STATIC_BFE': ['min', 'max', 'mean']  # Base Flood Elevation stats
        }
        
        # Include ZONE_SUBTY if available
        if 'ZONE_SUBTY' in intersections.columns:
            group_cols.append('ZONE_SUBTY')
            agg_dict['ZONE_SUBTY'] = 'first'  # Get the subtype value
        
        zone_groups = intersections.groupby(group_cols).agg(agg_dict).round(2)
        
        zone_stats = []
        
        for group_key in zone_groups.index:
            # Handle both single and multi-column grouping
            if isinstance(group_key, tuple):
                zone = group_key[0]
                zone_subtype = group_key[1] if len(group_key) > 1 and pd.notna(group_key[1]) else None
            else:
                zone = group_key
                zone_subtype = None
            
            area_sqft = zone_groups.loc[group_key, ('area_sqft', 'sum')]
            area_acres = zone_groups.loc[group_key, ('area_acres', 'sum')]
            percentage = (area_sqft / total_aoi_area_sqft) * 100
            feature_count = zone_groups.loc[group_key, ('OBJECTID', 'count')]
            
            # Handle BFE statistics (may be -9999 for no data)
            bfe_min = zone_groups.loc[group_key, ('STATIC_BFE', 'min')]
            bfe_max = zone_groups.loc[group_key, ('STATIC_BFE', 'max')]
            bfe_avg = zone_groups.loc[group_key, ('STATIC_BFE', 'mean')]
            
            # Clean up BFE values (-9999 indicates no data)
            bfe_min = None if bfe_min == -9999 else bfe_min
            bfe_max = None if bfe_max == -9999 else bfe_max
            bfe_avg = None if bfe_avg == -9999 else bfe_avg
            
            zone_stats.append(FloodZoneStats(
                zone=zone,
                area_sqft=area_sqft,
                area_acres=area_acres,
                percentage=percentage,
                feature_count=feature_count,
                zone_description=self.FLOOD_ZONE_DESCRIPTIONS.get(zone, f'Zone {zone}'),
                is_sfha=zone in self.SFHA_ZONES,
                zone_subtype=zone_subtype,
                bfe_min=bfe_min,
                bfe_max=bfe_max,
                bfe_avg=bfe_avg
            ))
        
        # Sort by area (largest first)
        zone_stats.sort(key=lambda x: x.area_sqft, reverse=True)
        
        return zone_stats
    
    def _calculate_sfha_stats(self, 
                            zone_stats: List[FloodZoneStats], 
                            total_aoi_area_sqft: float) -> Tuple[float, float, float]:
        """Calculate Special Flood Hazard Area statistics"""
        
        sfha_area_sqft = sum(stat.area_sqft for stat in zone_stats if stat.is_sfha)
        sfha_area_acres = sfha_area_sqft / 43560
        sfha_percentage = (sfha_area_sqft / total_aoi_area_sqft) * 100
        
        return sfha_area_sqft, sfha_area_acres, sfha_percentage
    
    def _extract_firm_panels(self, firm_panels_gdf: Optional[gpd.GeoDataFrame], 
                            fema_data_gdf: gpd.GeoDataFrame) -> List[FirmPanelInfo]:
        """Extract FIRM panel information from the data
        
        Args:
            firm_panels_gdf: Optional GeoDataFrame containing FIRM panels (preferred source)
            fema_data_gdf: GeoDataFrame containing flood zones (fallback source)
            
        Returns:
            List of FirmPanelInfo objects with panel details
        """
        
        # Prefer FIRM panels layer if available (has full metadata)
        if firm_panels_gdf is not None and len(firm_panels_gdf) > 0:
            if 'FIRM_PAN' in firm_panels_gdf.columns:
                return self._extract_detailed_firm_info(firm_panels_gdf)
        
        # Fallback to flood zones data (basic panel IDs only)
        if 'FIRM_PAN' in fema_data_gdf.columns:
            firm_panel_ids = fema_data_gdf['FIRM_PAN'].dropna().unique().tolist()
            logger.info(f"Extracted {len(firm_panel_ids)} FIRM panel IDs from flood zones data (no dates available)")
            return [FirmPanelInfo(panel_id=panel_id) for panel_id in sorted(firm_panel_ids)]
        
        logger.warning("No FIRM panel data found in either FIRM panels layer or flood zones")
        return []
    
    def _extract_detailed_firm_info(self, firm_panels_gdf: gpd.GeoDataFrame) -> List[FirmPanelInfo]:
        """Extract detailed FIRM panel information including dates"""
        
        firm_panels = []
        
        # Group by panel ID to get unique panels
        if 'FIRM_PAN' in firm_panels_gdf.columns:
            panel_groups = firm_panels_gdf.groupby('FIRM_PAN').first()
            
            for panel_id, row in panel_groups.iterrows():
                # Extract dates (prefer readable format if available, fallback to original)
                effective_date = None
                preliminary_date = None
                panel_type = None
                
                # Check for readable date columns first (updated for shapefile-compatible names)
                if 'eff_date_r' in row and pd.notna(row['eff_date_r']):
                    effective_date = str(row['eff_date_r'])
                elif 'effective_date' in row and pd.notna(row['effective_date']):  # Fallback for old name
                    effective_date = str(row['effective_date'])
                elif 'EFF_DATE' in row and pd.notna(row['EFF_DATE']):
                    # Convert from timestamp if not already converted
                    from src.utils.date_utils import convert_esri_date
                    effective_date = convert_esri_date(row['EFF_DATE'])
                
                if 'PANEL_TYP' in row and pd.notna(row['PANEL_TYP']):
                    panel_type = str(row['PANEL_TYP'])
                
                firm_panels.append(FirmPanelInfo(
                    panel_id=str(panel_id),
                    effective_date=effective_date,
                    preliminary_date=None,  # No longer extracting preliminary dates
                    panel_type=panel_type
                ))
        
        # Sort by panel ID
        firm_panels.sort(key=lambda x: x.panel_id)
        
        logger.info(f"Extracted {len(firm_panels)} FIRM panels with detailed information")
        return firm_panels
    
    def _get_utm_crs(self, gdf: gpd.GeoDataFrame) -> str:
        """Get appropriate UTM CRS for the given GeoDataFrame"""
        
        # Get centroid of the data
        centroid = gdf.geometry.unary_union.centroid
        
        # Calculate UTM zone
        utm_zone = int((centroid.x + 180) / 6) + 1
        
        # Determine hemisphere
        hemisphere = 'north' if centroid.y >= 0 else 'south'
        
        # Return EPSG code for UTM
        if hemisphere == 'north':
            return f'EPSG:{32600 + utm_zone}'
        else:
            return f'EPSG:{32700 + utm_zone}'
    
    def _create_empty_result(self, 
                           total_aoi_area_sqft: float, 
                           total_aoi_area_acres: float) -> FloodAnalysisResult:
        """Create an empty result when no flood data is found"""
        
        return FloodAnalysisResult(
            total_aoi_area_sqft=total_aoi_area_sqft,
            total_aoi_area_acres=total_aoi_area_acres,
            sfha_area_sqft=0.0,
            sfha_area_acres=0.0,
            sfha_percentage=0.0,
            zone_stats=[],
            firm_panels=[],
            analysis_metadata={'analysis_method': 'no_data_found'}
        )
    
    def generate_summary_report(self, result: FloodAnalysisResult) -> str:
        """
        Generate a text summary report of the flood analysis
        
        Args:
            result: FloodAnalysisResult from analyze_flood_zones
            
        Returns:
            Formatted text summary of flood analysis
        """
        
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("FEMA FLOOD HAZARD AREA ANALYSIS REPORT")
        report_lines.append("=" * 60)
        report_lines.append("")
        
        # AOI Summary
        report_lines.append("AREA OF INTEREST SUMMARY:")
        report_lines.append("-" * 30)
        report_lines.append(f"Total AOI Area: {result.total_aoi_area_sqft:,.0f} sq ft ({result.total_aoi_area_acres:,.2f} acres)")
        report_lines.append("")
        
        # SFHA Summary
        report_lines.append("SPECIAL FLOOD HAZARD AREA (SFHA) SUMMARY:")
        report_lines.append("-" * 45)
        report_lines.append(f"SFHA Area: {result.sfha_area_sqft:,.0f} sq ft ({result.sfha_area_acres:,.2f} acres)")
        report_lines.append(f"SFHA Percentage: {result.sfha_percentage:.2f}% of total AOI")
        report_lines.append("")
        
        # Flood Zone Breakdown
        if result.zone_stats:
            report_lines.append("FLOOD ZONE BREAKDOWN:")
            report_lines.append("-" * 25)
            report_lines.append(f"{'Zone':<8} {'Area (sq ft)':<15} {'Area (acres)':<15} {'Percentage':<12} {'SFHA':<6} {'Description':<50}")
            report_lines.append("-" * 110)
            
            for stat in result.zone_stats:
                sfha_indicator = "Yes" if stat.is_sfha else "No"
                report_lines.append(
                    f"{stat.zone:<8} {stat.area_sqft:>14,.0f} {stat.area_acres:>14,.2f} {stat.percentage:>10.2f}% "
                    f"{sfha_indicator:<6} {stat.zone_description[:50]:<50}"
                )
            
            report_lines.append("")
            
            # Base Flood Elevation Summary
            bfe_zones = [stat for stat in result.zone_stats if stat.bfe_avg is not None]
            if bfe_zones:
                report_lines.append("BASE FLOOD ELEVATION (BFE) SUMMARY:")
                report_lines.append("-" * 35)
                report_lines.append(f"{'Zone':<8} {'Min BFE':<10} {'Max BFE':<10} {'Avg BFE':<10}")
                report_lines.append("-" * 40)
                
                for stat in bfe_zones:
                    min_bfe = f"{stat.bfe_min:.1f}" if stat.bfe_min is not None else "N/A"
                    max_bfe = f"{stat.bfe_max:.1f}" if stat.bfe_max is not None else "N/A"
                    avg_bfe = f"{stat.bfe_avg:.1f}" if stat.bfe_avg is not None else "N/A"
                    
                    report_lines.append(f"{stat.zone:<8} {min_bfe:<10} {max_bfe:<10} {avg_bfe:<10}")
                
                report_lines.append("")
        
        # FIRM Panels
        if result.firm_panels:
            report_lines.append("FIRM PANELS:")
            report_lines.append("-" * 50)
            report_lines.append(f"{'Panel ID':<15} {'Effective Date':<15} {'Type':<15}")
            report_lines.append("-" * 50)
            
            for panel in result.firm_panels:
                eff_date = panel.effective_date if panel.effective_date else "N/A"
                panel_type = panel.panel_type if panel.panel_type else "N/A"
                report_lines.append(f"{panel.panel_id:<15} {eff_date:<15} {panel_type:<15}")
            
            report_lines.append("")
        
        # Analysis Metadata
        report_lines.append("ANALYSIS METADATA:")
        report_lines.append("-" * 20)
        for key, value in result.analysis_metadata.items():
            report_lines.append(f"{key.replace('_', ' ').title()}: {value}")
        
        report_lines.append("")
        report_lines.append("=" * 60)
        report_lines.append("End of Report")
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)
    
    def generate_markdown_report(self, result: FloodAnalysisResult) -> str:
        """
        Generate a markdown formatted report of the flood analysis
        
        Args:
            result: FloodAnalysisResult from analyze_flood_zones
            
        Returns:
            Markdown formatted flood analysis report
        """
        
        report_lines = []
        report_lines.append("# FEMA Flood Hazard Area Analysis Report")
        report_lines.append("")
        
        # AOI Summary
        report_lines.append("## Area of Interest Summary")
        report_lines.append("")
        report_lines.append(f"- **Total AOI Area**: {result.total_aoi_area_sqft:,.0f} sq ft ({result.total_aoi_area_acres:,.2f} acres)")
        report_lines.append("")
        
        # SFHA Summary
        report_lines.append("## Special Flood Hazard Area (SFHA) Summary")
        report_lines.append("")
        report_lines.append(f"- **SFHA Area**: {result.sfha_area_sqft:,.0f} sq ft ({result.sfha_area_acres:,.2f} acres)")
        report_lines.append(f"- **SFHA Percentage**: {result.sfha_percentage:.2f}% of total AOI")
        report_lines.append("")
        
        # Flood Zone Breakdown
        if result.zone_stats:
            report_lines.append("## Flood Zone Breakdown")
            report_lines.append("")
            report_lines.append("| Zone | Area (sq ft) | Area (acres) | Percentage | SFHA | Description |")
            report_lines.append("|------|-------------|-------------|------------|------|-------------|")
            
            for stat in result.zone_stats:
                sfha_indicator = "Yes" if stat.is_sfha else "No"
                report_lines.append(
                    f"| {stat.zone} | {stat.area_sqft:,.0f} | {stat.area_acres:.2f} | {stat.percentage:.2f}% | {sfha_indicator} | {stat.zone_description} |"
                )
            
            report_lines.append("")
            
            # Base Flood Elevation Summary
            bfe_zones = [stat for stat in result.zone_stats if stat.bfe_avg is not None]
            if bfe_zones:
                report_lines.append("### Base Flood Elevation (BFE) Summary")
                report_lines.append("")
                report_lines.append("| Zone | Min BFE | Max BFE | Avg BFE |")
                report_lines.append("|------|---------|---------|---------|")
                
                for stat in bfe_zones:
                    min_bfe = f"{stat.bfe_min:.1f}" if stat.bfe_min is not None else "N/A"
                    max_bfe = f"{stat.bfe_max:.1f}" if stat.bfe_max is not None else "N/A"
                    avg_bfe = f"{stat.bfe_avg:.1f}" if stat.bfe_avg is not None else "N/A"
                    
                    report_lines.append(f"| {stat.zone} | {min_bfe} | {max_bfe} | {avg_bfe} |")
                
                report_lines.append("")
        
        # FIRM Panels
        if result.firm_panels:
            report_lines.append("## FIRM Panels")
            report_lines.append("")
            report_lines.append("| Panel ID | Effective Date | Panel Type |")
            report_lines.append("|----------|---------------|------------|")
            
            for panel in result.firm_panels:
                eff_date = panel.effective_date if panel.effective_date else "N/A"
                panel_type = panel.panel_type if panel.panel_type else "N/A"
                report_lines.append(f"| {panel.panel_id} | {eff_date} | {panel_type} |")
            
            report_lines.append("")
        
        # Analysis Metadata
        report_lines.append("## Analysis Metadata")
        report_lines.append("")
        for key, value in result.analysis_metadata.items():
            report_lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
        
        return "\n".join(report_lines)
    
    def generate_json_report(self, result: FloodAnalysisResult) -> dict:
        """
        Generate a JSON structured report of the flood analysis
        
        Args:
            result: FloodAnalysisResult from analyze_flood_zones
            
        Returns:
            Dictionary containing structured flood analysis data
        """
        
        # Convert zone stats to dictionaries
        zone_stats_data = []
        for stat in result.zone_stats:
            zone_data = {
                "zone": str(stat.zone),
                "zone_subtype": str(stat.zone_subtype) if stat.zone_subtype else None,
                "area_square_feet": float(stat.area_sqft),
                "area_acres": float(stat.area_acres),
                "percentage_of_aoi": float(stat.percentage),
                "feature_count": int(stat.feature_count),
                "description": str(stat.zone_description),
                "is_special_flood_hazard_area": bool(stat.is_sfha),
                "base_flood_elevation": {
                    "minimum": float(stat.bfe_min) if stat.bfe_min is not None else None,
                    "maximum": float(stat.bfe_max) if stat.bfe_max is not None else None,
                    "average": float(stat.bfe_avg) if stat.bfe_avg is not None else None
                } if any([stat.bfe_min, stat.bfe_max, stat.bfe_avg]) else None
            }
            zone_stats_data.append(zone_data)
        
        # Create comprehensive JSON structure
        json_report = {
            "flood_analysis_report": {
                "summary": {
                    "total_aoi_area": {
                        "square_feet": float(result.total_aoi_area_sqft),
                        "acres": float(result.total_aoi_area_acres)
                    },
                    "special_flood_hazard_area": {
                        "area_square_feet": float(result.sfha_area_sqft),
                        "area_acres": float(result.sfha_area_acres),
                        "percentage_of_aoi": float(result.sfha_percentage)
                    },
                    "flood_zone_count": len(result.zone_stats),
                    "firm_panels": [
                        {
                            "panel_id": panel.panel_id,
                            "effective_date": panel.effective_date,
                            "preliminary_date": panel.preliminary_date,
                            "panel_type": panel.panel_type
                        } for panel in result.firm_panels
                    ]
                },
                "flood_zones": zone_stats_data,
                "risk_assessment": {
                    "high_risk_zones": [stat.zone for stat in result.zone_stats if stat.is_sfha],
                    "moderate_low_risk_zones": [stat.zone for stat in result.zone_stats if not stat.is_sfha],
                    "sfha_percentage_category": self._categorize_sfha_percentage(result.sfha_percentage),
                    "dominant_flood_zone": result.zone_stats[0].zone if result.zone_stats else None
                },
                "analysis_metadata": result.analysis_metadata,
                "generated_timestamp": self._get_timestamp()
            }
        }
        
        return json_report
    
    def _categorize_sfha_percentage(self, percentage: float) -> str:
        """Categorize SFHA percentage for risk assessment"""
        if percentage == 0:
            return "No Special Flood Hazard Areas"
        elif percentage < 5:
            return "Low SFHA Coverage"
        elif percentage < 15:
            return "Moderate SFHA Coverage"
        elif percentage < 30:
            return "High SFHA Coverage"
        else:
            return "Very High SFHA Coverage"
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for report generation"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
    
    def save_summary_to_file(self, result: FloodAnalysisResult, output_path: str) -> str:
        """
        Save flood analysis summary to a text file
        
        Args:
            result: FloodAnalysisResult from analyze_flood_zones
            output_path: Directory path to save the summary file
            
        Returns:
            Path to the saved summary file
        """
        
        # Generate the summary report
        summary_text = self.generate_summary_report(result)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
        # Create filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fema_flood_analysis_summary_{timestamp}.txt"
        file_path = os.path.join(output_path, filename)
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(summary_text)
        
        logger.info(f"Flood analysis summary saved to: {file_path}")
        
        return file_path