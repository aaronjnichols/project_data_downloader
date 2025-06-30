"""
Pydantic models for API request and response schemas
"""
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"


class LayerInfo(BaseModel):
    id: str
    name: str
    description: str
    geometry_type: str
    data_type: str


class DownloaderInfo(BaseModel):
    id: str
    name: str
    description: str
    layers: Dict[str, LayerInfo]


class AOIBounds(BaseModel):
    minx: float = Field(..., description="Minimum longitude (west)")
    miny: float = Field(..., description="Minimum latitude (south)")
    maxx: float = Field(..., description="Maximum longitude (east)")
    maxy: float = Field(..., description="Maximum latitude (north)")


class AOIGeometry(BaseModel):
    type: str = Field(..., description="GeoJSON geometry type")
    coordinates: List[Any] = Field(..., description="GeoJSON coordinates")


class JobRequest(BaseModel):
    downloader_id: str = Field(..., description="ID of the downloader to use")
    layer_ids: List[str] = Field(..., description="List of layer IDs to download")
    aoi_bounds: Optional[AOIBounds] = Field(None, description="Bounding box AOI")
    aoi_geometry: Optional[AOIGeometry] = Field(None, description="GeoJSON geometry AOI")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional configuration")

    class Config:
        json_schema_extra = {
            "example": {
                "downloader_id": "fema",
                "layer_ids": ["28", "16"],
                "aoi_bounds": {
                    "minx": -105.3,
                    "miny": 39.9,
                    "maxx": -105.1,
                    "maxy": 40.1
                },
                "config": {
                    "timeout": 60
                }
            }
        }


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str = "Job created successfully"


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None


class DownloadResult(BaseModel):
    success: bool
    layer_id: str
    feature_count: Optional[int] = None
    file_path: Optional[str] = None
    file_size_mb: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    download_results: List[DownloadResult]
    total_features: int
    total_files: int
    success_rate: float
    download_url: Optional[str] = None


class PreviewRequest(BaseModel):
    downloader_id: str
    layer_id: str
    aoi_bounds: Optional[AOIBounds] = None
    aoi_geometry: Optional[AOIGeometry] = None
    max_features: int = Field(default=100, description="Maximum features to return")


class PreviewResponse(BaseModel):
    layer_id: str
    feature_count: int
    geojson: Dict[str, Any]
    bounds: AOIBounds
    preview_note: str = "This is a preview with limited features"


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    job_id: Optional[str] = None


class APIInfoResponse(BaseModel):
    """Response model for the root API endpoint"""
    message: str
    version: str
    docs: str
    openapi: str


class DownloadersResponse(BaseModel):
    """Response model for the /downloaders endpoint"""
    fema: Optional[DownloaderInfo] = None
    usgs_lidar: Optional[DownloaderInfo] = None
    noaa_atlas14: Optional[DownloaderInfo] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "fema": {
                    "id": "fema",
                    "name": "FEMA NFHL",
                    "description": "National Flood Hazard Layer data",
                    "layers": {
                        "28": {
                            "id": "28",
                            "name": "Flood Hazard Areas",
                            "description": "Special Flood Hazard Areas",
                            "geometry_type": "polygon",
                            "data_type": "vector"
                        }
                    }
                }
            }
        }


class LayersResponse(BaseModel):
    """Response model for the /downloaders/{id}/layers endpoint"""
    layers: Dict[str, LayerInfo]
    
    class Config:
        json_schema_extra = {
            "example": {
                "layers": {
                    "28": {
                        "id": "28",
                        "name": "Flood Hazard Areas",
                        "description": "Special Flood Hazard Areas",
                        "geometry_type": "polygon",
                        "data_type": "vector"
                    }
                }
            }
        }


class DataSummary(BaseModel):
    """Summary statistics for a dataset"""
    feature_count: int
    total_area_sq_km: Optional[float] = None
    bounds: AOIBounds
    attribute_summary: Optional[Dict[str, Any]] = None
    data_quality: Optional[Dict[str, Any]] = None


class DownloadLinks(BaseModel):
    """Download links for different data formats"""
    geojson: Optional[str] = None
    shapefile: Optional[str] = None
    pdf: Optional[str] = None
    original_zip: Optional[str] = None
    expires_at: Optional[str] = None


class GPTDataResponse(BaseModel):
    """GPT-optimized data response"""
    job_id: str
    status: str
    data_size: str  # "small", "medium", "large"
    response_type: str  # "geojson", "summary", "links_only"
    
    # For small datasets - include GeoJSON directly
    geojson: Optional[Dict[str, Any]] = None
    
    # For large datasets - provide summary
    summary: Optional[DataSummary] = None
    
    # Always provide download links
    download_links: DownloadLinks
    
    # Instructions for GPT on how to use the data
    instructions: str
    
    # Metadata
    processing_info: Optional[Dict[str, Any]] = None


class DataPreviewResponse(BaseModel):
    """Response for data preview requests"""
    job_id: str
    preview_type: str  # "sample", "summary", "bounds_only"
    feature_count: int
    total_features: int
    sample_geojson: Optional[Dict[str, Any]] = None
    summary: DataSummary
    download_links: DownloadLinks 