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

from matplotlib.backends.backend\_pdf import PdfPages

import geopandas as gpd

from shapely.geometry import Point, box

import contextily as ctx

from PIL import Image

import logging



logger = logging.getLogger(\_\_name\_\_)





class LocationMapGenerator:

&nbsp;   """Generate professional location maps for civil engineering reports"""

&nbsp;   

&nbsp;   def \_\_init\_\_(self, config: Dict = None):

&nbsp;       """

&nbsp;       Initialize the location map generator

&nbsp;       

&nbsp;       Args:

&nbsp;           config: Configuration dictionary with map settings

&nbsp;       """

&nbsp;       self.config = config or {}

&nbsp;       

&nbsp;       # Page settings (8.5" x 11" in inches)

&nbsp;       self.page\_width = 8.5

&nbsp;       self.page\_height = 11.0

&nbsp;       self.dpi = 300

&nbsp;       

&nbsp;       # Standard engineering scales (1 inch = X feet)

&nbsp;       self.standard\_scales = \[20, 30, 40, 50, 60, 80, 100, 120, 150, 200, 300, 400, 500, 600, 800, 1000, 1200, 1600, 2000, 3000, 4000, 5000, 6000, 8000, 10000]

&nbsp;       

&nbsp;       # Layout settings with proper 0.5" margins

&nbsp;       self.margins = {

&nbsp;           'left': 0.5,

&nbsp;           'right': 0.5,

&nbsp;           'top': 0.5,

&nbsp;           'bottom': 0.5

&nbsp;       }

&nbsp;       

&nbsp;       # Calculate available space

&nbsp;       available\_width = self.page\_width - self.margins\['left'] - self.margins\['right']  # 7.5"

&nbsp;       available\_height = self.page\_height - self.margins\['top'] - self.margins\['bottom']  # 10.0"

&nbsp;       

&nbsp;       # Title block settings (at bottom with margin)

&nbsp;       self.title\_block\_frame = {

&nbsp;           'x': self.margins\['left'],

&nbsp;           'y': self.margins\['bottom'],

&nbsp;           'width': available\_width,

&nbsp;           'height': 1.75

&nbsp;       }

&nbsp;       

&nbsp;       # Main map frame - extends from left margin to right margin, under vicinity map

&nbsp;       # Leave 0.5" space above title block

&nbsp;       map\_top = self.page\_height - self.margins\['top']

&nbsp;       map\_bottom = self.title\_block\_frame\['y'] + self.title\_block\_frame\['height'] + 0.5  # 0.5" gap above title block

&nbsp;       

&nbsp;       self.main\_map\_frame = {

&nbsp;           'x': self.margins\['left'],

&nbsp;           'y': map\_bottom,

&nbsp;           'width': available\_width,

&nbsp;           'height': map\_top - map\_bottom

&nbsp;       }

&nbsp;       

&nbsp;       # Vicinity map settings (top right corner with margins)

&nbsp;       vicinity\_size = 1.75

&nbsp;       self.vicinity\_map\_frame = {

&nbsp;           'x': self.page\_width - self.margins\['right'] - vicinity\_size,

&nbsp;           'y': self.page\_height - self.margins\['top'] - vicinity\_size,

&nbsp;           'width': vicinity\_size,

&nbsp;           'height': vicinity\_size

&nbsp;       }

&nbsp;       

&nbsp;       # After main\_map\_frame definition, update north arrow pos

&nbsp;       self.north\_arrow\_pos = {

&nbsp;           'x': self.page\_width - self.margins\['right'] - 0.4,

&nbsp;           'y': self.main\_map\_frame\['y'] + 0.4,

&nbsp;           'size': 0.4

&nbsp;       }

&nbsp;       

&nbsp;       # Legend position remains the same

&nbsp;       legend\_height = 0.6

&nbsp;       self.legend\_pos = {

&nbsp;           'x': self.main\_map\_frame\['x'] + 0.1,

&nbsp;           # Align legend TOP with top of main map minus small gap (0.1")

&nbsp;           'y': self.main\_map\_frame\['y'] + self.main\_map\_frame\['height'] - legend\_height - 0.1,

&nbsp;           'width': 1.5,

&nbsp;           'height': legend\_height

&nbsp;       }

&nbsp;   

&nbsp;   def generate\_location\_map(self, 

&nbsp;                           site\_boundary: gpd.GeoDataFrame,

&nbsp;                           project\_info: Dict,

&nbsp;                           output\_path: str,

&nbsp;                           base\_map\_type: str = "satellite",

&nbsp;                           include\_vicinity: bool = True,

&nbsp;                           custom\_layers: Optional\[List\[gpd.GeoDataFrame]] = None) -> bool:

&nbsp;       """

&nbsp;       Generate a complete location map exhibit

&nbsp;       

&nbsp;       Args:

&nbsp;           site\_boundary: GeoDataFrame containing site boundary polygon(s)

&nbsp;           project\_info: Dictionary with project information for title block

&nbsp;           output\_path: Path for output PDF file

&nbsp;           base\_map\_type: Type of base map ("satellite", "terrain", "street")

&nbsp;           include\_vicinity: Whether to include vicinity map

&nbsp;           custom\_layers: Additional layers to include on the map

&nbsp;           

&nbsp;       Returns:

&nbsp;           True if successful, False otherwise

&nbsp;       """

&nbsp;       try:

&nbsp;           logger.info("Starting location map generation")

&nbsp;           

&nbsp;           # Ensure site boundary is in Web Mercator for contextily

&nbsp;           site\_boundary\_wm = site\_boundary.to\_crs('EPSG:3857')

&nbsp;           

&nbsp;           # Calculate optimal scale for main map

&nbsp;           optimal\_scale = self.\_calculate\_optimal\_scale(site\_boundary\_wm)

&nbsp;           logger.info(f"Calculated optimal scale: 1\\" = {optimal\_scale}'")

&nbsp;           

&nbsp;           # Create the PDF

&nbsp;           with PdfPages(output\_path) as pdf:

&nbsp;               fig = plt.figure(figsize=(self.page\_width, self.page\_height))

&nbsp;               fig.patch.set\_facecolor('white')

&nbsp;               

&nbsp;               # Create main map

&nbsp;               main\_ax = self.\_create\_main\_map(fig, site\_boundary\_wm, optimal\_scale, base\_map\_type)

&nbsp;               

&nbsp;               # Create vicinity map if requested

&nbsp;               if include\_vicinity:

&nbsp;                   vicinity\_ax = self.\_create\_vicinity\_map(fig, site\_boundary\_wm)

&nbsp;               

&nbsp;               # Add cartographic elements

&nbsp;               self.\_add\_north\_arrow(fig)

&nbsp;               self.\_add\_legend(fig)

&nbsp;               

&nbsp;               # Add title block

&nbsp;               self.\_add\_title\_block(fig, project\_info, optimal\_scale)

&nbsp;               

&nbsp;               # Save to PDF

&nbsp;               pdf.savefig(fig, dpi=self.dpi)

&nbsp;               plt.close(fig)

&nbsp;           

&nbsp;           logger.info(f"Location map successfully generated: {output\_path}")

&nbsp;           return True

&nbsp;           

&nbsp;       except Exception as e:

&nbsp;           logger.error(f"Error generating location map: {e}")

&nbsp;           return False

&nbsp;   

&nbsp;   def \_calculate\_optimal\_scale(self, site\_boundary\_wm: gpd.GeoDataFrame) -> int:

&nbsp;       """

&nbsp;       Calculate the optimal engineering scale for the site with buffer

&nbsp;       

&nbsp;       Args:

&nbsp;           site\_boundary\_wm: Site boundary in Web Mercator projection

&nbsp;           

&nbsp;       Returns:

&nbsp;           Optimal scale (feet per inch) with buffer to prevent boundary cutoff

&nbsp;       """

&nbsp;       # Get bounds in Web Mercator

&nbsp;       bounds = site\_boundary\_wm.total\_bounds

&nbsp;       width\_m = bounds\[2] - bounds\[0]

&nbsp;       height\_m = bounds\[3] - bounds\[1]

&nbsp;       

&nbsp;       # Convert to feet

&nbsp;       width\_ft = width\_m \* 3.28084

&nbsp;       height\_ft = height\_m \* 3.28084

&nbsp;       

&nbsp;       # Calculate scale needed to fit in main map frame (with 20% buffer)

&nbsp;       # Account for vicinity map overlap in the top right

&nbsp;       effective\_width = self.main\_map\_frame\['width'] \* 0.8

&nbsp;       effective\_height = self.main\_map\_frame\['height'] \* 0.8

&nbsp;       

&nbsp;       scale\_x = width\_ft / effective\_width

&nbsp;       scale\_y = height\_ft / effective\_height

&nbsp;       

&nbsp;       # Use the larger scale (smaller ratio) to ensure everything fits

&nbsp;       required\_scale = max(scale\_x, scale\_y)

&nbsp;       

&nbsp;       # Find the optimal scale, then bump it up to provide buffer

&nbsp;       optimal\_scale = None

&nbsp;       for scale in self.standard\_scales:

&nbsp;           if scale >= required\_scale:

&nbsp;               optimal\_scale = scale

&nbsp;               break

&nbsp;       

&nbsp;       # If no scale found, use the largest

&nbsp;       if optimal\_scale is None:

&nbsp;           return self.standard\_scales\[-1]

&nbsp;       

&nbsp;       # Find the index of the optimal scale

&nbsp;       try:

&nbsp;           scale\_index = self.standard\_scales.index(optimal\_scale)

&nbsp;           

&nbsp;           # Bump up to next scale level to provide buffer (skip 1 level)

&nbsp;           # This ensures AOI boundary won't be cut off

&nbsp;           if scale\_index + 1 < len(self.standard\_scales):

&nbsp;               return self.standard\_scales\[scale\_index + 1]

&nbsp;           else:

&nbsp;               # If already at the largest scale, use it

&nbsp;               return optimal\_scale

&nbsp;               

&nbsp;       except ValueError:

&nbsp;           return optimal\_scale

&nbsp;   

&nbsp;   def \_create\_main\_map(self, fig: plt.Figure, site\_boundary\_wm: gpd.GeoDataFrame, 

&nbsp;                       scale: int, base\_map\_type: str) -> plt.Axes:

&nbsp;       """

&nbsp;       Create the main site map

&nbsp;       

&nbsp;       Args:

&nbsp;           fig: Matplotlib figure

&nbsp;           site\_boundary\_wm: Site boundary in Web Mercator

&nbsp;           scale: Map scale (feet per inch)

&nbsp;           base\_map\_type: Type of base map

&nbsp;           

&nbsp;       Returns:

&nbsp;           Matplotlib axes object

&nbsp;       """

&nbsp;       # Create axes for main map

&nbsp;       ax = fig.add\_axes(\[

&nbsp;           self.main\_map\_frame\['x'] / self.page\_width,

&nbsp;           self.main\_map\_frame\['y'] / self.page\_height,

&nbsp;           self.main\_map\_frame\['width'] / self.page\_width,

&nbsp;           self.main\_map\_frame\['height'] / self.page\_height  # correct height ratio

&nbsp;       ])

&nbsp;       

&nbsp;       # Calculate map extent based on scale

&nbsp;       map\_width\_ft = self.main\_map\_frame\['width'] \* scale

&nbsp;       map\_height\_ft = self.main\_map\_frame\['height'] \* scale

&nbsp;       

&nbsp;       # Convert to meters

&nbsp;       map\_width\_m = map\_width\_ft / 3.28084

&nbsp;       map\_height\_m = map\_height\_ft / 3.28084

&nbsp;       

&nbsp;       # Get site centroid

&nbsp;       site\_centroid = site\_boundary\_wm.geometry.centroid.iloc\[0]

&nbsp;       

&nbsp;       # Calculate map bounds centered on site

&nbsp;       minx = site\_centroid.x - map\_width\_m / 2

&nbsp;       maxx = site\_centroid.x + map\_width\_m / 2

&nbsp;       miny = site\_centroid.y - map\_height\_m / 2

&nbsp;       maxy = site\_centroid.y + map\_height\_m / 2

&nbsp;       

&nbsp;       # Set map extent

&nbsp;       ax.set\_xlim(minx, maxx)

&nbsp;       ax.set\_ylim(miny, maxy)

&nbsp;       

&nbsp;       # Add base map (without attribution for clean professional appearance)

&nbsp;       try:

&nbsp;           if base\_map\_type == "satellite":

&nbsp;               ctx.add\_basemap(ax, crs=site\_boundary\_wm.crs, source=ctx.providers.Esri.WorldImagery, attribution="")

&nbsp;           elif base\_map\_type == "terrain":

&nbsp;               ctx.add\_basemap(ax, crs=site\_boundary\_wm.crs, source=ctx.providers.USGS.USTopo, attribution="")

&nbsp;           else:  # street

&nbsp;               ctx.add\_basemap(ax, crs=site\_boundary\_wm.crs, source=ctx.providers.OpenStreetMap.Mapnik, attribution="")

&nbsp;       except Exception as e:

&nbsp;           logger.warning(f"Could not load base map: {e}")

&nbsp;           ax.set\_facecolor('lightgray')

&nbsp;       

&nbsp;       # Plot site boundary

&nbsp;       site\_boundary\_wm.plot(ax=ax, facecolor='none', edgecolor='red', linewidth=3, alpha=0.8)

&nbsp;       

&nbsp;       # Remove axes

&nbsp;       ax.set\_xticks(\[])

&nbsp;       ax.set\_yticks(\[])

&nbsp;       

&nbsp;       # Add border

&nbsp;       for spine in ax.spines.values():

&nbsp;           spine.set\_visible(True)

&nbsp;           spine.set\_linewidth(2)

&nbsp;           spine.set\_color('black')

&nbsp;       

&nbsp;       return ax

&nbsp;   

&nbsp;   def \_create\_vicinity\_map(self, fig: plt.Figure, site\_boundary\_wm: gpd.GeoDataFrame) -> plt.Axes:

&nbsp;       """

&nbsp;       Create the vicinity/location map

&nbsp;       

&nbsp;       Args:

&nbsp;           fig: Matplotlib figure

&nbsp;           site\_boundary\_wm: Site boundary in Web Mercator

&nbsp;           

&nbsp;       Returns:

&nbsp;           Matplotlib axes object

&nbsp;       """

&nbsp;       # Create axes for vicinity map

&nbsp;       ax = fig.add\_axes(\[

&nbsp;           self.vicinity\_map\_frame\['x'] / self.page\_width,

&nbsp;           self.vicinity\_map\_frame\['y'] / self.page\_height,

&nbsp;           self.vicinity\_map\_frame\['width'] / self.page\_width,

&nbsp;           self.vicinity\_map\_frame\['height'] / self.page\_height

&nbsp;       ])

&nbsp;       

&nbsp;       # Get site centroid

&nbsp;       site\_centroid = site\_boundary\_wm.geometry.centroid.iloc\[0]

&nbsp;       

&nbsp;       # Create larger extent for vicinity map (approximately 10x larger)

&nbsp;       site\_bounds = site\_boundary\_wm.total\_bounds

&nbsp;       width = site\_bounds\[2] - site\_bounds\[0]

&nbsp;       height = site\_bounds\[3] - site\_bounds\[1]

&nbsp;       

&nbsp;       # Expand bounds for vicinity context

&nbsp;       buffer = max(width, height) \* 5  # 5x buffer

&nbsp;       

&nbsp;       minx = site\_centroid.x - buffer

&nbsp;       maxx = site\_centroid.x + buffer

&nbsp;       miny = site\_centroid.y - buffer

&nbsp;       maxy = site\_centroid.y + buffer

&nbsp;       

&nbsp;       # Set extent

&nbsp;       ax.set\_xlim(minx, maxx)

&nbsp;       ax.set\_ylim(miny, maxy)

&nbsp;       

&nbsp;       # Add base map (without attribution for clean professional appearance)

&nbsp;       try:

&nbsp;           ctx.add\_basemap(ax, crs=site\_boundary\_wm.crs, source=ctx.providers.OpenStreetMap.Mapnik, attribution="")

&nbsp;       except Exception as e:

&nbsp;           logger.warning(f"Could not load vicinity base map: {e}")

&nbsp;           ax.set\_facecolor('lightblue')

&nbsp;       

&nbsp;       # Plot site location as a point

&nbsp;       site\_centroid\_gdf = gpd.GeoDataFrame(\[1], geometry=\[site\_centroid], crs=site\_boundary\_wm.crs)

&nbsp;       site\_centroid\_gdf.plot(ax=ax, color='red', markersize=50, marker='\*')

&nbsp;       

&nbsp;       # Remove axes

&nbsp;       ax.set\_xticks(\[])

&nbsp;       ax.set\_yticks(\[])

&nbsp;       

&nbsp;       # Add border

&nbsp;       for spine in ax.spines.values():

&nbsp;           spine.set\_visible(True)

&nbsp;           spine.set\_linewidth(1)

&nbsp;           spine.set\_color('black')

&nbsp;       

&nbsp;       # Remove vicinity map title text as requested

&nbsp;       

&nbsp;       return ax

&nbsp;   

&nbsp;   def \_add\_north\_arrow(self, fig: plt.Figure):

&nbsp;       """Add north arrow to the map"""

&nbsp;       # Create north arrow at specified position

&nbsp;       ax = fig.add\_axes(\[

&nbsp;           self.north\_arrow\_pos\['x'] / self.page\_width,

&nbsp;           self.north\_arrow\_pos\['y'] / self.page\_height,

&nbsp;           self.north\_arrow\_pos\['size'] / self.page\_width,

&nbsp;           self.north\_arrow\_pos\['size'] / self.page\_height

&nbsp;       ])

&nbsp;       

&nbsp;       ax.set\_xlim(-1, 1)

&nbsp;       ax.set\_ylim(-1, 1)

&nbsp;       ax.axis('off')

&nbsp;       

&nbsp;       # Draw arrow

&nbsp;       arrow = patches.FancyArrowPatch((0, -0.7), (0, 0.7),

&nbsp;                                     arrowstyle='->', mutation\_scale=20,

&nbsp;                                     color='black', linewidth=2)

&nbsp;       ax.add\_patch(arrow)

&nbsp;       

&nbsp;       # Add "N" label

&nbsp;       ax.text(0, 0.9, 'N', ha='center', va='center', fontsize=12, fontweight='bold')

&nbsp;   

&nbsp;   def \_add\_legend(self, fig: plt.Figure):

&nbsp;       """Add legend to the map with white background and black border"""

&nbsp;       # Create legend at specified position (top left of main map)

&nbsp;       ax = fig.add\_axes(\[

&nbsp;           self.legend\_pos\['x'] / self.page\_width,

&nbsp;           self.legend\_pos\['y'] / self.page\_height,

&nbsp;           self.legend\_pos\['width'] / self.page\_width,

&nbsp;           self.legend\_pos\['height'] / self.page\_height

&nbsp;       ])

&nbsp;       

&nbsp;       ax.set\_xlim(0, 1)

&nbsp;       ax.set\_ylim(0, 1)

&nbsp;       ax.axis('off')

&nbsp;       

&nbsp;       # Add white background with black border

&nbsp;       background = Rectangle((0, 0), 1, 1, facecolor='white', edgecolor='black', linewidth=1)

&nbsp;       ax.add\_patch(background)

&nbsp;       

&nbsp;       # Add legend items

&nbsp;       # Site boundary

&nbsp;       line = plt.Line2D(\[0.1, 0.3], \[0.4, 0.4], color='red', linewidth=3)

&nbsp;       ax.add\_line(line)

&nbsp;       ax.text(0.35, 0.4, 'SITE BOUNDARY', va='center', fontsize=8)

&nbsp;       

&nbsp;       # Legend title

&nbsp;       ax.text(0.5, 0.7, 'LEGEND', ha='center', va='center', fontsize=9, fontweight='bold')

&nbsp;   

&nbsp;   def \_add\_title\_block(self, fig: plt.Figure, project\_info: Dict, scale: int):

&nbsp;       """Add title block with project information"""

&nbsp;       # Create title block axes

&nbsp;       ax = fig.add\_axes(\[

&nbsp;           self.title\_block\_frame\['x'] / self.page\_width,

&nbsp;           self.title\_block\_frame\['y'] / self.page\_height,

&nbsp;           self.title\_block\_frame\['width'] / self.page\_width,

&nbsp;           self.title\_block\_frame\['height'] / self.page\_height

&nbsp;       ])

&nbsp;       

&nbsp;       ax.set\_xlim(0, 1)

&nbsp;       ax.set\_ylim(0, 1)

&nbsp;       ax.axis('off')

&nbsp;       

&nbsp;       # Draw title block border

&nbsp;       border = Rectangle((0, 0), 1, 1, facecolor='none', edgecolor='black', linewidth=2)

&nbsp;       ax.add\_patch(border)

&nbsp;       

&nbsp;       # Add project information (all text converted to uppercase)

&nbsp;       project\_name = project\_info.get('name', 'PROJECT NAME').upper()

&nbsp;       project\_number = project\_info.get('number', 'PROJECT NUMBER').upper()

&nbsp;       client = project\_info.get('client', 'CLIENT NAME').upper()

&nbsp;       date = project\_info.get('date', datetime.now().strftime('%m/%d/%Y')).upper()

&nbsp;       drawn\_by = project\_info.get('drawn\_by', 'INITIALS').upper()

&nbsp;       

&nbsp;       # Title

&nbsp;       ax.text(0.5, 0.85, 'LOCATION MAP', ha='center', va='center', 

&nbsp;               fontsize=16, fontweight='bold')

&nbsp;       

&nbsp;       # Project info - left side

&nbsp;       ax.text(0.05, 0.65, f'PROJECT: {project\_name}', ha='left', va='center', fontsize=10)

&nbsp;       ax.text(0.05, 0.55, f'PROJECT NO: {project\_number}', ha='left', va='center', fontsize=10)

&nbsp;       ax.text(0.05, 0.45, f'CLIENT: {client}', ha='left', va='center', fontsize=10)

&nbsp;       

&nbsp;       # Drawing info - right side

&nbsp;       ax.text(0.95, 0.65, f'SCALE: 1" = {scale}\\'', ha='right', va='center', fontsize=10)

&nbsp;       ax.text(0.95, 0.55, f'DATE: {date}', ha='right', va='center', fontsize=10)

&nbsp;       ax.text(0.95, 0.45, f'DRAWN BY: {drawn\_by}', ha='right', va='center', fontsize=10)

&nbsp;       

&nbsp;       # Sheet info

&nbsp;       ax.text(0.5, 0.15, 'SHEET 1 OF 1', ha='center', va='center', fontsize=10)

&nbsp;       

&nbsp;       # Add horizontal divider lines

&nbsp;       ax.axhline(y=0.35, xmin=0.02, xmax=0.98, color='black', linewidth=1)

&nbsp;       ax.axhline(y=0.75, xmin=0.02, xmax=0.98, color='black', linewidth=1)





def create\_location\_map(aoi\_file\_path: str, project\_info: Dict, output\_path: str, 

&nbsp;                      base\_map\_type: str = "satellite") -> bool:

&nbsp;   """

&nbsp;   Convenience function to create a location map from an AOI file

&nbsp;   

&nbsp;   Args:

&nbsp;       aoi\_file\_path: Path to AOI shapefile

&nbsp;       project\_info: Project information dictionary

&nbsp;       output\_path: Output PDF path

&nbsp;       base\_map\_type: Type of base map to use

&nbsp;       

&nbsp;   Returns:

&nbsp;       True if successful, False otherwise

&nbsp;   """

&nbsp;   try:

&nbsp;       # Load AOI

&nbsp;       aoi\_gdf = gpd.read\_file(aoi\_file\_path)

&nbsp;       

&nbsp;       # Create map generator

&nbsp;       generator = LocationMapGenerator()

&nbsp;       

&nbsp;       # Generate map

&nbsp;       return generator.generate\_location\_map(

&nbsp;           site\_boundary=aoi\_gdf,

&nbsp;           project\_info=project\_info,

&nbsp;           output\_path=output\_path,

&nbsp;           base\_map\_type=base\_map\_type

&nbsp;       )

&nbsp;       

&nbsp;   except Exception as e:

&nbsp;       logger.error(f"Error creating location map: {e}")

&nbsp;       return False 

