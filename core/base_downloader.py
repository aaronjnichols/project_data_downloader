"""
Abstract base class for all data source downloaders.
Defines the standard interface that all downloader plugins must implement.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import geopandas as gpd


@dataclass
class LayerInfo:
    """Information about a data layer/dataset"""
    id: str
    name: str
    description: str
    geometry_type: str  # Point, Polyline, Polygon, Raster
    data_type: str      # Vector, Raster, PointCloud
    attributes: List[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class DownloadResult:
    """Result of a layer download operation"""
    success: bool
    layer_id: str
    feature_count: int = 0
    file_path: str = None
    error_message: str = None
    metadata: Dict[str, Any] = None


class BaseDownloader(ABC):
    """Abstract base class for all data source downloaders"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the downloader with configuration
        
        Args:
            config: Dictionary containing downloader-specific configuration
        """
        self.config = config or {}
        self.name = self.__class__.__name__
    
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