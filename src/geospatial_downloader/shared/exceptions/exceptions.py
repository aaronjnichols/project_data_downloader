"""Core exception classes for the geospatial downloader package."""

from typing import Any, Dict, Optional


class GeospatialDownloaderException(Exception):
    """Base exception for all geospatial downloader errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error context
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class AOIValidationError(GeospatialDownloaderException):
    """Raised when Area of Interest validation fails."""

    def __init__(
        self,
        message: str,
        aoi_area: Optional[float] = None,
        max_allowed: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize AOI validation error.
        
        Args:
            message: Error description
            aoi_area: Actual AOI area in km²
            max_allowed: Maximum allowed area in km²
            **kwargs: Additional arguments for base class
        """
        details = kwargs.get("details", {})
        if aoi_area is not None:
            details["aoi_area_km2"] = aoi_area
        if max_allowed is not None:
            details["max_allowed_km2"] = max_allowed
        
        super().__init__(message, error_code="AOI_VALIDATION_FAILED", details=details)


class DataSourceError(GeospatialDownloaderException):
    """Raised when data source operations fail."""

    def __init__(
        self,
        message: str,
        source_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize data source error.
        
        Args:
            message: Error description
            source_id: ID of the failing data source
            **kwargs: Additional arguments for base class
        """
        details = kwargs.get("details", {})
        if source_id:
            details["source_id"] = source_id
            
        super().__init__(message, error_code="DATA_SOURCE_ERROR", details=details)


class DownloadError(GeospatialDownloaderException):
    """Raised when download operations fail."""

    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        layer_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize download error.
        
        Args:
            message: Error description
            job_id: ID of the failing job
            layer_id: ID of the failing layer
            **kwargs: Additional arguments for base class
        """
        details = kwargs.get("details", {})
        if job_id:
            details["job_id"] = job_id
        if layer_id:
            details["layer_id"] = layer_id
            
        super().__init__(message, error_code="DOWNLOAD_ERROR", details=details)


class ConfigurationError(GeospatialDownloaderException):
    """Raised when configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize configuration error.
        
        Args:
            message: Error description
            config_key: Configuration key that caused the error
            **kwargs: Additional arguments for base class
        """
        details = kwargs.get("details", {})
        if config_key:
            details["config_key"] = config_key
            
        super().__init__(message, error_code="CONFIGURATION_ERROR", details=details)


class APIError(GeospatialDownloaderException):
    """Raised when API calls fail."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        endpoint: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize API error.
        
        Args:
            message: Error description
            status_code: HTTP status code
            endpoint: API endpoint that failed
            **kwargs: Additional arguments for base class
        """
        details = kwargs.get("details", {})
        if status_code:
            details["status_code"] = status_code
        if endpoint:
            details["endpoint"] = endpoint
            
        super().__init__(message, error_code="API_ERROR", details=details)