"""Exception classes for the geospatial downloader package."""

from .exceptions import (
    APIError,
    AOIValidationError,
    ConfigurationError,
    DataSourceError,
    DownloadError,
    GeospatialDownloaderException,
)

__all__ = [
    "GeospatialDownloaderException",
    "AOIValidationError", 
    "DataSourceError",
    "DownloadError",
    "ConfigurationError",
    "APIError",
]