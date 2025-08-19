"""
NOAA Atlas 14 precipitation frequency downloader plugin.
Downloads precipitation frequency estimates from NOAA's PFDS API for the centroid of the AOI.
"""
import os
import pandas as pd
from typing import Dict, Tuple, Optional
import requests
import logging
from datetime import datetime
import json

from core.base_downloader import BaseDownloader, LayerInfo, DownloadResult
from utils.pdf_utils import generate_precipitation_pdf

logger = logging.getLogger(__name__)


class NOAAAtlas14Downloader(BaseDownloader):
    """NOAA Atlas 14 precipitation frequency data downloader"""
    
    # Available data layers - combinations of analysis method, data type, and units
    AVAILABLE_LAYERS = {
        "pds_depth_english": LayerInfo(
            id="pds_depth_english",
            name="PDS Precipitation Depths (inches)",
            description="Partial Duration Series precipitation frequency estimates in inches",
            geometry_type="Point", 
            data_type="Tabular"
        ),
        "pds_depth_metric": LayerInfo(
            id="pds_depth_metric", 
            name="PDS Precipitation Depths (mm)",
            description="Partial Duration Series precipitation frequency estimates in millimeters",
            geometry_type="Point",
            data_type="Tabular"  
        ),
        "pds_intensity_english": LayerInfo(
            id="pds_intensity_english",
            name="PDS Precipitation Intensities (in/hr)", 
            description="Partial Duration Series precipitation intensity estimates in inches per hour",
            geometry_type="Point",
            data_type="Tabular"
        ),
        "pds_intensity_metric": LayerInfo(
            id="pds_intensity_metric",
            name="PDS Precipitation Intensities (mm/hr)",
            description="Partial Duration Series precipitation intensity estimates in mm per hour", 
            geometry_type="Point",
            data_type="Tabular"
        ),
        "ams_depth_english": LayerInfo(
            id="ams_depth_english",
            name="AMS Precipitation Depths (inches)",
            description="Annual Maximum Series precipitation frequency estimates in inches",
            geometry_type="Point", 
            data_type="Tabular"
        ),
        "ams_depth_metric": LayerInfo(
            id="ams_depth_metric", 
            name="AMS Precipitation Depths (mm)",
            description="Annual Maximum Series precipitation frequency estimates in millimeters",
            geometry_type="Point",
            data_type="Tabular"  
        )
    }
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.base_url = "https://hdsc.nws.noaa.gov/cgi-bin/hdsc/new/fe_text.csv"
        self.timeout = self.config.get('timeout', 30)
        self.max_retries = self.config.get('max_retries', 3)
    
    @property
    def source_name(self) -> str:
        return "NOAA Atlas 14 Precipitation Frequency"
    
    @property  
    def source_description(self) -> str:
        return "NOAA Atlas 14 precipitation frequency estimates providing statistical rainfall data for various durations and return periods at point locations."
    
    def get_available_layers(self) -> Dict[str, LayerInfo]:
        return self.AVAILABLE_LAYERS.copy()
    
    def download_layer(self, layer_id: str, aoi_bounds: Tuple[float, float, float, float],
                      output_path: str, **kwargs) -> DownloadResult:
        """Download NOAA Atlas 14 data for the centroid of the AOI"""
        
        if layer_id not in self.AVAILABLE_LAYERS:
            return DownloadResult(
                success=False,
                layer_id=layer_id, 
                error_message=f"Unknown layer ID: {layer_id}. Available layers: {list(self.AVAILABLE_LAYERS.keys())}"
            )
        
        # Calculate centroid of AOI bounds
        minx, miny, maxx, maxy = aoi_bounds
        centroid_lon = (minx + maxx) / 2
        centroid_lat = (miny + maxy) / 2
        
        logger.info(f"Downloading NOAA Atlas 14 data for centroid: ({centroid_lat:.6f}, {centroid_lon:.6f})")
        
        # Validate coverage area
        if not self._validate_coverage(centroid_lat, centroid_lon):
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message=f"Coordinates ({centroid_lat:.6f}, {centroid_lon:.6f}) may be outside NOAA Atlas 14 coverage area"
            )
        
        # Parse layer parameters
        parts = layer_id.split('_')
        if len(parts) != 3:
            return DownloadResult(
                success=False,
                layer_id=layer_id,
                error_message=f"Invalid layer ID format: {layer_id}"
            )
        
        series = parts[0]  # pds or ams
        data_type = parts[1]  # depth or intensity  
        units = parts[2]  # english or metric
        
        # Build API URL parameters
        params = {
            'lat': centroid_lat,
            'lon': centroid_lon, 
            'data': data_type,
            'units': units,
            'series': series
        }
        
        # Attempt download with retries
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempting NOAA API request (attempt {attempt + 1}/{self.max_retries})")
                response = requests.get(self.base_url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                # Check if response contains valid data
                if not response.text or 'No data available' in response.text:
                    return DownloadResult(
                        success=False,
                        layer_id=layer_id,
                        error_message="No precipitation frequency data available for this location"
                    )
                
                # Create output directory
                os.makedirs(output_path, exist_ok=True)
                
                # Generate simplified filenames for depth-duration-frequency data only
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Only create depth-duration-frequency CSV file
                csv_filename = f"depth_duration_frequency_{centroid_lat:.4f}_{centroid_lon:.4f}_{timestamp}.csv"
                output_file = os.path.join(output_path, csv_filename)
                
                # Save processed CSV response
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                # Parse and validate CSV data
                try:
                    # Parse the NOAA-specific CSV format
                    parsed_data = self._parse_noaa_csv(output_file)
                    feature_count = len(parsed_data.get('durations', []))
                    
                    # Create minimal metadata (embedded in PDF, not separate file)
                    metadata = {
                        'download_timestamp': timestamp,
                        'centroid_coordinates': {
                            'latitude': centroid_lat,
                            'longitude': centroid_lon
                        },
                        'data_summary': {
                            'durations': feature_count,
                            'return_periods': len(parsed_data.get('return_periods', [])),
                            'data_type': parsed_data.get('data_type', 'Unknown'),
                            'units': parsed_data.get('units', 'Unknown')
                        }
                    }
                    
                    # Generate PDF report - only essential output file
                    processed_file = parsed_data.get('processed_file')
                    if processed_file and os.path.exists(processed_file):
                        try:
                            pdf_filename = f"depth_duration_frequency_{centroid_lat:.4f}_{centroid_lon:.4f}_{timestamp}.pdf"
                            pdf_file = os.path.join(output_path, pdf_filename)
                            
                            # Create minimal metadata file for PDF generation only
                            temp_metadata_file = output_file.replace('.csv', '_temp_metadata.json')
                            with open(temp_metadata_file, 'w', encoding='utf-8') as f:
                                json.dump(metadata, f, indent=2)
                            
                            if generate_precipitation_pdf(processed_file, temp_metadata_file, pdf_file):
                                metadata['pdf_report'] = pdf_file
                                logger.info(f"Generated depth-duration-frequency PDF report: {os.path.basename(pdf_file)}")
                            else:
                                logger.warning("Failed to generate PDF report")
                                
                            # Clean up temporary metadata file
                            try:
                                os.remove(temp_metadata_file)
                            except:
                                pass
                                
                        except Exception as pdf_error:
                            logger.warning(f"PDF generation failed: {pdf_error}")
                    
                    logger.info(f"Successfully downloaded NOAA depth-duration-frequency data to {output_file}")
                    logger.info(f"Data contains {feature_count} precipitation frequency estimates")
                    
                    return DownloadResult(
                        success=True,
                        layer_id=layer_id,
                        feature_count=feature_count,
                        file_path=output_file,
                        metadata=metadata
                    )
                    
                except Exception as parse_error:
                    logger.error(f"Error parsing downloaded data: {parse_error}")
                    return DownloadResult(
                        success=False,
                        layer_id=layer_id,
                        error_message=f"Error parsing downloaded data: {parse_error}"
                    )
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    return DownloadResult(
                        success=False,
                        layer_id=layer_id,
                        error_message=f"Request timed out after {self.max_retries} attempts"
                    )
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    return DownloadResult(
                        success=False,
                        layer_id=layer_id,
                        error_message=f"Request failed after {self.max_retries} attempts: {e}"
                    )
                
            except Exception as e:
                logger.error(f"Unexpected error downloading NOAA Atlas 14 data: {e}")
                return DownloadResult(
                    success=False,
                    layer_id=layer_id,
                    error_message=f"Unexpected error: {e}"
                )
        
        # Should not reach here, but just in case
        return DownloadResult(
            success=False,
            layer_id=layer_id,
            error_message="Download failed for unknown reason"
        )
    
    def _validate_coverage(self, lat: float, lon: float) -> bool:
        """
        Validate that coordinates fall within NOAA Atlas 14 coverage area
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            
        Returns:
            True if coordinates are within expected coverage area
        """
        # NOAA Atlas 14 covers the contiguous US, Alaska, Hawaii, and territories
        # Basic validation for continental US bounds
        conus_bounds = {
            'lat_min': 24.0,  # Southern Florida
            'lat_max': 49.0,  # Northern border
            'lon_min': -125.0,  # West coast
            'lon_max': -66.0   # East coast
        }
        
        # Check if within CONUS bounds
        if (conus_bounds['lat_min'] <= lat <= conus_bounds['lat_max'] and 
            conus_bounds['lon_min'] <= lon <= conus_bounds['lon_max']):
            return True
        
        # Check Alaska bounds (rough approximation)
        if 54.0 <= lat <= 72.0 and -180.0 <= lon <= -130.0:
            return True
        
        # Check Hawaii bounds (rough approximation)
        if 18.0 <= lat <= 23.0 and -162.0 <= lon <= -154.0:
            return True
        
        logger.warning(f"Coordinates ({lat:.6f}, {lon:.6f}) may be outside NOAA Atlas 14 coverage area")
        return False
    
    def validate_aoi(self, aoi_bounds: Tuple[float, float, float, float]) -> bool:
        """
        Validate that the AOI centroid is acceptable for NOAA Atlas 14 data
        
        Args:
            aoi_bounds: Tuple of (minx, miny, maxx, maxy) in EPSG:4326
            
        Returns:
            True if AOI centroid is valid for this data source
        """
        # First do basic bounds validation
        if not super().validate_aoi(aoi_bounds):
            return False
        
        # Calculate and validate centroid
        minx, miny, maxx, maxy = aoi_bounds
        centroid_lon = (minx + maxx) / 2
        centroid_lat = (miny + maxy) / 2
        
        return self._validate_coverage(centroid_lat, centroid_lon)
    
    def _parse_noaa_csv(self, file_path: str) -> Dict:
        """
        Parse the NOAA Atlas 14 CSV format which has non-standard structure
        
        Args:
            file_path: Path to the NOAA CSV file
            
        Returns:
            Dictionary containing parsed data and metadata
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Parse metadata from header
            metadata = {}
            data_type = "Unknown"
            units = "Unknown"
            
            for i, line in enumerate(lines):
                line = line.strip()
                if line.startswith("Point precipitation frequency estimates"):
                    units_match = line.split("(")[-1].replace(")", "")
                    units = units_match if units_match else "Unknown"
                elif line.startswith("Data type:"):
                    data_type = line.split(":", 1)[1].strip()
                elif line.startswith("Time series type:"):
                    metadata['time_series_type'] = line.split(":", 1)[1].strip()
                elif line.startswith("Project area:"):
                    metadata['project_area'] = line.split(":", 1)[1].strip()
                elif line.startswith("Latitude:"):
                    metadata['latitude'] = line.split(":", 1)[1].strip()
                elif line.startswith("Longitude:"):
                    metadata['longitude'] = line.split(":", 1)[1].strip()
                elif line.startswith("Elevation"):
                    metadata['elevation'] = line.split(":", 1)[1].strip()
            
            # Find the main data section
            main_data_start = None
            for i, line in enumerate(lines):
                if line.strip().startswith("by duration for ARI (years):"):
                    main_data_start = i
                    break
            
            if main_data_start is None:
                raise ValueError("Could not find main data section in NOAA CSV")
            
            # Parse return periods from header
            header_line = lines[main_data_start].strip()
            return_periods = []
            if "," in header_line:
                parts = header_line.split(",")[1:]  # Skip the "by duration for ARI (years):" part
                return_periods = [int(p.strip()) for p in parts if p.strip().isdigit()]
            
            # Parse precipitation data
            durations = []
            estimates = []
            
            for i in range(main_data_start + 1, len(lines)):
                line = lines[i].strip()
                if not line or line.startswith("PRECIPITATION FREQUENCY") or line.startswith("Date/time"):
                    break
                
                if ":" in line and "," in line:
                    parts = line.split(",")
                    duration = parts[0].replace(":", "").strip()
                    values = []
                    for part in parts[1:]:
                        part = part.strip()
                        if part and part != "":
                            try:
                                values.append(float(part))
                            except ValueError:
                                pass
                    
                    if duration and values:
                        durations.append(duration)
                        estimates.append(values)
            
            # Create structured data
            result = {
                'metadata': metadata,
                'data_type': data_type,
                'units': units,
                'return_periods': return_periods,
                'durations': durations,
                'estimates': estimates
            }
            
            # Create a more user-friendly DataFrame and save it
            if durations and return_periods and estimates:
                df_data = {'Duration': durations}
                for i, rp in enumerate(return_periods):
                    col_name = f"{rp}_year"
                    df_data[col_name] = [row[i] if i < len(row) else None for row in estimates]
                
                df = pd.DataFrame(df_data)
                processed_file = file_path.replace('.csv', '_processed.csv')
                df.to_csv(processed_file, index=False)
                result['processed_file'] = processed_file
                
# PDF generation will be handled in download_layer after metadata file is created
                
                logger.info(f"Created processed precipitation frequency table with {len(durations)} durations and {len(return_periods)} return periods")
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing NOAA CSV file: {e}")
            return {
                'metadata': {},
                'data_type': 'Unknown',
                'units': 'Unknown', 
                'return_periods': [],
                'durations': [],
                'estimates': []
            } 