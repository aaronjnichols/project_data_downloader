"""USGS LiDAR/DEM downloader plugin."""
import os
import json
import zipfile
from typing import Dict, Tuple

from core.base_downloader import BaseDownloader, LayerInfo, DownloadResult
from utils.download_utils import DownloadSession, validate_response_content
from utils.spatial_utils import safe_file_name, dem_to_contours


class USGSLidarDownloader(BaseDownloader):
    """Downloader for USGS 3DEP LiDAR DEM data."""

    DEM_LAYER = LayerInfo(
        id="dem",
        name="Digital Elevation Model",
        description="USGS 3DEP DEM clipped to AOI",
        geometry_type="Raster",
        data_type="Raster",
    )

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.base_url = "https://tnmaccess.nationalmap.gov/api/v1/products"
        self.session = DownloadSession(
            max_retries=self.config.get("max_retries", 3),
            timeout=self.config.get("timeout", 60),
        )

    @property
    def source_name(self) -> str:
        return "USGS 3DEP LiDAR"

    @property
    def source_description(self) -> str:
        return (
            "U.S. Geological Survey 3D Elevation Program LiDAR and DEM downloads"
        )

    def get_available_layers(self) -> Dict[str, LayerInfo]:
        return {"dem": self.DEM_LAYER}

    def download_layer(
        self, layer_id: str, aoi_bounds: Tuple[float, float, float, float], output_path: str, **kwargs
    ) -> DownloadResult:
        if layer_id != "dem":
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message=f"Unsupported layer {layer_id}",
            )

        minx, miny, maxx, maxy = aoi_bounds
        params = {
            "bbox": f"{minx},{miny},{maxx},{maxy}",
            "datasets": "3DEP Elevation: DEM (1 meter)",
            "prodFormats": "GeoTIFF",
            "outputFormat": "JSON",
            "max": 1,
        }

        response = self.session.get(self.base_url, params=params)
        if not validate_response_content(response, ["application/json"]):
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message="Failed to query USGS API",
            )

        try:
            data = response.json()
            items = data.get("items", [])
            if not items:
                return DownloadResult(
                    success=False,
                    layer_id=layer_id,
                    error_message="No DEM available for AOI",
                )
            download_url = items[0].get("downloadURL") or items[0].get("urls", {}).get("downloadURL")
            if not download_url:
                return DownloadResult(
                    success=False,
                    layer_id=layer_id,
                    error_message="Download URL not found",
                )
        except Exception as e:
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message=f"Invalid API response: {e}",
            )

        os.makedirs(output_path, exist_ok=True)
        zip_path = os.path.join(output_path, "usgs_dem.zip")

        if not self.session.download_file(download_url, zip_path):
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message="DEM download failed",
            )

        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(output_path)
        except Exception as e:
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message=f"Error extracting DEM: {e}",
            )
        finally:
            if os.path.exists(zip_path):
                os.remove(zip_path)

        dem_files = [f for f in os.listdir(output_path) if f.lower().endswith(".tif")]
        if not dem_files:
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message="No DEM file found after extraction",
            )

        dem_path = os.path.join(output_path, dem_files[0])
        metadata = {"dem_path": dem_path}

        interval = self.config.get("contour_interval")
        if interval:
            contour_name = f"contours_{safe_file_name(str(interval))}.shp"
            contour_path = os.path.join(output_path, contour_name)
            success = dem_to_contours(dem_path, contour_path, interval)
            if success:
                metadata["contour_path"] = contour_path

        return DownloadResult(success=True, layer_id=layer_id, file_path=dem_path, metadata=metadata)
