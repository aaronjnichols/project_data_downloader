"""Unit tests for exception classes."""

import pytest

from geospatial_downloader.shared.exceptions import (
    APIError,
    AOIValidationError,
    ConfigurationError,
    DataSourceError,
    DownloadError,
    GeospatialDownloaderException,
)


class TestGeospatialDownloaderException:
    """Test base exception class."""

    def test_basic_exception(self):
        """Test basic exception creation."""
        exc = GeospatialDownloaderException("Test message")
        assert str(exc) == "Test message"
        assert exc.message == "Test message"
        assert exc.error_code is None
        assert exc.details == {}

    def test_exception_with_details(self):
        """Test exception with error code and details."""
        details = {"key": "value", "number": 42}
        exc = GeospatialDownloaderException(
            "Test message", error_code="TEST_ERROR", details=details
        )
        assert exc.error_code == "TEST_ERROR"
        assert exc.details == details


class TestAOIValidationError:
    """Test AOI validation error."""

    def test_aoi_validation_error(self):
        """Test AOI validation error with area details."""
        exc = AOIValidationError(
            "AOI too large", aoi_area=15000.0, max_allowed=10000.0
        )
        assert exc.error_code == "AOI_VALIDATION_FAILED"
        assert exc.details["aoi_area_km2"] == 15000.0
        assert exc.details["max_allowed_km2"] == 10000.0


class TestDataSourceError:
    """Test data source error."""

    def test_data_source_error(self):
        """Test data source error with source ID."""
        exc = DataSourceError("Source unavailable", source_id="fema")
        assert exc.error_code == "DATA_SOURCE_ERROR"
        assert exc.details["source_id"] == "fema"


class TestDownloadError:
    """Test download error."""

    def test_download_error(self):
        """Test download error with job and layer IDs."""
        exc = DownloadError(
            "Download failed", job_id="job-123", layer_id="layer-456"
        )
        assert exc.error_code == "DOWNLOAD_ERROR"
        assert exc.details["job_id"] == "job-123"
        assert exc.details["layer_id"] == "layer-456"


class TestConfigurationError:
    """Test configuration error."""

    def test_configuration_error(self):
        """Test configuration error with config key."""
        exc = ConfigurationError("Missing config", config_key="api_base_url")
        assert exc.error_code == "CONFIGURATION_ERROR"
        assert exc.details["config_key"] == "api_base_url"


class TestAPIError:
    """Test API error."""

    def test_api_error(self):
        """Test API error with status code and endpoint."""
        exc = APIError(
            "API call failed", status_code=404, endpoint="/api/v1/jobs"
        )
        assert exc.error_code == "API_ERROR"
        assert exc.details["status_code"] == 404
        assert exc.details["endpoint"] == "/api/v1/jobs"