"""
Job manager for handling background download tasks and job persistence
"""
import os
import json
import uuid
import zipfile
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
import numpy as np
import geopandas as gpd
from shapely.geometry import shape, box

from api.models import JobStatus, JobRequest, DownloadResult as APIDownloadResult
from core.base_downloader import DownloadResult
from downloaders import get_downloader, list_downloaders

logger = logging.getLogger(__name__)


class JobManager:
    """Manages download jobs and their lifecycle"""
    
    def __init__(self, jobs_dir: str = "output/jobs", results_dir: str = "output/results"):
        self.jobs_dir = Path(jobs_dir)
        self.results_dir = Path(results_dir)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory job tracking
        self._active_jobs: Dict[str, asyncio.Task] = {}
        
    def create_job(self, request: JobRequest) -> str:
        """Create a new download job"""
        job_id = str(uuid.uuid4())
        
        job_data = {
            "job_id": job_id,
            "status": JobStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
            "request": request.dict(),
            "progress": {},
            "results": []
        }
        
        # Save job metadata
        job_file = self.jobs_dir / f"{job_id}.json"
        with open(job_file, 'w') as f:
            json.dump(job_data, f, indent=2)
        
        logger.info(f"Created job {job_id}")
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get current job status"""
        job_file = self.jobs_dir / f"{job_id}.json"
        if not job_file.exists():
            return None
            
        with open(job_file, 'r') as f:
            return json.load(f)
    
    def update_job_status(self, job_id: str, status: JobStatus, 
                         error_message: str = None, progress: Dict = None,
                         results: List = None):
        """Update job status"""
        job_data = self.get_job_status(job_id)
        if not job_data:
            return
        
        job_data["status"] = status.value
        job_data["updated_at"] = datetime.utcnow().isoformat()
        
        if status == JobStatus.RUNNING and "started_at" not in job_data:
            job_data["started_at"] = datetime.utcnow().isoformat()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            job_data["completed_at"] = datetime.utcnow().isoformat()
        
        if error_message:
            job_data["error_message"] = error_message
        if progress:
            job_data["progress"] = progress
        if results:
            job_data["results"] = results
        
        job_file = self.jobs_dir / f"{job_id}.json"
        with open(job_file, 'w') as f:
            json.dump(job_data, f, indent=2)
    
    async def start_job(self, job_id: str):
        """Start processing a job in the background"""
        if job_id in self._active_jobs:
            logger.warning(f"Job {job_id} is already running")
            return
        
        task = asyncio.create_task(self._process_job(job_id))
        self._active_jobs[job_id] = task
        
        # Clean up completed task
        task.add_done_callback(lambda t: self._active_jobs.pop(job_id, None))
    
    async def _process_job(self, job_id: str):
        """Process a download job"""
        try:
            logger.info(f"Starting job {job_id}")
            self.update_job_status(job_id, JobStatus.RUNNING)
            
            job_data = self.get_job_status(job_id)
            request_data = job_data["request"]
            request = JobRequest(**request_data)
            
            # Create job output directory
            job_output_dir = self.results_dir / job_id
            job_output_dir.mkdir(exist_ok=True)
            
            # Get downloader
            downloader_class = get_downloader(request.downloader_id)
            downloader = downloader_class(request.config)
            
            # Prepare AOI
            aoi_bounds, aoi_gdf = self._prepare_aoi(request)
            
            # Download each layer
            results = []
            total_layers = len(request.layer_ids)
            
            for i, layer_id in enumerate(request.layer_ids):
                logger.info(f"Processing layer {layer_id} ({i+1}/{total_layers})")
                
                # Update progress
                progress = {
                    "current_layer": layer_id,
                    "completed_layers": i,
                    "total_layers": total_layers,
                    "percent_complete": (i / total_layers) * 100
                }
                self.update_job_status(job_id, JobStatus.RUNNING, progress=progress)
                
                # Download layer
                result = downloader.download_layer(
                    layer_id=layer_id,
                    aoi_bounds=aoi_bounds,
                    output_path=str(job_output_dir),
                    aoi_gdf=aoi_gdf
                )
                
                # Convert to API result format
                api_result = self._convert_download_result(result)
                results.append(api_result.dict())
                
                logger.info(f"Layer {layer_id} {'succeeded' if result.success else 'failed'}")
            
            # Create result ZIP file
            zip_path = await self._create_result_zip(job_id, job_output_dir)
            
            # Final progress update
            final_progress = {
                "completed_layers": total_layers,
                "total_layers": total_layers,
                "percent_complete": 100,
                "zip_file": str(zip_path) if zip_path else None
            }
            
            self.update_job_status(
                job_id, 
                JobStatus.COMPLETED, 
                progress=final_progress,
                results=results
            )
            
            logger.info(f"Job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {str(e)}")
            self.update_job_status(
                job_id, 
                JobStatus.FAILED, 
                error_message=str(e)
            )
    
    def _prepare_aoi(self, request: JobRequest) -> Tuple[Tuple[float, float, float, float], gpd.GeoDataFrame]:
        """Prepare AOI from request"""
        if request.aoi_bounds:
            bounds = request.aoi_bounds
            aoi_bounds = (bounds.minx, bounds.miny, bounds.maxx, bounds.maxy)
            aoi_geom = box(bounds.minx, bounds.miny, bounds.maxx, bounds.maxy)
        elif request.aoi_geometry:
            aoi_geom = shape(request.aoi_geometry.dict())
            aoi_bounds = aoi_geom.bounds
        else:
            raise ValueError("Either aoi_bounds or aoi_geometry must be provided")
        
        # Create GeoDataFrame
        aoi_gdf = gpd.GeoDataFrame([1], geometry=[aoi_geom], crs='EPSG:4326')
        
        return aoi_bounds, aoi_gdf
    
    def _convert_download_result(self, result: DownloadResult) -> APIDownloadResult:
        """Convert core DownloadResult to API DownloadResult"""
        file_size_mb = None
        if result.file_path and os.path.exists(result.file_path):
            file_size_mb = os.path.getsize(result.file_path) / (1024 * 1024)
        
        return APIDownloadResult(
            success=result.success,
            layer_id=result.layer_id,
            feature_count=result.feature_count,
            file_path=result.file_path,
            file_size_mb=file_size_mb,
            error_message=result.error_message,
            metadata=result.metadata
        )
    
    async def _create_result_zip(self, job_id: str, job_output_dir: Path) -> Optional[Path]:
        """Create a ZIP file containing all job results"""
        try:
            zip_path = self.results_dir / f"{job_id}_results.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in job_output_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(job_output_dir)
                        zipf.write(file_path, arcname)
            
            return zip_path if zip_path.exists() else None
            
        except Exception as e:
            logger.error(f"Failed to create ZIP for job {job_id}: {e}")
            return None
    
    def get_available_downloaders(self) -> Dict[str, Dict]:
        """Get information about all available downloaders"""
        downloaders = {}
        
        for name, downloader_class in list_downloaders().items():
            try:
                downloader = downloader_class()
                layers = {}
                
                for layer_id, layer_info in downloader.get_available_layers().items():
                    layers[layer_id] = {
                        "id": layer_id,
                        "name": layer_info.name,
                        "description": layer_info.description,
                        "geometry_type": layer_info.geometry_type,
                        "data_type": layer_info.data_type
                    }
                
                downloaders[name] = {
                    "id": name,
                    "name": downloader.source_name,
                    "description": downloader.source_description,
                    "layers": layers
                }
                
            except Exception as e:
                logger.error(f"Error getting info for downloader {name}: {e}")
        
        return downloaders
    
    def get_result_file_path(self, job_id: str) -> Optional[Path]:
        """Get the path to the result ZIP file for a job"""
        zip_path = self.results_dir / f"{job_id}_results.zip"
        return zip_path if zip_path.exists() else None
    
    def get_gpt_optimized_data(self, job_id: str) -> Optional[Dict]:
        """Get GPT-optimized data for a completed job"""
        job_data = self.get_job_status(job_id)
        if not job_data or job_data["status"] != "completed":
            return None
        
        job_dir = self.results_dir / job_id
        if not job_dir.exists():
            return None
        
        # Collect all GeoJSON files
        geojson_files = list(job_dir.glob("*.geojson"))
        if not geojson_files:
            # Try to find shapefiles and convert
            shp_files = list(job_dir.glob("*.shp"))
            if shp_files:
                geojson_files = self._convert_shapefiles_to_geojson(shp_files)
        
        if not geojson_files:
            return None
        
        # Analyze data size and create appropriate response
        total_size = 0
        all_features = []
        bounds_list = []
        
        for geojson_file in geojson_files:
            try:
                with open(geojson_file, 'r') as f:
                    data = json.load(f)
                
                if data.get("type") == "FeatureCollection":
                    features = data.get("features", [])
                    all_features.extend(features)
                    
                    # Calculate bounds
                    if features:
                        gdf = gpd.read_file(geojson_file)
                        bounds = gdf.total_bounds
                        bounds_list.append(bounds)
                
                total_size += geojson_file.stat().st_size
                
            except Exception as e:
                logger.warning(f"Error reading {geojson_file}: {e}")
                continue
        
        # Determine response type based on size
        size_mb = total_size / (1024 * 1024)
        
        if size_mb < 0.5:  # Small dataset - return GeoJSON
            return self._create_small_dataset_response(job_id, all_features, bounds_list)
        elif size_mb < 5:  # Medium dataset - return summary + sample
            return self._create_medium_dataset_response(job_id, all_features, bounds_list)
        else:  # Large dataset - return summary only
            return self._create_large_dataset_response(job_id, all_features, bounds_list)
    
    def _convert_shapefiles_to_geojson(self, shp_files: List[Path]) -> List[Path]:
        """Convert shapefiles to GeoJSON for GPT consumption"""
        geojson_files = []
        
        for shp_file in shp_files:
            try:
                gdf = gpd.read_file(shp_file)
                geojson_file = shp_file.with_suffix('.geojson')
                
                # Simplify geometries and reduce precision for GPT
                if not gdf.empty:
                    # Simplify geometries (tolerance in degrees)
                    gdf['geometry'] = gdf['geometry'].simplify(0.0001)
                    
                    # Round coordinates to 6 decimal places
                    gdf = gdf.round(6)
                    
                    # Write to GeoJSON
                    gdf.to_file(geojson_file, driver='GeoJSON')
                    geojson_files.append(geojson_file)
                    
            except Exception as e:
                logger.warning(f"Error converting {shp_file} to GeoJSON: {e}")
                continue
        
        return geojson_files
    
    def _create_small_dataset_response(self, job_id: str, features: List, bounds_list: List) -> Dict:
        """Create response for small datasets (include full GeoJSON)"""
        # Combine all features
        combined_geojson = {
            "type": "FeatureCollection",
            "features": features[:1000]  # Limit to 1000 features max
        }
        
        # Calculate combined bounds
        overall_bounds = self._calculate_overall_bounds(bounds_list)
        
        return {
            "data_size": "small",
            "response_type": "geojson",
            "geojson": combined_geojson,
            "feature_count": len(features),
            "bounds": overall_bounds,
            "instructions": "This dataset is small enough to be included directly as GeoJSON. You can use this data immediately with geopandas or other geospatial libraries."
        }
    
    def _create_medium_dataset_response(self, job_id: str, features: List, bounds_list: List) -> Dict:
        """Create response for medium datasets (summary + sample)"""
        # Create sample (first 100 features)
        sample_features = features[:100]
        sample_geojson = {
            "type": "FeatureCollection",
            "features": sample_features
        }
        
        overall_bounds = self._calculate_overall_bounds(bounds_list)
        summary = self._create_data_summary(features, overall_bounds)
        
        return {
            "data_size": "medium",
            "response_type": "summary",
            "sample_geojson": sample_geojson,
            "summary": summary,
            "instructions": f"This dataset contains {len(features)} features. A sample of {len(sample_features)} features is included. Use the download links for the complete dataset."
        }
    
    def _create_large_dataset_response(self, job_id: str, features: List, bounds_list: List) -> Dict:
        """Create response for large datasets (summary only)"""
        overall_bounds = self._calculate_overall_bounds(bounds_list)
        summary = self._create_data_summary(features, overall_bounds)
        
        return {
            "data_size": "large",
            "response_type": "links_only",
            "summary": summary,
            "instructions": f"This large dataset contains {len(features)} features. Due to size constraints, only summary statistics are provided. Use the download links to access the complete data."
        }
    
    def _calculate_overall_bounds(self, bounds_list: List) -> Dict:
        """Calculate overall bounds from list of bounds"""
        if not bounds_list:
            return {"minx": 0, "miny": 0, "maxx": 0, "maxy": 0}
        
        # Combine all bounds
        all_bounds = np.array(bounds_list)
        overall = {
            "minx": float(all_bounds[:, 0].min()),
            "miny": float(all_bounds[:, 1].min()),
            "maxx": float(all_bounds[:, 2].max()),
            "maxy": float(all_bounds[:, 3].max())
        }
        return overall
    
    def _create_data_summary(self, features: List, bounds: Dict) -> Dict:
        """Create summary statistics for features"""
        if not features:
            return {"feature_count": 0, "bounds": bounds}
        
        # Analyze attributes
        attribute_summary = {}
        for feature in features[:100]:  # Sample first 100 for attribute analysis
            properties = feature.get("properties", {})
            for key, value in properties.items():
                if key not in attribute_summary:
                    attribute_summary[key] = {"type": type(value).__name__, "sample_values": set()}
                
                if len(attribute_summary[key]["sample_values"]) < 5:
                    attribute_summary[key]["sample_values"].add(str(value))
        
        # Convert sets to lists for JSON serialization
        for key in attribute_summary:
            attribute_summary[key]["sample_values"] = list(attribute_summary[key]["sample_values"])
        
        return {
            "feature_count": len(features),
            "bounds": bounds,
            "attribute_summary": attribute_summary,
            "data_quality": {
                "has_geometries": all(f.get("geometry") is not None for f in features[:10]),
                "has_properties": all(f.get("properties") for f in features[:10])
            }
        }
    
    def generate_download_links(self, job_id: str) -> Dict:
        """Generate download links for different formats"""
        base_url = "https://project-data-downloader.onrender.com"
        
        # Check what files are available
        job_dir = self.results_dir / job_id
        zip_path = self.results_dir / f"{job_id}_results.zip"
        
        links = {}
        
        if zip_path.exists():
            links["original_zip"] = f"{base_url}/jobs/{job_id}/result"
        
        if job_dir.exists():
            # Check for GeoJSON files
            if list(job_dir.glob("*.geojson")):
                links["geojson"] = f"{base_url}/jobs/{job_id}/export/geojson"
            
            # Check for shapefiles
            if list(job_dir.glob("*.shp")):
                links["shapefile"] = f"{base_url}/jobs/{job_id}/export/shapefile"
            
            # Check for PDFs
            if list(job_dir.glob("*.pdf")):
                links["pdf"] = f"{base_url}/jobs/{job_id}/export/pdf"
        
        # Add expiration time (24 hours from now)
        from datetime import datetime, timedelta
        expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z"
        links["expires_at"] = expires_at
        
        return links
    
    def cleanup_old_jobs(self, max_age_days: int = 7):
        """Clean up old job files and results"""
        import time
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        # Clean up job metadata files
        for job_file in self.jobs_dir.glob("*.json"):
            if job_file.stat().st_mtime < cutoff_time:
                job_file.unlink()
                logger.info(f"Cleaned up old job file: {job_file}")
        
        # Clean up result directories and ZIP files
        for result_path in self.results_dir.iterdir():
            if result_path.stat().st_mtime < cutoff_time:
                if result_path.is_dir():
                    import shutil
                    shutil.rmtree(result_path)
                else:
                    result_path.unlink()
                logger.info(f"Cleaned up old result: {result_path}")


# Global job manager instance
job_manager = JobManager() 