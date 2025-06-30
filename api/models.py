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