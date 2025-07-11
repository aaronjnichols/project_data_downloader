"""
FEMA NFHL (National Flood Hazard Layer) downloader plugin.
Downloads all available FEMA spatial data layers from the NFHL service.
"""
import os
import io
import tempfile
import zipfile
from typing import Dict, Tuple
import geopandas as gpd

from core.base_downloader import BaseDownloader, LayerInfo, DownloadResult
from utils.download_utils import DownloadSession, extract_zip_response, validate_response_content
from utils.spatial_utils import clip_vector_to_aoi, safe_file_name


class FEMADownloader(BaseDownloader):
    """FEMA NFHL data downloader"""
    
    # FEMA NFHL Layer definitions - all available layers from the MapServer
    NFHL_LAYERS = {
        "0": LayerInfo(
            id="0", name="NFHL_Availability", description="NFHL Availability",
            geometry_type="Polygon", data_type="Vector"
        ),
        "1": LayerInfo(
            id="1", name="LOMRs", description="Letters of Map Revision",
            geometry_type="Polygon", data_type="Vector"
        ),
        "3": LayerInfo(
            id="3", name="FIRM_Panels", description="FIRM Panels",
            geometry_type="Polygon", data_type="Vector"
        ),
        "4": LayerInfo(
            id="4", name="Base_Index", description="Base Index",
            geometry_type="Polygon", data_type="Vector"
        ),
        "5": LayerInfo(
            id="5", name="PLSS", description="Public Land Survey System",
            geometry_type="Polygon", data_type="Vector"
        ),
        "6": LayerInfo(
            id="6", name="Topographic_Low_Confidence_Areas", 
            description="Topographic Low Confidence Areas",
            geometry_type="Polygon", data_type="Vector"
        ),
        "7": LayerInfo(
            id="7", name="River_Mile_Markers", description="River Mile Markers",
            geometry_type="Point", data_type="Vector"
        ),
        "8": LayerInfo(
            id="8", name="Datum_Conversion_Points", description="Datum Conversion Points",
            geometry_type="Point", data_type="Vector"
        ),
        "9": LayerInfo(
            id="9", name="Coastal_Gages", description="Coastal Gages",
            geometry_type="Point", data_type="Vector"
        ),
        "10": LayerInfo(
            id="10", name="Gages", description="Gages",
            geometry_type="Point", data_type="Vector"
        ),
        "11": LayerInfo(
            id="11", name="Nodes", description="Nodes",
            geometry_type="Point", data_type="Vector"
        ),
        "12": LayerInfo(
            id="12", name="High_Water_Marks", description="High Water Marks",
            geometry_type="Point", data_type="Vector"
        ),
        "13": LayerInfo(
            id="13", name="Station_Start_Points", description="Station Start Points",
            geometry_type="Point", data_type="Vector"
        ),
        "14": LayerInfo(
            id="14", name="Cross_Sections", description="Cross-Sections",
            geometry_type="Polyline", data_type="Vector"
        ),
        "15": LayerInfo(
            id="15", name="Coastal_Transects", description="Coastal Transects",
            geometry_type="Polyline", data_type="Vector"
        ),
        "16": LayerInfo(
            id="16", name="Base_Flood_Elevations", description="Base Flood Elevations (BFEs)",
            geometry_type="Polyline", data_type="Vector"
        ),
        "17": LayerInfo(
            id="17", name="Profile_Baselines", description="Profile Baselines",
            geometry_type="Polyline", data_type="Vector"
        ),
        "18": LayerInfo(
            id="18", name="Transect_Baselines", description="Transect Baselines",
            geometry_type="Polyline", data_type="Vector"
        ),
        "19": LayerInfo(
            id="19", name="Limit_of_Moderate_Wave_Action", 
            description="Limit of Moderate Wave Action",
            geometry_type="Polyline", data_type="Vector"
        ),
        "20": LayerInfo(
            id="20", name="Water_Lines", description="Water Lines (Stream Centerlines)",
            geometry_type="Polyline", data_type="Vector"
        ),
        "22": LayerInfo(
            id="22", name="Political_Jurisdictions", description="Political Jurisdictions",
            geometry_type="Polygon", data_type="Vector"
        ),
        "23": LayerInfo(
            id="23", name="Levees", description="Levees",
            geometry_type="Polyline", data_type="Vector"
        ),
        "24": LayerInfo(
            id="24", name="General_Structures", description="General Structures",
            geometry_type="Polyline", data_type="Vector"
        ),
        "25": LayerInfo(
            id="25", name="Primary_Frontal_Dunes", description="Primary Frontal Dunes",
            geometry_type="Polyline", data_type="Vector"
        ),
        "26": LayerInfo(
            id="26", name="Hydrologic_Reaches", description="Hydrologic Reaches",
            geometry_type="Polyline", data_type="Vector"
        ),
        "27": LayerInfo(
            id="27", name="Flood_Hazard_Boundaries", description="Flood Hazard Boundaries",
            geometry_type="Polyline", data_type="Vector"
        ),
        "28": LayerInfo(
            id="28", name="Flood_Hazard_Zones", description="Flood Hazard Zones",
            geometry_type="Polygon", data_type="Vector"
        ),
        "29": LayerInfo(
            id="29", name="Seclusion_Boundaries", description="Seclusion Boundaries",
            geometry_type="Polygon", data_type="Vector"
        ),
        "30": LayerInfo(
            id="30", name="Alluvial_Fans", description="Alluvial Fans",
            geometry_type="Polygon", data_type="Vector"
        ),
        "31": LayerInfo(
            id="31", name="Subbasins", description="Subbasins",
            geometry_type="Polygon", data_type="Vector"
        ),
        "32": LayerInfo(
            id="32", name="Water_Areas", description="Water Areas",
            geometry_type="Polygon", data_type="Vector"
        ),
        "34": LayerInfo(
            id="34", name="LOMAs", description="Letters of Map Amendment",
            geometry_type="Point", data_type="Vector"
        )
    }
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.base_url = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer"
        self.wfs_url = "https://hazards.fema.gov/arcgis/services/public/NFHL/MapServer/WFSServer"
        self.session = DownloadSession(
            max_retries=self.config.get('max_retries', 3),
            timeout=self.config.get('timeout', 60)
        )
    
    @property
    def source_name(self) -> str:
        return "FEMA National Flood Hazard Layer (NFHL)"
    
    @property
    def source_description(self) -> str:
        return "Federal Emergency Management Agency flood hazard mapping data including flood zones, base flood elevations, cross-sections, and related flood risk information."
    
    def get_available_layers(self) -> Dict[str, LayerInfo]:
        return self.NFHL_LAYERS.copy()
    
    def download_layer(self, layer_id: str, aoi_bounds: Tuple[float, float, float, float], 
                      output_path: str, **kwargs) -> DownloadResult:
        """Download a specific FEMA NFHL layer"""
        
        if layer_id not in self.NFHL_LAYERS:
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message=f"Unknown layer ID: {layer_id}"
            )
        
        layer_info = self.NFHL_LAYERS[layer_id]
        
        # Create AOI GeoDataFrame for clipping
        from shapely.geometry import box
        aoi_geom = box(*aoi_bounds)
        aoi_gdf = gpd.GeoDataFrame([1], geometry=[aoi_geom], crs='EPSG:4326')
        
        # Try WFS first (only for supported layers)
        gdf = self._try_wfs_download(layer_id, aoi_bounds)
        
        # If WFS failed, try REST API
        if gdf is None:
            gdf = self._try_rest_api_download(layer_id, aoi_bounds)
        
        if gdf is None or len(gdf) == 0:
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message="No data found for this layer and AOI"
            )
        
        # Clip to AOI
        clipped_gdf = clip_vector_to_aoi(gdf, aoi_gdf)
        
        if clipped_gdf is None or len(clipped_gdf) == 0:
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message="No features found within AOI after clipping"
            )
        
        # Save the clipped data
        try:
            os.makedirs(output_path, exist_ok=True)
            safe_name = safe_file_name(layer_info.name)
            output_file = os.path.join(output_path, f"{safe_name}_clipped.shp")
            clipped_gdf.to_file(output_file)
            
            return DownloadResult(
                success=True,
                layer_id=layer_id,
                feature_count=len(clipped_gdf),
                file_path=output_file,
                metadata={"original_features": len(gdf), "clipped_features": len(clipped_gdf)}
            )
            
        except Exception as e:
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message=f"Error saving layer: {str(e)}"
            )
    
    def _try_wfs_download(self, layer_id: str, aoi_bounds: Tuple[float, float, float, float]) -> gpd.GeoDataFrame:
        """Try downloading via WFS (only works for certain layers)"""
        
        # Only certain layers support WFS - primarily flood hazard zones
        if layer_id != "28":  # For now, only try WFS for flood hazard zones
            return None
        
        wfs_layer_names = {
            "28": "NFHL:Flood_Hazard_Zones"
        }
        
        if layer_id not in wfs_layer_names:
            return None
        
        minx, miny, maxx, maxy = aoi_bounds
        bbox_str = f'{minx},{miny},{maxx},{maxy},EPSG:4326'
        
        params = {
            'service': 'WFS',
            'request': 'GetFeature',
            'version': '1.1.0',
            'typeName': wfs_layer_names[layer_id],
            'outputFormat': 'shape-zip',
            'bbox': bbox_str
        }
        
        response = self.session.get(self.wfs_url, params=params)
        
        if response and response.content.startswith(b'PK'):
            return self._process_zip_response(response)
        
        return None
    
    def _try_rest_api_download(self, layer_id: str, aoi_bounds: Tuple[float, float, float, float]) -> gpd.GeoDataFrame:
        """Try downloading via REST API"""
        
        minx, miny, maxx, maxy = aoi_bounds
        
        params = {
            'where': '1=1',  # Select all features
            'geometry': f'{minx},{miny},{maxx},{maxy}',
            'geometryType': 'esriGeometryEnvelope',
            'inSR': '4326',
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': '*',
            'returnGeometry': 'true',
            'f': 'geojson'
        }
        
        url = f"{self.base_url}/{layer_id}/query"
        response = self.session.get(url, params=params)
        
        if response:
            return self._process_geojson_response(response)
        
        return None
    
    def _process_geojson_response(self, response) -> gpd.GeoDataFrame:
        """Process GeoJSON response from REST API"""
        try:
            gdf = gpd.read_file(io.StringIO(response.text))
            return gdf if len(gdf) > 0 else None
        except Exception:
            return None
    
    def _process_zip_response(self, response) -> gpd.GeoDataFrame:
        """Process ZIP response from WFS"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Find the .shp file
                shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
                if not shp_files:
                    return None
                
                shp_file = os.path.join(temp_dir, shp_files[0])
                gdf = gpd.read_file(shp_file)
                return gdf
                
        except (zipfile.BadZipFile, Exception):
            return None 