"""Geospatial Data Downloader Package.

A comprehensive solution for downloading geospatial data from multiple federal
and public sources including FEMA, USGS, and NOAA.

Author: Project Team
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Project Team"
__email__ = "team@example.com"

# Package level imports for convenience
from .shared.exceptions import GeospatialDownloaderException

__all__ = [
    "__version__",
    "__author__", 
    "__email__",
    "GeospatialDownloaderException",
]