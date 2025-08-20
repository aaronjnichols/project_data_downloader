"""
Abstract base class for all data source downloaders.
Defines the standard interface that all downloader plugins must implement.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any, Union, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    pass  # For forward references
import logging
import os
import time
from functools import wraps
import geopandas as gpd
import random
from enum import Enum


class RetryStrategy(Enum):
    """Retry strategy enumeration"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_DELAY = "fixed_delay"
    LINEAR_BACKOFF = "linear_backoff"
    IMMEDIATE = "immediate"


class ErrorSeverity(Enum):
    """Error severity levels"""
    RECOVERABLE = "recoverable"  # Can retry
    TEMPORARY = "temporary"      # Should retry with delay
    PERMANENT = "permanent"      # Should not retry


@dataclass
class LayerInfo:
    """Information about a data layer/dataset"""
    id: str
    name: str
    description: str
    geometry_type: str  # Point, Polyline, Polygon, Raster
    data_type: str      # Vector, Raster, PointCloud
    attributes: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class DownloadResult:
    """Result of a layer download operation"""
    success: bool
    layer_id: str
    feature_count: int = 0
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


class BaseDownloader(ABC):
    """Abstract base class for all data source downloaders"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the downloader with configuration
        
        Args:
            config: Dictionary containing downloader-specific configuration
        """
        self.config = config or {}
        self.name = self.__class__.__name__
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the human-readable name of this data source"""
        pass
    
    @property
    @abstractmethod
    def source_description(self) -> str:
        """Return a description of this data source"""
        pass
    
    @abstractmethod
    def get_available_layers(self) -> Dict[str, LayerInfo]:
        """
        Return information about all available layers/datasets
        
        Returns:
            Dictionary mapping layer IDs to LayerInfo objects
        """
        pass
    
    @abstractmethod
    def download_layer(self, layer_id: str, aoi_bounds: Tuple[float, float, float, float], 
                      output_path: str, **kwargs) -> DownloadResult:
        """
        Download a specific layer within the AOI bounds
        
        Args:
            layer_id: Identifier of the layer to download
            aoi_bounds: Tuple of (minx, miny, maxx, maxy) in EPSG:4326
            output_path: Directory path where files should be saved
            **kwargs: Additional downloader-specific parameters
            
        Returns:
            DownloadResult object with success status and details
        """
        pass
    
    def get_layer_metadata(self, layer_id: str) -> Dict[str, Any]:
        """
        Get metadata for a specific layer
        
        Args:
            layer_id: Identifier of the layer
            
        Returns:
            Dictionary containing layer metadata
        """
        layers = self.get_available_layers()
        if layer_id in layers:
            return layers[layer_id].metadata or {}
        return {}
    
    def validate_aoi(self, aoi_bounds: Tuple[float, float, float, float]) -> bool:
        """
        Validate that the AOI is acceptable for this data source
        
        Args:
            aoi_bounds: Tuple of (minx, miny, maxx, maxy) in EPSG:4326
            
        Returns:
            True if AOI is valid, False otherwise
        """
        # Default implementation - basic bounds checking
        minx, miny, maxx, maxy = aoi_bounds
        
        # Check for valid bounds
        if minx >= maxx or miny >= maxy:
            return False
            
        # Check for reasonable geographic bounds (WGS84)
        if not (-180 <= minx <= 180 and -180 <= maxx <= 180):
            return False
        if not (-90 <= miny <= 90 and -90 <= maxy <= 90):
            return False
            
        return True
    
    def supports_layer(self, layer_id: str) -> bool:
        """
        Check if this downloader supports a specific layer
        
        Args:
            layer_id: Identifier of the layer
            
        Returns:
            True if layer is supported, False otherwise
        """
        return layer_id in self.get_available_layers()
    
    def get_configuration_schema(self) -> Dict[str, Any]:
        """
        Return the configuration schema for this downloader
        Override in subclasses to provide specific schema
        
        Returns:
            Dictionary describing the configuration parameters
        """
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def _create_error_result(self, layer_id: str, error_message: str) -> DownloadResult:
        """
        Helper method to create standardized error results
        
        Args:
            layer_id: The layer that failed
            error_message: Description of the error
            
        Returns:
            DownloadResult indicating failure
        """
        self.logger.error(f"Download failed for layer {layer_id}: {error_message}")
        return DownloadResult(
            success=False,
            layer_id=layer_id,
            error_message=error_message
        )
    
    def _create_success_result(self, layer_id: str, file_path: str, 
                             feature_count: int = 0, file_size_bytes: Optional[int] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> DownloadResult:
        """
        Helper method to create standardized success results
        
        Args:
            layer_id: The layer that was downloaded
            file_path: Path to the downloaded file
            feature_count: Number of features downloaded
            file_size_bytes: Size of the downloaded file
            metadata: Additional metadata
            
        Returns:
            DownloadResult indicating success
        """
        self.logger.info(f"Successfully downloaded layer {layer_id}: {feature_count} features")
        return DownloadResult(
            success=True,
            layer_id=layer_id,
            file_path=file_path,
            feature_count=feature_count,
            file_size_bytes=file_size_bytes,
            metadata=metadata or {}
        )
    
    def _validate_layer_id(self, layer_id: str) -> bool:
        """
        Helper method to validate layer ID exists
        
        Args:
            layer_id: Layer ID to validate
            
        Returns:
            True if layer exists, False otherwise
        """
        if not self.supports_layer(layer_id):
            self.logger.warning(f"Layer {layer_id} not supported by {self.source_name}")
            return False
        return True
    
    def _safe_file_operation(self, operation_func, *args, **kwargs):
        """
        Safely execute file operations with error handling
        
        Args:
            operation_func: Function to execute safely
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of operation_func or None if error occurred
        """
        try:
            return operation_func(*args, **kwargs)
        except PermissionError as e:
            self.logger.error(f"Permission denied during file operation: {e}")
            return None
        except OSError as e:
            self.logger.error(f"OS error during file operation: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during file operation: {e}")
            return None
    
    def _validate_output_path(self, output_path: str) -> bool:
        """
        Validate and prepare output path
        
        Args:
            output_path: Path to validate
            
        Returns:
            True if path is valid and accessible, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(output_path, exist_ok=True)
            
            # Test write permissions
            test_file = os.path.join(output_path, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            return True
        except Exception as e:
            self.logger.error(f"Output path validation failed for {output_path}: {e}")
            return False
    
    def _log_download_attempt(self, layer_id: str, aoi_bounds: Tuple[float, float, float, float]):
        """
        Log download attempt with consistent formatting
        
        Args:
            layer_id: Layer being downloaded
            aoi_bounds: Area of interest bounds
        """
        minx, miny, maxx, maxy = aoi_bounds
        bbox_str = f"({minx:.6f}, {miny:.6f}, {maxx:.6f}, {maxy:.6f})"
        self.logger.info(f"Starting download: {self.source_name} layer '{layer_id}' for AOI {bbox_str}")
    
    def _log_download_success(self, result: 'DownloadResult'):
        """
        Log successful download with metrics
        
        Args:
            result: Download result to log
        """
        file_size_mb = ""
        if result.file_size_bytes:
            file_size_mb = f" ({result.file_size_bytes / (1024*1024):.2f} MB)"
        
        feature_info = ""
        if result.feature_count > 0:
            feature_info = f" with {result.feature_count} features"
        
        self.logger.info(f"Download completed: {result.layer_id}{feature_info}{file_size_mb}")
    
    def _measure_execution_time(self, func):
        """
        Decorator to measure and log execution time
        
        Args:
            func: Function to measure
            
        Returns:
            Decorated function that logs execution time
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                self.logger.info(f"{func.__name__} completed in {execution_time:.2f} seconds")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                self.logger.error(f"{func.__name__} failed after {execution_time:.2f} seconds: {e}")
                raise
        return wrapper
    
    def _handle_network_error(self, error: Exception, layer_id: str, attempt: int = 1, max_attempts: int = 1) -> Optional[DownloadResult]:
        """
        Handle network-related errors with appropriate logging and retry logic
        
        Args:
            error: The network error that occurred
            layer_id: Layer ID being downloaded
            attempt: Current attempt number
            max_attempts: Maximum number of attempts
            
        Returns:
            DownloadResult if this is the final attempt, None if should retry
        """
        import requests
        
        if isinstance(error, requests.exceptions.Timeout):
            if attempt < max_attempts:
                self.logger.warning(f"Timeout on attempt {attempt}/{max_attempts} for layer {layer_id}, retrying...")
                return None
            else:
                return self._create_error_result(layer_id, f"Request timed out after {max_attempts} attempts")
        
        elif isinstance(error, requests.exceptions.ConnectionError):
            if attempt < max_attempts:
                self.logger.warning(f"Connection error on attempt {attempt}/{max_attempts} for layer {layer_id}, retrying...")
                return None
            else:
                return self._create_error_result(layer_id, f"Connection failed after {max_attempts} attempts")
        
        elif isinstance(error, requests.exceptions.HTTPError):
            status_code = getattr(error.response, 'status_code', 'unknown')
            return self._create_error_result(layer_id, f"HTTP error {status_code}: {error}")
        
        else:
            return self._create_error_result(layer_id, f"Network error: {error}")
    
    def _create_safe_filename(self, base_name: str, extension: str = "") -> str:
        """
        Create a safe filename by removing invalid characters
        
        Args:
            base_name: Base filename
            extension: File extension (with or without dot)
            
        Returns:
            Safe filename
        """
        import re
        
        # Remove invalid characters
        safe_name = re.sub(r'[<>:"/\|?*]', '_', base_name)
        safe_name = re.sub(r'\s+', '_', safe_name)  # Replace spaces with underscores
        safe_name = safe_name.strip('._')  # Remove leading/trailing dots and underscores
        
        if extension:
            if not extension.startswith('.'):
                extension = '.' + extension
            safe_name += extension
        
        return safe_name
    
    def _classify_error(self, error: Exception) -> ErrorSeverity:
        """
        Classify error severity to determine retry strategy
        
        Args:
            error: Exception to classify
            
        Returns:
            ErrorSeverity indicating how to handle the error
        """
        import requests
        
        # Network-related errors that should be retried
        if isinstance(error, (requests.exceptions.Timeout, 
                            requests.exceptions.ConnectionError)):
            return ErrorSeverity.TEMPORARY
        
        # HTTP errors - some are retryable, others are not
        if isinstance(error, requests.exceptions.HTTPError):
            status_code = getattr(error.response, 'status_code', 500)
            if status_code in [429, 500, 502, 503, 504]:  # Rate limit and server errors
                return ErrorSeverity.TEMPORARY
            elif status_code in [400, 401, 403, 404]:  # Client errors
                return ErrorSeverity.PERMANENT
            else:
                return ErrorSeverity.RECOVERABLE
        
        # File system errors
        if isinstance(error, (OSError, IOError)):
            if isinstance(error, PermissionError):
                return ErrorSeverity.PERMANENT
            else:
                return ErrorSeverity.RECOVERABLE
        
        # Memory errors
        if isinstance(error, MemoryError):
            return ErrorSeverity.TEMPORARY
        
        # Default to recoverable for unknown errors
        return ErrorSeverity.RECOVERABLE
    
    def _calculate_retry_delay(self, attempt: int, strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
                             base_delay: float = 1.0, max_delay: float = 60.0, jitter: bool = True) -> float:
        """
        Calculate delay before next retry attempt
        
        Args:
            attempt: Current attempt number (1-based)
            strategy: Retry strategy to use
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            jitter: Whether to add random jitter to prevent thundering herd
            
        Returns:
            Delay in seconds before next attempt
        """
        if strategy == RetryStrategy.IMMEDIATE:
            delay = 0.0
        elif strategy == RetryStrategy.FIXED_DELAY:
            delay = base_delay
        elif strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = base_delay * attempt
        elif strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = base_delay * (2 ** (attempt - 1))
        else:
            delay = base_delay
        
        # Cap at maximum delay
        delay = min(delay, max_delay)
        
        # Add jitter to prevent thundering herd
        if jitter and delay > 0:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(0.0, delay)
    
    def _should_retry(self, error: Exception, attempt: int, max_attempts: int) -> bool:
        """
        Determine if an operation should be retried
        
        Args:
            error: Exception that occurred
            attempt: Current attempt number
            max_attempts: Maximum allowed attempts
            
        Returns:
            True if should retry, False otherwise
        """
        if attempt >= max_attempts:
            return False
        
        severity = self._classify_error(error)
        return severity in [ErrorSeverity.RECOVERABLE, ErrorSeverity.TEMPORARY]
    
    def _execute_with_retry(self, operation_func, layer_id: str, *args, 
                          max_attempts: int = 3, 
                          retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
                          base_delay: float = 1.0, **kwargs) -> DownloadResult:
        """
        Execute an operation with retry logic and error recovery
        
        Args:
            operation_func: Function to execute with retries
            layer_id: Layer ID for error reporting
            *args: Arguments for operation_func
            max_attempts: Maximum number of retry attempts
            retry_strategy: Strategy for calculating retry delays
            base_delay: Base delay between retries
            **kwargs: Keyword arguments for operation_func
            
        Returns:
            DownloadResult from successful execution or final error
        """
        last_error = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                self.logger.info(f"Executing operation for layer {layer_id} (attempt {attempt}/{max_attempts})")
                result = operation_func(*args, **kwargs)
                
                if attempt > 1:
                    self.logger.info(f"Operation succeeded on attempt {attempt} for layer {layer_id}")
                
                return result
                
            except Exception as error:
                last_error = error
                self.logger.warning(f"Attempt {attempt} failed for layer {layer_id}: {error}")
                
                if not self._should_retry(error, attempt, max_attempts):
                    self.logger.error(f"Error classified as non-retryable or max attempts reached for layer {layer_id}")
                    break
                
                if attempt < max_attempts:
                    delay = self._calculate_retry_delay(attempt, retry_strategy, base_delay)
                    if delay > 0:
                        self.logger.info(f"Waiting {delay:.2f} seconds before retry...")
                        time.sleep(delay)
        
        # All attempts failed
        severity = self._classify_error(last_error) if last_error else ErrorSeverity.PERMANENT
        error_msg = f"Operation failed after {max_attempts} attempts. Last error: {last_error}"
        
        return self._create_error_result(layer_id, error_msg)
    
    def _validate_file_integrity(self, file_path: str, expected_size: Optional[int] = None) -> bool:
        """
        Validate the integrity of a downloaded file
        
        Args:
            file_path: Path to file to validate
            expected_size: Expected file size in bytes (optional)
            
        Returns:
            True if file appears valid, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"File does not exist: {file_path}")
                return False
            
            file_size = os.path.getsize(file_path)
            
            # Check if file is empty
            if file_size == 0:
                self.logger.error(f"File is empty: {file_path}")
                return False
            
            # Check expected size if provided (allow 5% variance)
            if expected_size is not None:
                size_variance = abs(file_size - expected_size) / expected_size
                if size_variance > 0.05:  # 5% tolerance
                    self.logger.warning(f"File size variance {size_variance:.1%} for {file_path}")
                    return False
            
            # Try to read the first few bytes to ensure file is accessible
            with open(file_path, 'rb') as f:
                header = f.read(1024)  # Read first 1KB
                if not header:
                    self.logger.error(f"Cannot read file header: {file_path}")
                    return False
            
            self.logger.debug(f"File validation passed: {file_path} ({file_size} bytes)")
            return True
            
        except Exception as e:
            self.logger.error(f"File validation error for {file_path}: {e}")
            return False
    
    def _cleanup_partial_download(self, file_path: str) -> bool:
        """
        Clean up partially downloaded or corrupted files
        
        Args:
            file_path: Path to file to clean up
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.info(f"Cleaned up partial download: {file_path}")
                return True
            return True
        except Exception as e:
            self.logger.error(f"Failed to cleanup partial download {file_path}: {e}")
            return False
    
    def _recover_from_partial_download(self, file_path: str, download_func, *args, **kwargs) -> bool:
        """
        Attempt to recover from a partial download
        
        Args:
            file_path: Path to the partially downloaded file
            download_func: Function to re-attempt download
            *args: Arguments for download_func
            **kwargs: Keyword arguments for download_func
            
        Returns:
            True if recovery successful, False otherwise
        """
        try:
            self.logger.info(f"Attempting recovery from partial download: {file_path}")
            
            # Clean up partial file
            if not self._cleanup_partial_download(file_path):
                return False
            
            # Re-attempt download
            return download_func(*args, **kwargs)
            
        except Exception as e:
            self.logger.error(f"Recovery failed for {file_path}: {e}")
            return False
    
    def _handle_disk_space_error(self, output_path: str, required_space_mb: float = 100.0) -> bool:
        """
        Handle disk space errors by checking available space and suggesting cleanup
        
        Args:
            output_path: Output directory path
            required_space_mb: Required space in MB
            
        Returns:
            True if sufficient space is available, False otherwise
        """
        try:
            import shutil
            
            # Check available disk space
            total, used, free = shutil.disk_usage(output_path)
            free_mb = free / (1024 * 1024)
            
            self.logger.info(f"Disk space check: {free_mb:.1f} MB available, {required_space_mb:.1f} MB required")
            
            if free_mb < required_space_mb:
                self.logger.error(f"Insufficient disk space: {free_mb:.1f} MB available, {required_space_mb:.1f} MB required")
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Could not check disk space: {e}")
            return True  # Assume OK if we can't check
    
    def _create_recovery_metadata(self, layer_id: str, error: Exception, attempt: int) -> Dict[str, Any]:
        """
        Create metadata for recovery attempts
        
        Args:
            layer_id: Layer ID that failed
            error: Exception that occurred
            attempt: Attempt number
            
        Returns:
            Dictionary with recovery metadata
        """
        return {
            'layer_id': layer_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'attempt_number': attempt,
            'timestamp': time.time(),
            'recovery_strategy': self._classify_error(error).value
        }