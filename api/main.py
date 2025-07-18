"""
FastAPI application for the Multi-Source Geospatial Data Downloader
"""
import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import geopandas as gpd
from shapely.geometry import shape

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, BackgroundTasks, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.models import (
    JobRequest, JobResponse, JobStatusResponse, 
    DownloaderInfo, LayerInfo, PreviewRequest, PreviewResponse,
    ErrorResponse, AOIBounds, APIInfoResponse, DownloadersResponse, LayersResponse,
    GPTDataResponse, DataPreviewResponse, DataSummary, DownloadLinks, UnifiedDataResponse
)
from api.job_manager import job_manager, JobStatus
from downloaders import get_downloader, list_downloaders

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Multi-Source Geospatial Data Downloader API",
    description="""
    A REST API for downloading geospatial data from multiple federal and public data sources 
    within a user-defined Area of Interest (AOI).
    
    ## Features
    - **FEMA NFHL**: National Flood Hazard Layer data including flood zones and base flood elevations
    - **USGS LiDAR**: 3DEP digital elevation models with optional contour generation  
    - **NOAA Atlas 14**: Precipitation frequency data with automatic PDF report generation
    
    ## Usage
    1. Get available data sources: `GET /downloaders`
    2. Create a download job: `POST /jobs`
    3. Monitor job progress: `GET /jobs/{job_id}`
    4. Download results: `GET /jobs/{job_id}/result`
    """,
    version="1.0.0",
    contact={
        "name": "Multi-Source Geospatial Data Downloader",
        "url": "https://github.com/your-username/project_data_downloader"
    },
    servers=[
        {
            "url": "https://project-data-downloader.onrender.com",
            "description": "Production server"
        }
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (for any web interface)
if Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_model=APIInfoResponse)
async def root():
    """API root endpoint"""
    return APIInfoResponse(
        message="Multi-Source Geospatial Data Downloader API",
        version="1.0.0",
        docs="/docs",
        openapi="/openapi.json"
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is running"}


@app.get("/debug/job/{job_id}")
async def debug_job_files(job_id: str):
    """Debug endpoint to check job file status"""
    try:
        job_data = job_manager.get_job_status(job_id)
        if not job_data:
            return {"error": "Job not found"}
        
        zip_path = job_manager.get_result_file_path(job_id)
        job_dir = job_manager.results_dir / job_id
        
        debug_info = {
            "job_id": job_id,
            "job_status": job_data.get("status"),
            "zip_path": str(zip_path) if zip_path else None,
            "zip_exists": zip_path.exists() if zip_path else False,
            "zip_size": zip_path.stat().st_size if zip_path and zip_path.exists() else None,
            "job_dir": str(job_dir),
            "job_dir_exists": job_dir.exists(),
            "job_dir_contents": list(str(p) for p in job_dir.iterdir()) if job_dir.exists() else [],
            "results_dir": str(job_manager.results_dir),
            "results_dir_contents": list(str(p.name) for p in job_manager.results_dir.iterdir()),
            "progress": job_data.get("progress", {}),
            "results": job_data.get("results", [])
        }
        
        return debug_info
        
    except Exception as e:
        return {"error": str(e)}


@app.get("/downloaders", response_model=DownloadersResponse)
async def get_downloaders():
    """Get all available data source downloaders and their layers"""
    try:
        downloaders_info = job_manager.get_available_downloaders()
        
        # Convert to response format
        response_data = {}
        for downloader_id, info in downloaders_info.items():
            layers = {}
            for layer_id, layer_info in info["layers"].items():
                layers[layer_id] = LayerInfo(**layer_info)
            
            response_data[downloader_id] = DownloaderInfo(
                id=info["id"],
                name=info["name"],
                description=info["description"],
                layers=layers
            )
        
        # Create response with explicit fields
        return DownloadersResponse(
            fema=response_data.get("fema"),
            usgs_lidar=response_data.get("usgs_lidar"),
            noaa_atlas14=response_data.get("noaa_atlas14")
        )
        
    except Exception as e:
        logger.error(f"Error getting downloaders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/downloaders/{downloader_id}/layers", response_model=LayersResponse)
async def get_downloader_layers(downloader_id: str):
    """Get available layers for a specific downloader"""
    try:
        downloader_class = get_downloader(downloader_id)
        downloader = downloader_class()
        
        layers = {}
        for layer_id, layer_info in downloader.get_available_layers().items():
            layers[layer_id] = LayerInfo(
                id=layer_id,
                name=layer_info.name,
                description=layer_info.description,
                geometry_type=layer_info.geometry_type,
                data_type=layer_info.data_type
            )
        
        return LayersResponse(layers=layers)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting layers for {downloader_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs", response_model=JobResponse)
async def create_job(request: JobRequest, background_tasks: BackgroundTasks):
    """Create a new download job"""
    try:
        # Validate downloader exists
        try:
            get_downloader(request.downloader_id)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Unknown downloader: {request.downloader_id}"
            )
        
        # Validate AOI is provided
        if not request.aoi_bounds and not request.aoi_geometry:
            raise HTTPException(
                status_code=400,
                detail="Either aoi_bounds or aoi_geometry must be provided"
            )
        
        # Create job
        job_id = job_manager.create_job(request)
        
        # Start job in background
        background_tasks.add_task(job_manager.start_job, job_id)
        
        return JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="Job created and will start processing shortly"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the status of a download job"""
    job_data = job_manager.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Calculate result summary if completed
    result_summary = None
    if job_data["status"] == JobStatus.COMPLETED.value and job_data.get("results"):
        results = job_data["results"]
        successful = sum(1 for r in results if r.get("success", False))
        total_features = sum(r.get("feature_count", 0) for r in results if r.get("success", False))
        
        zip_path = job_manager.get_result_file_path(job_id)
        has_download = zip_path is not None and zip_path.exists()
        
        result_summary = {
            "total_layers": len(results),
            "successful_layers": successful,
            "failed_layers": len(results) - successful,
            "total_features": total_features,
            "success_rate": successful / len(results) if results else 0,
            "has_download": has_download,
            # Primary GPT endpoint (pure text/JSON data)
            "data_url": f"/jobs/{job_id}/data" if has_download else None,
            # Legacy endpoints (still available)
            "download_url": f"/jobs/{job_id}/result" if has_download else None,
            "download_info_url": f"/jobs/{job_id}/download-info" if has_download else None,
            "summary_url": f"/jobs/{job_id}/summary" if has_download else None,
            "preview_url": f"/jobs/{job_id}/preview" if has_download else None
        }
    
    return JobStatusResponse(
        job_id=job_data["job_id"],
        status=JobStatus(job_data["status"]),
        created_at=job_data["created_at"],
        started_at=job_data.get("started_at"),
        completed_at=job_data.get("completed_at"),
        progress=job_data.get("progress"),
        error_message=job_data.get("error_message"),
        result_summary=result_summary
    )


@app.get("/jobs/{job_id}/result")
async def download_job_result(job_id: str):
    """Download the ZIP file containing all job results"""
    try:
        logger.info(f"Download request for job {job_id}")
        
        job_data = job_manager.get_job_status(job_id)
        if not job_data:
            logger.warning(f"Job {job_id} not found")
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job_data["status"] != JobStatus.COMPLETED.value:
            logger.warning(f"Job {job_id} not completed, status: {job_data['status']}")
            raise HTTPException(
                status_code=400, 
                detail=f"Job is not completed. Current status: {job_data['status']}"
            )
        
        zip_path = job_manager.get_result_file_path(job_id)
        logger.info(f"Looking for result file at: {zip_path}")
        
        if not zip_path:
            logger.error(f"No result file path found for job {job_id}")
            raise HTTPException(status_code=404, detail="Result file path not found")
        
        if not zip_path.exists():
            logger.error(f"Result file does not exist: {zip_path}")
            raise HTTPException(status_code=404, detail=f"Result file not found at {zip_path}")
        
        # Check file size and permissions
        file_size = zip_path.stat().st_size
        logger.info(f"Serving file {zip_path} (size: {file_size} bytes)")
        
        if file_size == 0:
            logger.error(f"Result file is empty: {zip_path}")
            raise HTTPException(status_code=500, detail="Result file is empty")
        
        return FileResponse(
            path=str(zip_path),
            filename=f"geospatial_data_{job_id}.zip",
            media_type="application/zip",
            headers={
                "Content-Length": str(file_size),
                "Cache-Control": "no-cache"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error serving file for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error serving file: {str(e)}")


@app.get("/jobs/{job_id}/data", response_model=UnifiedDataResponse)
async def get_job_data_unified(job_id: str):
    """Get unified text-based data for GPT consumption - pure JSON response"""
    try:
        job_data = job_manager.get_job_status(job_id)
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job_data["status"] != JobStatus.COMPLETED.value:
            raise HTTPException(
                status_code=400, 
                detail=f"Job is not completed. Current status: {job_data['status']}"
            )
        
        # Get unified data (text-based only)
        unified_data = job_manager.get_unified_data(job_id)
        if not unified_data:
            raise HTTPException(status_code=404, detail="No processable data found for this job")
        
        # Create unified response
        response = UnifiedDataResponse(
            job_id=job_id,
            status="completed",
            data_type=unified_data["data_type"],
            metadata=unified_data["metadata"],
            location=unified_data["location"],
            usage_instructions=unified_data["usage_instructions"]
        )
        
        # Add data based on type
        if unified_data["data_type"] == "geospatial":
            response.geojson = unified_data["geojson"]
        elif unified_data["data_type"] == "precipitation":
            response.rainfall_data = unified_data["rainfall_data"]
        elif unified_data["data_type"] == "elevation":
            response.elevation_data = unified_data.get("elevation_data")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting unified data for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}/data-legacy", response_model=GPTDataResponse)
async def get_job_data_gpt_optimized(job_id: str, format: Optional[str] = None):
    """Get GPT-optimized data for a completed job"""
    try:
        job_data = job_manager.get_job_status(job_id)
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job_data["status"] != JobStatus.COMPLETED.value:
            raise HTTPException(
                status_code=400, 
                detail=f"Job is not completed. Current status: {job_data['status']}"
            )
        
        # Get GPT-optimized data
        gpt_data = job_manager.get_gpt_optimized_data(job_id)
        if not gpt_data:
            raise HTTPException(status_code=404, detail="No processable data found for this job")
        
        # Generate download links
        download_links = job_manager.generate_download_links(job_id)
        
        # Create response
        response = GPTDataResponse(
            job_id=job_id,
            status="completed",
            data_size=gpt_data["data_size"],
            response_type=gpt_data["response_type"],
            download_links=DownloadLinks(**download_links),
            instructions=gpt_data["instructions"],
            processing_info={
                "completed_at": job_data.get("completed_at"),
                "total_layers": len(job_data.get("results", [])),
                "successful_layers": sum(1 for r in job_data.get("results", []) if r.get("success"))
            }
        )
        
        # Add data based on response type
        if gpt_data["response_type"] == "geojson":
            response.geojson = gpt_data["geojson"]
        elif gpt_data["response_type"] == "summary":
            response.summary = DataSummary(
                feature_count=gpt_data["summary"]["feature_count"],
                bounds=AOIBounds(**gpt_data["summary"]["bounds"]),
                attribute_summary=gpt_data["summary"].get("attribute_summary"),
                data_quality=gpt_data["summary"].get("data_quality")
            )
            if "sample_geojson" in gpt_data:
                response.geojson = gpt_data["sample_geojson"]
        else:  # links_only
            response.summary = DataSummary(
                feature_count=gpt_data["summary"]["feature_count"],
                bounds=AOIBounds(**gpt_data["summary"]["bounds"]),
                attribute_summary=gpt_data["summary"].get("attribute_summary"),
                data_quality=gpt_data["summary"].get("data_quality")
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting GPT data for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}/summary", response_model=DataSummary)
async def get_job_summary(job_id: str):
    """Get data summary for a completed job (always returns summary, never full data)"""
    try:
        job_data = job_manager.get_job_status(job_id)
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job_data["status"] != JobStatus.COMPLETED.value:
            raise HTTPException(
                status_code=400, 
                detail=f"Job is not completed. Current status: {job_data['status']}"
            )
        
        # Get GPT-optimized data
        gpt_data = job_manager.get_gpt_optimized_data(job_id)
        if not gpt_data or "summary" not in gpt_data:
            raise HTTPException(status_code=404, detail="No summary data available for this job")
        
        summary_data = gpt_data["summary"]
        return DataSummary(
            feature_count=summary_data["feature_count"],
            bounds=AOIBounds(**summary_data["bounds"]),
            attribute_summary=summary_data.get("attribute_summary"),
            data_quality=summary_data.get("data_quality")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting summary for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}/preview", response_model=DataPreviewResponse)
async def get_job_preview(job_id: str, max_features: int = 50):
    """Get a preview of job data (small sample for any dataset size)"""
    try:
        job_data = job_manager.get_job_status(job_id)
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job_data["status"] != JobStatus.COMPLETED.value:
            raise HTTPException(
                status_code=400, 
                detail=f"Job is not completed. Current status: {job_data['status']}"
            )
        
        # Get GPT-optimized data
        gpt_data = job_manager.get_gpt_optimized_data(job_id)
        if not gpt_data:
            raise HTTPException(status_code=404, detail="No preview data available for this job")
        
        # Create preview from available data
        preview_geojson = None
        if gpt_data.get("geojson"):
            features = gpt_data["geojson"].get("features", [])
            preview_features = features[:max_features]
            preview_geojson = {
                "type": "FeatureCollection",
                "features": preview_features
            }
        elif gpt_data.get("sample_geojson"):
            features = gpt_data["sample_geojson"].get("features", [])
            preview_features = features[:max_features]
            preview_geojson = {
                "type": "FeatureCollection", 
                "features": preview_features
            }
        
        summary_data = gpt_data["summary"]
        download_links = job_manager.generate_download_links(job_id)
        
        return DataPreviewResponse(
            job_id=job_id,
            preview_type="sample",
            feature_count=len(preview_geojson["features"]) if preview_geojson else 0,
            total_features=summary_data["feature_count"],
            sample_geojson=preview_geojson,
            summary=DataSummary(
                feature_count=summary_data["feature_count"],
                bounds=AOIBounds(**summary_data["bounds"]),
                attribute_summary=summary_data.get("attribute_summary"),
                data_quality=summary_data.get("data_quality")
            ),
            download_links=DownloadLinks(**download_links)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preview for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}/download-info")
async def get_download_info(job_id: str):
    """Get download information for a completed job"""
    try:
        job_data = job_manager.get_job_status(job_id)
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job_data["status"] != JobStatus.COMPLETED.value:
            raise HTTPException(
                status_code=400, 
                detail=f"Job is not completed. Current status: {job_data['status']}"
            )
        
        zip_path = job_manager.get_result_file_path(job_id)
        if not zip_path or not zip_path.exists():
            raise HTTPException(status_code=404, detail="Result file not found")
        
        file_size = zip_path.stat().st_size
        
        return {
            "job_id": job_id,
            "download_url": f"/jobs/{job_id}/result",
            "filename": f"geospatial_data_{job_id}.zip",
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "status": "ready",
            "created_at": job_data.get("completed_at", job_data.get("created_at"))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting download info for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}/export/geojson")
async def export_geojson(job_id: str):
    """Export job results as GeoJSON file"""
    try:
        job_data = job_manager.get_job_status(job_id)
        if not job_data or job_data["status"] != JobStatus.COMPLETED.value:
            raise HTTPException(status_code=404, detail="Job not found or not completed")
        
        job_dir = job_manager.results_dir / job_id
        geojson_files = list(job_dir.glob("*.geojson"))
        
        if not geojson_files:
            # Try to convert shapefiles to GeoJSON
            shp_files = list(job_dir.glob("*.shp"))
            if shp_files:
                geojson_files = job_manager._convert_shapefiles_to_geojson(shp_files)
        
        if not geojson_files:
            raise HTTPException(status_code=404, detail="No GeoJSON data available")
        
        # If multiple files, combine them
        if len(geojson_files) == 1:
            return FileResponse(
                path=str(geojson_files[0]),
                filename=f"geospatial_data_{job_id}.geojson",
                media_type="application/geo+json"
            )
        else:
            # Combine multiple GeoJSON files
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False) as temp_file:
                combined_features = []
                for geojson_file in geojson_files:
                    with open(geojson_file, 'r') as f:
                        data = json.load(f)
                        if data.get("type") == "FeatureCollection":
                            combined_features.extend(data.get("features", []))
                
                combined_geojson = {
                    "type": "FeatureCollection",
                    "features": combined_features
                }
                json.dump(combined_geojson, temp_file, indent=2)
                temp_path = temp_file.name
            
            return FileResponse(
                path=temp_path,
                filename=f"geospatial_data_{job_id}.geojson",
                media_type="application/geo+json"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting GeoJSON for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}/export/shapefile")
async def export_shapefile(job_id: str):
    """Export job results as shapefile ZIP"""
    try:
        job_data = job_manager.get_job_status(job_id)
        if not job_data or job_data["status"] != JobStatus.COMPLETED.value:
            raise HTTPException(status_code=404, detail="Job not found or not completed")
        
        job_dir = job_manager.results_dir / job_id
        
        # Look for existing shapefiles
        shp_files = list(job_dir.glob("*.shp"))
        if shp_files:
            # Create ZIP with all shapefile components
            import tempfile
            import zipfile
            
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
                with zipfile.ZipFile(temp_zip.name, 'w') as zipf:
                    for shp_file in shp_files:
                        # Add shapefile and its components
                        base_name = shp_file.stem
                        for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
                            component_file = shp_file.parent / f"{base_name}{ext}"
                            if component_file.exists():
                                zipf.write(component_file, component_file.name)
                
                return FileResponse(
                    path=temp_zip.name,
                    filename=f"geospatial_data_{job_id}_shapefiles.zip",
                    media_type="application/zip"
                )
        else:
            # Try to convert GeoJSON to shapefile
            geojson_files = list(job_dir.glob("*.geojson"))
            if not geojson_files:
                raise HTTPException(status_code=404, detail="No shapefile data available")
            
            import tempfile
            import zipfile
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Convert GeoJSON to shapefile
                for i, geojson_file in enumerate(geojson_files):
                    try:
                        gdf = gpd.read_file(geojson_file)
                        if not gdf.empty:
                            shp_name = f"layer_{i}_{geojson_file.stem}.shp"
                            shp_path = temp_path / shp_name
                            gdf.to_file(shp_path, driver='ESRI Shapefile')
                    except Exception as e:
                        logger.warning(f"Error converting {geojson_file} to shapefile: {e}")
                
                # Create ZIP with all shapefiles
                zip_path = temp_path / "shapefiles.zip"
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for file_path in temp_path.rglob('*'):
                        if file_path.is_file() and file_path.name != "shapefiles.zip":
                            zipf.write(file_path, file_path.name)
                
                return FileResponse(
                    path=str(zip_path),
                    filename=f"geospatial_data_{job_id}_shapefiles.zip",
                    media_type="application/zip"
                )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting shapefile for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}/export/pdf")
async def export_pdf(job_id: str):
    """Export job PDF reports if available"""
    try:
        job_data = job_manager.get_job_status(job_id)
        if not job_data or job_data["status"] != JobStatus.COMPLETED.value:
            raise HTTPException(status_code=404, detail="Job not found or not completed")
        
        job_dir = job_manager.results_dir / job_id
        pdf_files = list(job_dir.glob("*.pdf"))
        
        if not pdf_files:
            raise HTTPException(status_code=404, detail="No PDF reports available for this job")
        
        if len(pdf_files) == 1:
            return FileResponse(
                path=str(pdf_files[0]),
                filename=f"report_{job_id}.pdf",
                media_type="application/pdf"
            )
        else:
            # Create ZIP with multiple PDFs
            import tempfile
            import zipfile
            
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
                with zipfile.ZipFile(temp_zip.name, 'w') as zipf:
                    for pdf_file in pdf_files:
                        zipf.write(pdf_file, pdf_file.name)
                
                return FileResponse(
                    path=temp_zip.name,
                    filename=f"reports_{job_id}.zip",
                    media_type="application/zip"
                )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting PDF for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/preview", response_model=PreviewResponse)
async def preview_layer(request: PreviewRequest):
    """Get a preview of layer data (synchronous, limited features)"""
    try:
        # Validate downloader
        try:
            downloader_class = get_downloader(request.downloader_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown downloader: {request.downloader_id}"
            )
        
        # Validate AOI
        if not request.aoi_bounds and not request.aoi_geometry:
            raise HTTPException(
                status_code=400,
                detail="Either aoi_bounds or aoi_geometry must be provided"
            )
        
        # Prepare AOI
        if request.aoi_bounds:
            bounds = request.aoi_bounds
            aoi_bounds = (bounds.minx, bounds.miny, bounds.maxx, bounds.maxy)
        else:
            aoi_geom = shape(request.aoi_geometry.dict())
            aoi_bounds = aoi_geom.bounds
        
        # Get downloader and download layer
        downloader = downloader_class()
        
        # Create temporary directory for preview
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            result = downloader.download_layer(
                layer_id=request.layer_id,
                aoi_bounds=aoi_bounds,
                output_path=temp_dir
            )
            
            if not result.success:
                raise HTTPException(
                    status_code=400,
                    detail=f"Preview failed: {result.error_message}"
                )
            
            # Load and limit features for preview
            if result.file_path and os.path.exists(result.file_path):
                try:
                    gdf = gpd.read_file(result.file_path)
                    
                    # Limit features for preview
                    if len(gdf) > request.max_features:
                        gdf = gdf.head(request.max_features)
                    
                    # Convert to GeoJSON
                    geojson = gdf.to_json()
                    import json
                    geojson_dict = json.loads(geojson)
                    
                    # Get bounds
                    bounds = gdf.total_bounds
                    preview_bounds = AOIBounds(
                        minx=float(bounds[0]),
                        miny=float(bounds[1]), 
                        maxx=float(bounds[2]),
                        maxy=float(bounds[3])
                    )
                    
                    return PreviewResponse(
                        layer_id=request.layer_id,
                        feature_count=len(gdf),
                        geojson=geojson_dict,
                        bounds=preview_bounds,
                        preview_note=f"Preview showing {len(gdf)} of {result.feature_count or 'unknown'} total features"
                    )
                    
                except Exception as e:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error processing preview data: {str(e)}"
                    )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="No data file generated for preview"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its results"""
    job_data = job_manager.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        # Delete job metadata file
        job_file = job_manager.jobs_dir / f"{job_id}.json"
        if job_file.exists():
            job_file.unlink()
        
        # Delete result files
        result_dir = job_manager.results_dir / job_id
        if result_dir.exists():
            import shutil
            shutil.rmtree(result_dir)
        
        zip_file = job_manager.get_result_file_path(job_id)
        if zip_file and zip_file.exists():
            zip_file.unlink()
        
        return {"message": f"Job {job_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/cleanup")
async def cleanup_old_jobs(max_age_days: int = 7):
    """Admin endpoint to clean up old jobs and results"""
    try:
        job_manager.cleanup_old_jobs(max_age_days)
        return {"message": f"Cleaned up jobs older than {max_age_days} days"}
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(error="Not Found", detail=str(exc.detail)).dict()
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Internal Server Error", detail="An unexpected error occurred").dict()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 