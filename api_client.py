"""
API Client for Geospatial Data Downloader
=========================================

This module provides a client class for interacting with the FastAPI backend
of the geospatial data downloader system.

Features:
- Full API endpoint coverage
- Error handling and retry logic
- Type hints and documentation
- Session management
- Response validation
"""

import requests
import json
import time
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import logging

# Configure logging
logger = logging.getLogger(__name__)

class APIClientError(Exception):
    """Custom exception for API client errors"""
    pass

class GeospatialAPIClient:
    """
    Client for interacting with the Geospatial Data Downloader API
    
    This client provides a comprehensive interface to all API endpoints
    with proper error handling, retries, and response validation.
    """
    
    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize the API client
        
        Args:
            base_url: Base URL of the API (e.g., 'http://localhost:8000')
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retries: int = 3
    ) -> Dict[str, Any]:
        """
        Make HTTP request with error handling and retries
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            retries: Number of retry attempts
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIClientError: If request fails after retries
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(retries + 1):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, params=params, timeout=self.timeout)
                elif method.upper() == 'POST':
                    response = self.session.post(url, json=data, params=params, timeout=self.timeout)
                elif method.upper() == 'DELETE':
                    response = self.session.delete(url, timeout=self.timeout)
                else:
                    raise APIClientError(f"Unsupported HTTP method: {method}")
                
                # Check response status
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise APIClientError(f"Endpoint not found: {endpoint}")
                elif response.status_code >= 400:
                    error_detail = "Unknown error"
                    try:
                        error_data = response.json()
                        error_detail = error_data.get('detail', str(error_data))
                    except:
                        error_detail = response.text or f"HTTP {response.status_code}"
                    
                    raise APIClientError(f"API error ({response.status_code}): {error_detail}")
                    
            except requests.exceptions.ConnectionError:
                if attempt < retries:
                    logger.warning(f"Connection failed, retrying in {2**attempt} seconds...")
                    time.sleep(2**attempt)
                    continue
                raise APIClientError(f"Failed to connect to API at {self.base_url}")
                
            except requests.exceptions.Timeout:
                if attempt < retries:
                    logger.warning(f"Request timeout, retrying in {2**attempt} seconds...")
                    time.sleep(2**attempt)
                    continue
                raise APIClientError(f"Request timeout after {self.timeout} seconds")
                
            except APIClientError:
                raise
                
            except Exception as e:
                if attempt < retries:
                    logger.warning(f"Request failed: {e}, retrying...")
                    time.sleep(2**attempt)
                    continue
                raise APIClientError(f"Unexpected error: {str(e)}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check API health status
        
        Returns:
            Health status information
        """
        return self._make_request('GET', '/health')
    
    def get_api_info(self) -> Dict[str, Any]:
        """
        Get API information and metadata
        
        Returns:
            API information including version and endpoints
        """
        return self._make_request('GET', '/')
    
    def get_downloaders(self) -> Dict[str, Any]:
        """
        Get all available data source downloaders and their layers
        
        Returns:
            Dictionary of available downloaders with their layer information
        """
        response = self._make_request('GET', '/downloaders')
        
        # Convert to a more usable format
        downloaders = {}
        for field in ['fema', 'usgs_lidar', 'noaa_atlas14']:
            if hasattr(response, field) and getattr(response, field):
                downloaders[field] = getattr(response, field)
            elif field in response and response[field]:
                downloaders[field] = response[field]
        
        return downloaders
    
    def get_downloader_layers(self, downloader_id: str) -> Dict[str, Any]:
        """
        Get available layers for a specific downloader
        
        Args:
            downloader_id: ID of the downloader (e.g., 'fema', 'usgs_lidar', 'noaa_atlas14')
            
        Returns:
            Dictionary of available layers for the specified downloader
        """
        return self._make_request('GET', f'/downloaders/{downloader_id}/layers')
    
    def create_job(self, job_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new download job
        
        Args:
            job_request: Job request data including:
                - downloader_id: ID of the downloader
                - layer_ids: List of layer IDs to download
                - aoi_bounds: Bounding box (optional)
                - aoi_geometry: GeoJSON geometry (optional)
                - config: Additional configuration (optional)
                
        Returns:
            Job creation response with job_id and status
        """
        return self._make_request('POST', '/jobs', data=job_request)
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get the status of a download job
        
        Args:
            job_id: ID of the job to check
            
        Returns:
            Job status information including progress and results
        """
        return self._make_request('GET', f'/jobs/{job_id}')
    
    def delete_job(self, job_id: str) -> Dict[str, Any]:
        """
        Delete a job and its results
        
        Args:
            job_id: ID of the job to delete
            
        Returns:
            Deletion confirmation message
        """
        return self._make_request('DELETE', f'/jobs/{job_id}')
    
    def get_job_data(self, job_id: str) -> Dict[str, Any]:
        """
        Get unified text-based data for a completed job
        
        Args:
            job_id: ID of the completed job
            
        Returns:
            Unified data response optimized for processing
        """
        return self._make_request('GET', f'/jobs/{job_id}/data')
    
    def get_job_preview(self, job_id: str, max_features: int = 50) -> Dict[str, Any]:
        """
        Get a preview of job data (small sample)
        
        Args:
            job_id: ID of the completed job
            max_features: Maximum number of features to include in preview
            
        Returns:
            Data preview with sample features and summary
        """
        params = {'max_features': max_features}
        return self._make_request('GET', f'/jobs/{job_id}/preview', params=params)
    
    def get_job_summary(self, job_id: str) -> Dict[str, Any]:
        """
        Get data summary for a completed job
        
        Args:
            job_id: ID of the completed job
            
        Returns:
            Data summary with statistics and metadata
        """
        return self._make_request('GET', f'/jobs/{job_id}/summary')
    
    def get_download_info(self, job_id: str) -> Dict[str, Any]:
        """
        Get download information for a completed job
        
        Args:
            job_id: ID of the completed job
            
        Returns:
            Download information including file size and URL
        """
        return self._make_request('GET', f'/jobs/{job_id}/download-info')
    
    def download_job_result(self, job_id: str, output_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Download the ZIP file containing all job results
        
        Args:
            job_id: ID of the completed job
            output_path: Optional path to save the file (defaults to current directory)
            
        Returns:
            Path to the downloaded file
            
        Raises:
            APIClientError: If download fails
        """
        url = f"{self.base_url}/jobs/{job_id}/result"
        
        try:
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # Determine output filename
            if output_path:
                output_path = Path(output_path)
                if output_path.is_dir():
                    filename = f"geospatial_data_{job_id}.zip"
                    output_path = output_path / filename
            else:
                output_path = Path(f"geospatial_data_{job_id}.zip")
            
            # Download file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return output_path
            
        except requests.exceptions.RequestException as e:
            raise APIClientError(f"Failed to download file: {str(e)}")
    
    def export_geojson(self, job_id: str, output_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Export job results as GeoJSON file
        
        Args:
            job_id: ID of the completed job
            output_path: Optional path to save the file
            
        Returns:
            Path to the exported GeoJSON file
        """
        url = f"{self.base_url}/jobs/{job_id}/export/geojson"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Determine output filename
            if output_path:
                output_path = Path(output_path)
                if output_path.is_dir():
                    filename = f"geospatial_data_{job_id}.geojson"
                    output_path = output_path / filename
            else:
                output_path = Path(f"geospatial_data_{job_id}.geojson")
            
            # Save file
            with open(output_path, 'w') as f:
                f.write(response.text)
            
            return output_path
            
        except requests.exceptions.RequestException as e:
            raise APIClientError(f"Failed to export GeoJSON: {str(e)}")
    
    def export_shapefile(self, job_id: str, output_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Export job results as shapefile ZIP
        
        Args:
            job_id: ID of the completed job
            output_path: Optional path to save the file
            
        Returns:
            Path to the exported shapefile ZIP
        """
        url = f"{self.base_url}/jobs/{job_id}/export/shapefile"
        
        try:
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # Determine output filename
            if output_path:
                output_path = Path(output_path)
                if output_path.is_dir():
                    filename = f"geospatial_data_{job_id}_shapefiles.zip"
                    output_path = output_path / filename
            else:
                output_path = Path(f"geospatial_data_{job_id}_shapefiles.zip")
            
            # Download file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return output_path
            
        except requests.exceptions.RequestException as e:
            raise APIClientError(f"Failed to export shapefile: {str(e)}")
    
    def export_pdf(self, job_id: str, output_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Export job PDF reports if available
        
        Args:
            job_id: ID of the completed job
            output_path: Optional path to save the file
            
        Returns:
            Path to the exported PDF file(s)
        """
        url = f"{self.base_url}/jobs/{job_id}/export/pdf"
        
        try:
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # Determine output filename
            if output_path:
                output_path = Path(output_path)
                if output_path.is_dir():
                    if 'zip' in response.headers.get('content-type', ''):
                        filename = f"reports_{job_id}.zip"
                    else:
                        filename = f"report_{job_id}.pdf"
                    output_path = output_path / filename
            else:
                if 'zip' in response.headers.get('content-type', ''):
                    output_path = Path(f"reports_{job_id}.zip")
                else:
                    output_path = Path(f"report_{job_id}.pdf")
            
            # Download file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return output_path
            
        except requests.exceptions.RequestException as e:
            raise APIClientError(f"Failed to export PDF: {str(e)}")
    
    def preview_layer(
        self, 
        downloader_id: str, 
        layer_id: str,
        aoi_bounds: Optional[Dict[str, float]] = None,
        aoi_geometry: Optional[Dict[str, Any]] = None,
        max_features: int = 100
    ) -> Dict[str, Any]:
        """
        Get a preview of layer data (synchronous, limited features)
        
        Args:
            downloader_id: ID of the downloader
            layer_id: ID of the layer
            aoi_bounds: Bounding box AOI (optional)
            aoi_geometry: GeoJSON geometry AOI (optional)
            max_features: Maximum features to return
            
        Returns:
            Preview data with limited features
        """
        request_data = {
            'downloader_id': downloader_id,
            'layer_id': layer_id,
            'max_features': max_features
        }
        
        if aoi_bounds:
            request_data['aoi_bounds'] = aoi_bounds
        elif aoi_geometry:
            request_data['aoi_geometry'] = aoi_geometry
        
        return self._make_request('POST', '/preview', data=request_data)
    
    def cleanup_old_jobs(self, max_age_days: int = 7) -> Dict[str, Any]:
        """
        Admin endpoint to clean up old jobs and results
        
        Args:
            max_age_days: Maximum age of jobs to keep (in days)
            
        Returns:
            Cleanup confirmation message
        """
        params = {'max_age_days': max_age_days}
        return self._make_request('POST', '/admin/cleanup', params=params)
    
    def debug_job_files(self, job_id: str) -> Dict[str, Any]:
        """
        Debug endpoint to check job file status
        
        Args:
            job_id: ID of the job to debug
            
        Returns:
            Debug information about job files and status
        """
        return self._make_request('GET', f'/debug/job/{job_id}')
    
    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Convenience functions for common operations
def create_simple_client(base_url: str = "http://localhost:8000") -> GeospatialAPIClient:
    """
    Create a simple API client with default settings
    
    Args:
        base_url: Base URL of the API
        
    Returns:
        Configured API client
    """
    return GeospatialAPIClient(base_url)

def wait_for_job_completion(
    client: GeospatialAPIClient, 
    job_id: str, 
    max_wait_time: int = 300,
    poll_interval: int = 2
) -> Dict[str, Any]:
    """
    Wait for a job to complete and return the final status
    
    Args:
        client: API client instance
        job_id: ID of the job to monitor
        max_wait_time: Maximum time to wait in seconds
        poll_interval: How often to check status in seconds
        
    Returns:
        Final job status
        
    Raises:
        APIClientError: If job fails or times out
    """
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        status = client.get_job_status(job_id)
        
        if status['status'] in ['completed', 'failed']:
            return status
        
        time.sleep(poll_interval)
    
    raise APIClientError(f"Job {job_id} did not complete within {max_wait_time} seconds")


# Example usage
if __name__ == "__main__":
    # Example of using the API client
    client = create_simple_client("http://localhost:8000")
    
    try:
        # Check API health
        health = client.health_check()
        print(f"API Status: {health}")
        
        # Get available downloaders
        downloaders = client.get_downloaders()
        print(f"Available downloaders: {list(downloaders.keys())}")
        
        # Example job creation
        job_request = {
            "downloader_id": "fema",
            "layer_ids": ["28"],
            "aoi_bounds": {
                "minx": -105.3,
                "miny": 39.9,
                "maxx": -105.1,
                "maxy": 40.1
            }
        }
        
        job_response = client.create_job(job_request)
        job_id = job_response['job_id']
        print(f"Created job: {job_id}")
        
        # Wait for completion
        final_status = wait_for_job_completion(client, job_id)
        print(f"Job completed with status: {final_status['status']}")
        
    except APIClientError as e:
        print(f"API Error: {e}")
    finally:
        client.close()