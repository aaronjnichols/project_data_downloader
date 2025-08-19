"""
Location Map Generator for Civil Engineering Reports

Creates professional location maps with main site view, vicinity inset, cartographic elements, and title block.
"""

import os
import math
import tempfile
from typing import Dict, Tuple, Optional, List, Union
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.backends.backend_pdf import PdfPages
import geopandas as gpd
from shapely.geometry import Point, box
import contextily as ctx
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class LocationMapGenerator:
    """Generate professional location maps for civil engineering reports"""
    
    def __init__(self, config: Dict = None):
        """
        Initialize the location map generator
        
        Args:
            config: Configuration dictionary with map settings
        """
        self.config = config or {}
        
        # Page settings (8.5" x 11" in inches)
        self.page_width = 8.5
        self.page_height = 11.0
        self.dpi = 300
        
        # Standard engineering scales (1 inch = X feet)
        self.standard_scales = [20, 30, 40, 50, 60, 80, 100, 120, 150, 200, 300, 400, 500, 600, 800, 1000, 1200, 1600, 2000, 3000, 4000, 5000, 6000, 8000, 10000]
        
        # Layout settings with proper 0.5" margins
        self.margins = {
            'left': 0.5,
            'right': 0.5,
            'top': 0.5,
            'bottom': 0.5
        }
        
        # Calculate available space
        available_width = self.page_width - self.margins['left'] - self.margins['right']  # 7.5"
        available_height = self.page_height - self.margins['top'] - self.margins['bottom']  # 10.0"
        
        # Title block settings (at bottom with margin)
        self.title_block_frame = {
            'x': self.margins['left'],
            'y': self.margins['bottom'],
            'width': available_width,
            'height': 1.75
        }
        
        # Main map frame - extends from left margin to right margin, under vicinity map
        # Leave 0.5" space above title block
        map_top = self.page_height - self.margins['top']
        map_bottom = self.title_block_frame['y'] + self.title_block_frame['height'] + 0.5  # 0.5" gap above title block
        
        self.main_map_frame = {
            'x': self.margins['left'],
            'y': map_bottom,
            'width': available_width,
            'height': map_top - map_bottom
        }
        
        # Vicinity map settings (top right corner with margins)
        vicinity_size = 1.75
        self.vicinity_map_frame = {
            'x': self.page_width - self.margins['right'] - vicinity_size,
            'y': self.page_height - self.margins['top'] - vicinity_size,
            'width': vicinity_size,
            'height': vicinity_size
        }
        
        # After main_map_frame definition, update north arrow pos
        self.north_arrow_pos = {
            'x': self.page_width - self.margins['right'] - 0.4,
            'y': self.main_map_frame['y'] + 0.4,
            'size': 0.4
        }
        
        # Legend position remains the same
        legend_height = 0.6
        self.legend_pos = {
            'x': self.main_map_frame['x'] + 0.1,
            # Align legend TOP with top of main map minus small gap (0.1")
            'y': self.main_map_frame['y'] + self.main_map_frame['height'] - legend_height - 0.1,
            'width': 1.5,
            'height': legend_height
        }
    
    def generate_location_map(self, 
                           site_boundary: gpd.GeoDataFrame,
                           project_info: Dict,
                           output_path: str,
                           base_map_type: str = "satellite",
                           include_vicinity: bool = True,
                           custom_layers: Optional[List[gpd.GeoDataFrame]] = None) -> bool:
        """
        Generate a complete location map exhibit
        
        Args:
            site_boundary: GeoDataFrame containing site boundary polygon(s)
            project_info: Dictionary with project information for title block
            output_path: Path for output PDF file
            base_map_type: Type of base map ("satellite", "terrain", "street")
            include_vicinity: Whether to include vicinity map
            custom_layers: Additional layers to include on the map
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Starting location map generation")
            
            # Ensure site boundary is in Web Mercator for contextily
            site_boundary_wm = site_boundary.to_crs('EPSG:3857')
            
            # Calculate optimal scale for main map
            optimal_scale = self._calculate_optimal_scale(site_boundary_wm)
            logger.info(f"Calculated optimal scale: 1\" = {optimal_scale}'")
            
            # Create the PDF
            with PdfPages(output_path) as pdf:
                fig = plt.figure(figsize=(self.page_width, self.page_height))
                fig.patch.set_facecolor('white')
                
                # Create main map
                main_ax = self._create_main_map(fig, site_boundary_wm, optimal_scale, base_map_type)
                
                # Create vicinity map if requested
                if include_vicinity:
                    vicinity_ax = self._create_vicinity_map(fig, site_boundary_wm)
                
                # Add cartographic elements
                self._add_north_arrow(fig)
                self._add_legend(fig)
                
                # Add title block
                self._add_title_block(fig, project_info, optimal_scale)
                
                # Save to PDF
                pdf.savefig(fig, dpi=self.dpi)
                plt.close(fig)
            
            logger.info(f"Location map successfully generated: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating location map: {e}")
            return False
    
    def _calculate_optimal_scale(self, site_boundary_wm: gpd.GeoDataFrame) -> int:
        """
        Calculate the optimal engineering scale for the site with buffer
        
        Args:
            site_boundary_wm: Site boundary in Web Mercator projection
            
        Returns:
            Optimal scale (feet per inch) with buffer to prevent boundary cutoff
        """
        # Get bounds in Web Mercator
        bounds = site_boundary_wm.total_bounds
        width_m = bounds[2] - bounds[0]
        height_m = bounds[3] - bounds[1]
        
        # Convert to feet
        width_ft = width_m * 3.28084
        height_ft = height_m * 3.28084
        
        # Calculate scale needed to fit in main map frame (with 20% buffer)
        # Account for vicinity map overlap in the top right
        effective_width = self.main_map_frame['width'] * 0.8
        effective_height = self.main_map_frame['height'] * 0.8
        
        scale_x = width_ft / effective_width
        scale_y = height_ft / effective_height
        
        # Use the larger scale (smaller ratio) to ensure everything fits
        required_scale = max(scale_x, scale_y)
        
        # Find the optimal scale, then bump it up to provide buffer
        optimal_scale = None
        for scale in self.standard_scales:
            if scale >= required_scale:
                optimal_scale = scale
                break
        
        # If no scale found, use the largest
        if optimal_scale is None:
            return self.standard_scales[-1]
        
        # Find the index of the optimal scale
        try:
            scale_index = self.standard_scales.index(optimal_scale)
            
            # Bump up to next scale level to provide buffer (skip 1 level)
            # This ensures AOI boundary won't be cut off
            if scale_index + 1 < len(self.standard_scales):
                return self.standard_scales[scale_index + 1]
            else:
                # If already at the largest scale, use it
                return optimal_scale
                
        except ValueError:
            return optimal_scale
    
    def _create_main_map(self, fig: plt.Figure, site_boundary_wm: gpd.GeoDataFrame, 
                       scale: int, base_map_type: str) -> plt.Axes:
        """
        Create the main site map
        
        Args:
            fig: Matplotlib figure
            site_boundary_wm: Site boundary in Web Mercator
            scale: Map scale (feet per inch)
            base_map_type: Type of base map
            
        Returns:
            Matplotlib axes object
        """
        # Create axes for main map
        ax = fig.add_axes([
            self.main_map_frame['x'] / self.page_width,
            self.main_map_frame['y'] / self.page_height,
            self.main_map_frame['width'] / self.page_width,
            self.main_map_frame['height'] / self.page_height  # correct height ratio
        ])
        
        # Calculate map extent based on scale
        map_width_ft = self.main_map_frame['width'] * scale
        map_height_ft = self.main_map_frame['height'] * scale
        
        # Convert to meters
        map_width_m = map_width_ft / 3.28084
        map_height_m = map_height_ft / 3.28084
        
        # Get site centroid
        site_centroid = site_boundary_wm.geometry.centroid.iloc[0]
        
        # Calculate map bounds centered on site
        minx = site_centroid.x - map_width_m / 2
        maxx = site_centroid.x + map_width_m / 2
        miny = site_centroid.y - map_height_m / 2
        maxy = site_centroid.y + map_height_m / 2
        
        # Set map extent
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        
        # Add base map (without attribution for clean professional appearance)
        try:
            if base_map_type == "satellite":
                ctx.add_basemap(ax, crs=site_boundary_wm.crs, source=ctx.providers.Esri.WorldImagery, attribution="")
            elif base_map_type == "terrain":
                ctx.add_basemap(ax, crs=site_boundary_wm.crs, source=ctx.providers.USGS.USTopo, attribution="")
            else:  # street
                ctx.add_basemap(ax, crs=site_boundary_wm.crs, source=ctx.providers.OpenStreetMap.Mapnik, attribution="")
        except Exception as e:
            logger.warning(f"Could not load base map: {e}")
            ax.set_facecolor('lightgray')
        
        # Plot site boundary
        site_boundary_wm.plot(ax=ax, facecolor='none', edgecolor='red', linewidth=3, alpha=0.8)
        
        # Remove axes
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Add border
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(2)
            spine.set_color('black')
        
        return ax
    
    def _create_vicinity_map(self, fig: plt.Figure, site_boundary_wm: gpd.GeoDataFrame) -> plt.Axes:
        """
        Create the vicinity/location map
        
        Args:
            fig: Matplotlib figure
            site_boundary_wm: Site boundary in Web Mercator
            
        Returns:
            Matplotlib axes object
        """
        # Create axes for vicinity map
        ax = fig.add_axes([
            self.vicinity_map_frame['x'] / self.page_width,
            self.vicinity_map_frame['y'] / self.page_height,
            self.vicinity_map_frame['width'] / self.page_width,
            self.vicinity_map_frame['height'] / self.page_height
        ])
        
        # Get site centroid
        site_centroid = site_boundary_wm.geometry.centroid.iloc[0]
        
        # Create larger extent for vicinity map (approximately 10x larger)
        site_bounds = site_boundary_wm.total_bounds
        width = site_bounds[2] - site_bounds[0]
        height = site_bounds[3] - site_bounds[1]
        
        # Expand bounds for vicinity context
        buffer = max(width, height) * 5  # 5x buffer
        
        minx = site_centroid.x - buffer
        maxx = site_centroid.x + buffer
        miny = site_centroid.y - buffer
        maxy = site_centroid.y + buffer
        
        # Set extent
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        
        # Add base map (without attribution for clean professional appearance)
        try:
            ctx.add_basemap(ax, crs=site_boundary_wm.crs, source=ctx.providers.OpenStreetMap.Mapnik, attribution="")
        except Exception as e:
            logger.warning(f"Could not load vicinity base map: {e}")
            ax.set_facecolor('lightblue')
        
        # Plot site location as a point
        site_centroid_gdf = gpd.GeoDataFrame([1], geometry=[site_centroid], crs=site_boundary_wm.crs)
        site_centroid_gdf.plot(ax=ax, color='red', markersize=50, marker='*')
        
        # Remove axes
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Add border
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(1)
            spine.set_color('black')
        
        # Remove vicinity map title text as requested
        
        return ax
    
    def _add_north_arrow(self, fig: plt.Figure):
        """Add north arrow to the map"""
        # Create north arrow at specified position
        ax = fig.add_axes([
            self.north_arrow_pos['x'] / self.page_width,
            self.north_arrow_pos['y'] / self.page_height,
            self.north_arrow_pos['size'] / self.page_width,
            self.north_arrow_pos['size'] / self.page_height
        ])
        
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)
        ax.axis('off')
        
        # Draw arrow
        arrow = patches.FancyArrowPatch((0, -0.7), (0, 0.7),
                                      arrowstyle='->', mutation_scale=20,
                                      color='black', linewidth=2)
        ax.add_patch(arrow)
        
        # Add "N" label
        ax.text(0, 0.9, 'N', ha='center', va='center', fontsize=12, fontweight='bold')
    
    def _add_legend(self, fig: plt.Figure):
        """Add legend to the map with white background and black border"""
        # Create legend at specified position (top left of main map)
        ax = fig.add_axes([
            self.legend_pos['x'] / self.page_width,
            self.legend_pos['y'] / self.page_height,
            self.legend_pos['width'] / self.page_width,
            self.legend_pos['height'] / self.page_height
        ])
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        # Add white background with black border
        background = Rectangle((0, 0), 1, 1, facecolor='white', edgecolor='black', linewidth=1)
        ax.add_patch(background)
        
        # Add legend items
        # Site boundary
        line = plt.Line2D([0.1, 0.3], [0.4, 0.4], color='red', linewidth=3)
        ax.add_line(line)
        ax.text(0.35, 0.4, 'SITE BOUNDARY', va='center', fontsize=8)
        
        # Legend title
        ax.text(0.5, 0.7, 'LEGEND', ha='center', va='center', fontsize=9, fontweight='bold')
    
    def _add_title_block(self, fig: plt.Figure, project_info: Dict, scale: int):
        """Add title block with project information"""
        # Create title block axes
        ax = fig.add_axes([
            self.title_block_frame['x'] / self.page_width,
            self.title_block_frame['y'] / self.page_height,
            self.title_block_frame['width'] / self.page_width,
            self.title_block_frame['height'] / self.page_height
        ])
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        # Draw title block border
        border = Rectangle((0, 0), 1, 1, facecolor='none', edgecolor='black', linewidth=2)
        ax.add_patch(border)
        
        # Add project information (all text converted to uppercase)
        project_name = project_info.get('name', 'PROJECT NAME').upper()
        project_number = project_info.get('number', 'PROJECT NUMBER').upper()
        client = project_info.get('client', 'CLIENT NAME').upper()
        date = project_info.get('date', datetime.now().strftime('%m/%d/%Y')).upper()
        drawn_by = project_info.get('drawn_by', 'INITIALS').upper()
        
        # Title
        ax.text(0.5, 0.85, 'LOCATION MAP', ha='center', va='center', 
               fontsize=16, fontweight='bold')
        
        # Project info - left side
        ax.text(0.05, 0.65, f'PROJECT: {project_name}', ha='left', va='center', fontsize=10)
        ax.text(0.05, 0.55, f'PROJECT NO: {project_number}', ha='left', va='center', fontsize=10)
        ax.text(0.05, 0.45, f'CLIENT: {client}', ha='left', va='center', fontsize=10)
        
        # Drawing info - right side
        ax.text(0.95, 0.65, f'SCALE: 1" = {scale}\'', ha='right', va='center', fontsize=10)
        ax.text(0.95, 0.55, f'DATE: {date}', ha='right', va='center', fontsize=10)
        ax.text(0.95, 0.45, f'DRAWN BY: {drawn_by}', ha='right', va='center', fontsize=10)
        
        # Sheet info
        ax.text(0.5, 0.15, 'SHEET 1 OF 1', ha='center', va='center', fontsize=10)
        
        # Add horizontal divider lines
        ax.axhline(y=0.35, xmin=0.02, xmax=0.98, color='black', linewidth=1)
        ax.axhline(y=0.75, xmin=0.02, xmax=0.98, color='black', linewidth=1)


def create_location_map(aoi_file_path: str, project_info: Dict, output_path: str, 
                       base_map_type: str = "satellite") -> bool:
    """
    Convenience function to create a location map from an AOI file
    
    Args:
        aoi_file_path: Path to AOI shapefile
        project_info: Project information dictionary
        output_path: Output PDF path
        base_map_type: Type of base map to use
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load AOI
        aoi_gdf = gpd.read_file(aoi_file_path)
        
        # Create map generator
        generator = LocationMapGenerator()
        
        # Generate map
        return generator.generate_location_map(
            site_boundary=aoi_gdf,
            project_info=project_info,
            output_path=output_path,
            base_map_type=base_map_type
        )
        
    except Exception as e:
        logger.error(f"Error creating location map: {e}")
        return False