"""
Download utility functions for HTTP handling, retry logic, and response processing.
"""
import os
import time
import zipfile
import tempfile
from typing import Optional, Dict, Any, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

logger = logging.getLogger(__name__)


class DownloadSession:
    """Configured requests session with retry logic and timeouts"""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.0, 
                 timeout: int = 60):
        """
        Initialize download session with retry configuration
        
        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Factor for exponential backoff
            timeout: Request timeout in seconds
        """
        self.session = requests.Session()
        self.timeout = timeout
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        
        # Mount adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'User-Agent': 'Multi-Source Geospatial Data Downloader/1.0'
        })
    
    def get(self, url: str, params: Dict[str, Any] = None, **kwargs) -> Optional[requests.Response]:
        """
        Perform GET request with retry logic
        
        Args:
            url: Request URL
            params: Query parameters
            **kwargs: Additional requests parameters
            
        Returns:
            Response object or None if failed
        """
        try:
            kwargs.setdefault('timeout', self.timeout)
            response = self.session.get(url, params=params, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"GET request failed for {url}: {e}")
            return None
    
    def post(self, url: str, data: Dict[str, Any] = None, **kwargs) -> Optional[requests.Response]:
        """
        Perform POST request with retry logic
        
        Args:
            url: Request URL
            data: POST data
            **kwargs: Additional requests parameters
            
        Returns:
            Response object or None if failed
        """
        try:
            kwargs.setdefault('timeout', self.timeout)
            response = self.session.post(url, data=data, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"POST request failed for {url}: {e}")
            return None
    
    def download_file(self, url: str, output_path: str, params: Dict[str, Any] = None, 
                     chunk_size: int = 8192) -> bool:
        """
        Download file with progress tracking
        
        Args:
            url: Download URL
            output_path: Local file path for download
            params: Query parameters
            chunk_size: Download chunk size in bytes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create output directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            response = self.session.get(url, params=params, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progress for large files
                        if total_size > 0 and downloaded % (chunk_size * 100) == 0:
                            progress = (downloaded / total_size) * 100
                            logger.debug(f"Download progress: {progress:.1f}%")
            
            logger.info(f"Downloaded file: {output_path} ({downloaded:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"File download failed for {url}: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)  # Clean up partial download
            return False


def extract_zip_response(response: requests.Response, 
                        extract_to: str = None) -> Optional[str]:
    """
    Extract ZIP file from HTTP response
    
    Args:
        response: HTTP response containing ZIP data
        extract_to: Directory to extract to (default: temp directory)
        
    Returns:
        Path to extraction directory or None if failed
    """
    try:
        if extract_to is None:
            extract_to = tempfile.mkdtemp()
        else:
            os.makedirs(extract_to, exist_ok=True)
        
        # Extract the zip file
        with zipfile.ZipFile(response.content) as zip_ref:
            zip_ref.extractall(extract_to)
        
        logger.info(f"Extracted ZIP to: {extract_to}")
        return extract_to
        
    except zipfile.BadZipFile:
        logger.error("Response does not contain valid ZIP data")
        return None
    except Exception as e:
        logger.error(f"Error extracting ZIP: {e}")
        return None


def find_files_by_extension(directory: str, extension: str) -> list:
    """
    Find all files with specific extension in directory
    
    Args:
        directory: Directory to search
        extension: File extension (e.g., '.shp', '.tif')
        
    Returns:
        List of file paths
    """
    files = []
    for root, dirs, filenames in os.walk(directory):
        for filename in filenames:
            if filename.lower().endswith(extension.lower()):
                files.append(os.path.join(root, filename))
    return files


def validate_response_content(response: requests.Response, 
                            expected_types: list = None) -> bool:
    """
    Validate response content type and size
    
    Args:
        response: HTTP response to validate
        expected_types: List of expected content types
        
    Returns:
        True if valid, False otherwise
    """
    if response is None:
        return False
    
    # Check status code
    if response.status_code != 200:
        logger.warning(f"Unexpected status code: {response.status_code}")
        return False
    
    # Check content length
    if len(response.content) == 0:
        logger.warning("Response contains no data")
        return False
    
    # Check content type if specified
    if expected_types:
        content_type = response.headers.get('content-type', '').lower()
        if not any(expected_type.lower() in content_type for expected_type in expected_types):
            logger.warning(f"Unexpected content type: {content_type}")
            return False
    
    return True


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in MB
    """
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except OSError:
        return 0.0


def clean_temp_files(temp_dir: str) -> None:
    """
    Clean up temporary files and directories
    
    Args:
        temp_dir: Temporary directory to clean
    """
    try:
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")


def estimate_download_time(file_size_mb: float, 
                          connection_speed_mbps: float = 10.0) -> float:
    """
    Estimate download time for a file
    
    Args:
        file_size_mb: File size in megabytes
        connection_speed_mbps: Connection speed in Mbps
        
    Returns:
        Estimated download time in seconds
    """
    # Convert Mbps to MB/s (divide by 8)
    speed_mbs = connection_speed_mbps / 8
    
    # Add overhead factor
    overhead_factor = 1.2
    
    return (file_size_mb / speed_mbs) * overhead_factor 