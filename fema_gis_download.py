# FEMA NFHL Multi-Layer Downloader - Download all spatial data layers from NFHL
import requests, zipfile, io, os, geopandas as gpd
import tempfile
import shutil
from collections import defaultdict

# Configuration
out_path = r'C:\_Python\project_data_downloader\output'
aoi_shapefile = r'C:\_Python\project_data_downloader\data\aoi.shp'  # Path to your AOI shapefile

# FEMA NFHL Layer definitions - all available layers from the MapServer
NFHL_LAYERS = {
    0: {"name": "NFHL_Availability", "description": "NFHL Availability", "geometry": "Polygon"},
    1: {"name": "LOMRs", "description": "Letters of Map Revision", "geometry": "Polygon"},
    3: {"name": "FIRM_Panels", "description": "FIRM Panels", "geometry": "Polygon"},
    4: {"name": "Base_Index", "description": "Base Index", "geometry": "Polygon"},
    5: {"name": "PLSS", "description": "Public Land Survey System", "geometry": "Polygon"},
    6: {"name": "Topographic_Low_Confidence_Areas", "description": "Topographic Low Confidence Areas", "geometry": "Polygon"},
    7: {"name": "River_Mile_Markers", "description": "River Mile Markers", "geometry": "Point"},
    8: {"name": "Datum_Conversion_Points", "description": "Datum Conversion Points", "geometry": "Point"},
    9: {"name": "Coastal_Gages", "description": "Coastal Gages", "geometry": "Point"},
    10: {"name": "Gages", "description": "Gages", "geometry": "Point"},
    11: {"name": "Nodes", "description": "Nodes", "geometry": "Point"},
    12: {"name": "High_Water_Marks", "description": "High Water Marks", "geometry": "Point"},
    13: {"name": "Station_Start_Points", "description": "Station Start Points", "geometry": "Point"},
    14: {"name": "Cross_Sections", "description": "Cross-Sections", "geometry": "Polyline"},
    15: {"name": "Coastal_Transects", "description": "Coastal Transects", "geometry": "Polyline"},
    16: {"name": "Base_Flood_Elevations", "description": "Base Flood Elevations (BFEs)", "geometry": "Polyline"},
    17: {"name": "Profile_Baselines", "description": "Profile Baselines", "geometry": "Polyline"},
    18: {"name": "Transect_Baselines", "description": "Transect Baselines", "geometry": "Polyline"},
    19: {"name": "Limit_of_Moderate_Wave_Action", "description": "Limit of Moderate Wave Action", "geometry": "Polyline"},
    20: {"name": "Water_Lines", "description": "Water Lines (Stream Centerlines)", "geometry": "Polyline"},
    22: {"name": "Political_Jurisdictions", "description": "Political Jurisdictions", "geometry": "Polygon"},
    23: {"name": "Levees", "description": "Levees", "geometry": "Polyline"},
    24: {"name": "General_Structures", "description": "General Structures", "geometry": "Polyline"},
    25: {"name": "Primary_Frontal_Dunes", "description": "Primary Frontal Dunes", "geometry": "Polyline"},
    26: {"name": "Hydrologic_Reaches", "description": "Hydrologic Reaches", "geometry": "Polyline"},
    27: {"name": "Flood_Hazard_Boundaries", "description": "Flood Hazard Boundaries", "geometry": "Polyline"},
    28: {"name": "Flood_Hazard_Zones", "description": "Flood Hazard Zones", "geometry": "Polygon"},
    29: {"name": "Seclusion_Boundaries", "description": "Seclusion Boundaries", "geometry": "Polygon"},
    30: {"name": "Alluvial_Fans", "description": "Alluvial Fans", "geometry": "Polygon"},
    31: {"name": "Subbasins", "description": "Subbasins", "geometry": "Polygon"},
    32: {"name": "Water_Areas", "description": "Water Areas", "geometry": "Polygon"},
    34: {"name": "LOMAs", "description": "Letters of Map Amendment", "geometry": "Point"}
}

def load_aoi(aoi_path):
    """Load the AOI shapefile and get its bounds"""
    try:
        print(f"Loading AOI shapefile: {aoi_path}")
        aoi_gdf = gpd.read_file(aoi_path)
        
        # Ensure AOI is in WGS84 (EPSG:4326) for the API requests
        if aoi_gdf.crs != 'EPSG:4326':
            print(f"Reprojecting AOI from {aoi_gdf.crs} to EPSG:4326")
            aoi_gdf = aoi_gdf.to_crs('EPSG:4326')
        
        print(f"AOI loaded successfully with {len(aoi_gdf)} feature(s)")
        print(f"AOI CRS: {aoi_gdf.crs}")
        
        # Get the bounds of the AOI
        bounds = aoi_gdf.total_bounds  # [minx, miny, maxx, maxy]
        bbox_str = f'{bounds[0]},{bounds[1]},{bounds[2]},{bounds[3]},EPSG:4326'
        
        print(f"AOI bounds: {bounds}")
        print(f"Bbox string: {bbox_str}")
        
        return aoi_gdf, bbox_str
        
    except Exception as e:
        print(f"Error loading AOI shapefile: {e}")
        return None, None

def try_wfs_approach_for_layer(bbox, layer_id):
    """Try the WFS approach for a specific layer (limited layers support WFS)"""
    # Only certain layers support WFS - primarily flood hazard zones
    if layer_id != 28:  # For now, only try WFS for flood hazard zones
        return None
        
    wfs_layer_names = {
        28: "NFHL:Flood_Hazard_Zones"
    }
    
    if layer_id not in wfs_layer_names:
        return None
        
    params = {
        'service': 'WFS', 
        'request': 'GetFeature', 
        'version': '1.1.0',
        'typeName': wfs_layer_names[layer_id],
        'outputFormat': 'shape-zip',
        'bbox': bbox
    }
    url = 'https://hazards.fema.gov/arcgis/services/public/NFHL/MapServer/WFSServer'
    
    try:
        response = requests.get(url, params=params, timeout=60)
        if response.status_code == 200 and len(response.content) > 0:
            return response
        return None
    except Exception as e:
        print(f"WFS request failed for layer {layer_id}: {e}")
        return None

def try_rest_api_approach_for_layer(bbox, layer_id):
    """Try using the REST API for a specific layer"""
    # Convert bbox to the format expected by ArcGIS REST API
    bbox_coords = bbox.split(',')
    xmin, ymin, xmax, ymax = map(float, bbox_coords[:4])
    
    params = {
        'where': '1=1',  # Select all features
        'geometry': f'{xmin},{ymin},{xmax},{ymax}',
        'geometryType': 'esriGeometryEnvelope',
        'inSR': '4326',
        'spatialRel': 'esriSpatialRelIntersects',
        'outFields': '*',
        'returnGeometry': 'true',
        'f': 'geojson'
    }
    
    # Use the REST API endpoint for the specific layer
    url = f'https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/{layer_id}/query'
    
    try:
        response = requests.get(url, params=params, timeout=60)
        if response.status_code == 200 and len(response.content) > 0:
            return response
        return None
    except Exception as e:
        print(f"REST API request failed for layer {layer_id}: {e}")
        return None

def process_geojson_response(response):
    """Process GeoJSON response from REST API"""
    try:
        # Read GeoJSON directly into GeoPandas
        gdf = gpd.read_file(io.StringIO(response.text))
        
        if len(gdf) == 0:
            return None
            
        return gdf
    except Exception as e:
        print(f"Error processing GeoJSON response: {e}")
        return None

def process_zip_response(response):
    """Process ZIP response from WFS"""
    try:
        # Create a temporary directory to extract the zip
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract the zip file
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                zip_ref.extractall(temp_dir)
                
            # Find the .shp file in the extracted contents
            shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
            if not shp_files:
                return None
                
            shp_file = os.path.join(temp_dir, shp_files[0])
            
            # Read the shapefile with geopandas
            gdf = gpd.read_file(shp_file)
            
            return gdf
            
    except zipfile.BadZipFile:
        return None
    except Exception as e:
        print(f"Error processing zip response: {e}")
        return None

def clip_to_aoi(data_gdf, aoi_gdf):
    """Clip the data to the exact AOI geometry"""
    try:
        # Ensure both datasets are in the same CRS
        if data_gdf.crs != aoi_gdf.crs:
            data_gdf = data_gdf.to_crs(aoi_gdf.crs)
        
        # Perform the clip operation
        clipped_gdf = gpd.clip(data_gdf, aoi_gdf)
        
        if len(clipped_gdf) == 0:
            return None
            
        return clipped_gdf
        
    except Exception as e:
        print(f"Error clipping data to AOI: {e}")
        return data_gdf  # Return original data if clipping fails

def download_layer(layer_id, layer_info, bbox, aoi_gdf):
    """Download a specific NFHL layer"""
    layer_name = layer_info["name"]
    layer_desc = layer_info["description"]
    
    print(f"\n{'='*60}")
    print(f"Processing Layer {layer_id}: {layer_desc}")
    print(f"{'='*60}")
    
    gdf = None
    
    # Try WFS first (only for supported layers)
    response = try_wfs_approach_for_layer(bbox, layer_id)
    if response and response.content.startswith(b'PK'):
        print(f"WFS returned data for layer {layer_id}, processing...")
        gdf = process_zip_response(response)
    
    # If WFS failed, try REST API
    if gdf is None:
        response = try_rest_api_approach_for_layer(bbox, layer_id)
        if response:
            gdf = process_geojson_response(response)
    
    # Process the data if we got any
    if gdf is not None and len(gdf) > 0:
        print(f"Successfully downloaded {len(gdf)} features for {layer_desc}")
        
        # Clip to AOI
        clipped_gdf = clip_to_aoi(gdf, aoi_gdf)
        
        if clipped_gdf is not None and len(clipped_gdf) > 0:
            # Save the clipped data
            try:
                os.makedirs(out_path, exist_ok=True)
                output_file = os.path.join(out_path, f"{layer_name}_clipped.shp")
                clipped_gdf.to_file(output_file)
                print(f"✓ Saved {len(clipped_gdf)} features to: {output_file}")
                return True, len(clipped_gdf)
            except Exception as e:
                print(f"✗ Error saving {layer_desc}: {e}")
                return False, 0
        else:
            print(f"⚠ No features found within AOI for {layer_desc}")
            return False, 0
    else:
        print(f"⚠ No data found for {layer_desc}")
        return False, 0

# Main execution
print("FEMA NFHL Multi-Layer Downloader")
print("=" * 50)
print(f"Downloading {len(NFHL_LAYERS)} NFHL layers including:")
print("• Flood Hazard Zones • Base Flood Elevations • Cross-Sections")
print("• Water Lines (Stream Centerlines) • Levees • FIRM Panels")
print("• And all other available NFHL spatial data layers")
print("=" * 50)

# Load the AOI shapefile
aoi_gdf, bbox = load_aoi(aoi_shapefile)

if aoi_gdf is None or bbox is None:
    print("Failed to load AOI shapefile. Please check the path and file format.")
    exit(1)

# Download statistics
successful_downloads = 0
total_features = 0
failed_layers = []

# Download each layer
for layer_id, layer_info in NFHL_LAYERS.items():
    try:
        success, feature_count = download_layer(layer_id, layer_info, bbox, aoi_gdf)
        if success:
            successful_downloads += 1
            total_features += feature_count
        else:
            failed_layers.append(f"{layer_id}: {layer_info['name']}")
    except Exception as e:
        print(f"✗ Error processing layer {layer_id} ({layer_info['name']}): {e}")
        failed_layers.append(f"{layer_id}: {layer_info['name']}")

# Print summary
print(f"\n{'='*60}")
print("DOWNLOAD SUMMARY")
print(f"{'='*60}")
print(f"Total layers attempted: {len(NFHL_LAYERS)}")
print(f"Successful downloads: {successful_downloads}")
print(f"Failed downloads: {len(failed_layers)}")
print(f"Total features downloaded: {total_features}")

if successful_downloads > 0:
    print(f"\n✓ SUCCESS: Downloaded {successful_downloads} layers with {total_features} total features")
    print(f"  Output directory: {out_path}")
    print("  Files saved with naming pattern: [LayerName]_clipped.shp")

if failed_layers:
    print(f"\n⚠ FAILED LAYERS ({len(failed_layers)}):")
    for layer in failed_layers:
        print(f"  - {layer}")
    print("\nNote: Some layers may not have data in your AOI or may be unavailable.")

print(f"\n{'='*60}")
print("Download complete!")
print(f"{'='*60}")
