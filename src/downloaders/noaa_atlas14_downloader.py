"""
NOAA Atlas 14 precipitation frequency downloader plugin.
Downloads precipitation frequency estimates from NOAA's PFDS API for the centroid of the AOI.

Enhanced features:
- Robust CSV parsing with encoding detection
- Multiple output formats (CSV, JSON, PDF)
- Enhanced error handling and validation
- Quality assessment metrics
"""
import os
import pandas as pd
from typing import Dict, Tuple, Optional, Any, List
import requests
import logging
from datetime import datetime
import json
from pathlib import Path

try:
    import chardet
    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False

from src.core.base_downloader import BaseDownloader, LayerInfo, DownloadResult
from src.utils.pdf_utils import generate_precipitation_pdf

logger = logging.getLogger(__name__)


class NOAAAtlas14Downloader(BaseDownloader):
    """NOAA Atlas 14 precipitation frequency data downloader"""
    
    # Available data layer - Only depth frequency estimates in inches
    AVAILABLE_LAYERS = {
        "pds_depth_english": LayerInfo(
            id="pds_depth_english",
            name="Precipitation Depth Frequency Estimates (inches)",
            description="Precipitation frequency estimates for various durations and return periods in inches",
            geometry_type="Point", 
            data_type="Tabular"
        )
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = "https://hdsc.nws.noaa.gov/cgi-bin/hdsc/new/fe_text.csv"
        self.timeout = self.config.get('timeout', 30)
        self.max_retries = self.config.get('max_retries', 3)
        
        # Enhanced configuration options
        self.output_formats = self.config.get('output_formats', ['csv', 'json', 'pdf'])
        self.generate_quality_report = self.config.get('generate_quality_report', True)
        self.validate_data_completeness = self.config.get('validate_data_completeness', True)
    
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
        
        if not self._validate_layer_id(layer_id):
            return self._create_error_result(layer_id, f"Unknown layer ID: {layer_id}. Available layers: {list(self.AVAILABLE_LAYERS.keys())}")
        
        # Calculate centroid of AOI bounds
        minx, miny, maxx, maxy = aoi_bounds
        centroid_lon = (minx + maxx) / 2
        centroid_lat = (miny + maxy) / 2
        
        logger.info(f"Downloading NOAA Atlas 14 data for centroid: ({centroid_lat:.6f}, {centroid_lon:.6f})")
        
        # Validate coverage area
        if not self._validate_coverage(centroid_lat, centroid_lon):
            return self._create_error_result(layer_id, f"Coordinates ({centroid_lat:.6f}, {centroid_lon:.6f}) may be outside NOAA Atlas 14 coverage area")
        
        # Parse layer parameters
        parts = layer_id.split('_')
        if len(parts) != 3:
            return self._create_error_result(layer_id, f"Invalid layer ID format: {layer_id}")
        
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
                    return self._create_error_result(layer_id, "No precipitation frequency data available for this location")
                
                # Create output directory
                os.makedirs(output_path, exist_ok=True)
                
                # Generate simplified filenames for depth-duration-frequency data only
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Only create depth-duration-frequency CSV file
                csv_filename = f"depth_duration_frequency_{centroid_lat:.4f}_{centroid_lon:.4f}_{timestamp}.csv"
                output_file = os.path.join(output_path, csv_filename)
                
                # Save processed CSV response with encoding detection
                encoding = self._detect_encoding(response.content)
                with open(output_file, 'w', encoding=encoding) as f:
                    f.write(response.text)
                
                # Parse and validate CSV data with enhanced parsing
                try:
                    # Parse the NOAA-specific CSV format
                    parsed_data = self._parse_noaa_csv_enhanced(output_file)
                    feature_count = len(parsed_data.get('durations', []))
                    
                    # Validate data quality if requested
                    quality_metrics = {}
                    if self.validate_data_completeness:
                        quality_metrics = self._assess_data_quality(parsed_data)
                    
                    # Create comprehensive metadata
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
                            'units': parsed_data.get('units', 'Unknown'),
                            'encoding_used': encoding
                        },
                        'quality_metrics': quality_metrics
                    }
                    
                    # Generate multiple output formats based on configuration
                    output_files = self._generate_output_formats(
                        parsed_data, metadata, output_path, timestamp, 
                        centroid_lat, centroid_lon
                    )
                    metadata.update(output_files)
                    
                    logger.info(f"Successfully downloaded NOAA depth-duration-frequency data to {output_file}")
                    logger.info(f"Data contains {feature_count} precipitation frequency estimates")
                    
                    file_size = os.path.getsize(output_file) if os.path.exists(output_file) else None
                    return self._create_success_result(
                        layer_id=layer_id,
                        file_path=output_file,
                        feature_count=feature_count,
                        file_size_bytes=file_size,
                        metadata=metadata
                    )
                    
                except Exception as parse_error:
                    logger.error(f"Error parsing downloaded data: {parse_error}")
                    return self._create_error_result(layer_id, f"Error parsing downloaded data: {parse_error}")
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    return self._create_error_result(layer_id, f"Request timed out after {self.max_retries} attempts")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    return self._create_error_result(layer_id, f"Request failed after {self.max_retries} attempts: {e}")
                
            except Exception as e:
                logger.error(f"Unexpected error downloading NOAA Atlas 14 data: {e}")
                return self._create_error_result(layer_id, f"Unexpected error: {e}")
        
        # Should not reach here, but just in case
        return self._create_error_result(layer_id, "Download failed for unknown reason")
    
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
    
    def _detect_encoding(self, content: bytes) -> str:
        """
        Detect the encoding of the response content
        
        Args:
            content: Raw response content as bytes
            
        Returns:
            Detected encoding string, defaults to 'utf-8'
        """
        if not CHARDET_AVAILABLE:
            self.logger.debug("chardet not available, using utf-8 encoding")
            return 'utf-8'
            
        try:
            detected = chardet.detect(content)
            encoding = detected.get('encoding', 'utf-8')
            confidence = detected.get('confidence', 0.0)
            
            self.logger.info(f"Detected encoding: {encoding} (confidence: {confidence:.2f})")
            
            # Fallback to utf-8 if confidence is too low
            if confidence < 0.7:
                self.logger.warning(f"Low confidence in encoding detection, using utf-8")
                return 'utf-8'
            
            return encoding
        except Exception as e:
            self.logger.warning(f"Encoding detection failed: {e}, using utf-8")
            return 'utf-8'

    def _assess_data_quality(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the quality and completeness of parsed precipitation data
        
        Args:
            parsed_data: Dictionary containing parsed NOAA data
            
        Returns:
            Dictionary with quality assessment metrics
        """
        quality_metrics = {
            'completeness_score': 0.0,
            'data_gaps': 0,
            'total_data_points': 0,
            'missing_durations': [],
            'invalid_values': 0,
            'assessment_status': 'unknown'
        }
        
        try:
            durations = parsed_data.get('durations', [])
            estimates = parsed_data.get('estimates', [])
            return_periods = parsed_data.get('return_periods', [])
            
            if not durations or not estimates or not return_periods:
                quality_metrics['assessment_status'] = 'insufficient_data'
                return quality_metrics
            
            total_expected = len(durations) * len(return_periods)
            quality_metrics['total_data_points'] = total_expected
            
            missing_count = 0
            invalid_count = 0
            
            # Check each duration's data
            for i, duration in enumerate(durations):
                if i >= len(estimates):
                    quality_metrics['missing_durations'].append(duration)
                    missing_count += len(return_periods)
                    continue
                
                duration_estimates = estimates[i]
                expected_values = len(return_periods)
                actual_values = len(duration_estimates)
                
                if actual_values < expected_values:
                    missing_count += (expected_values - actual_values)
                
                # Check for invalid values (negative, zero, or extremely high)
                for value in duration_estimates:
                    if isinstance(value, (int, float)):
                        if value <= 0 or value > 100:  # Reasonable range for inches
                            invalid_count += 1
                    else:
                        invalid_count += 1
            
            quality_metrics['data_gaps'] = missing_count
            quality_metrics['invalid_values'] = invalid_count
            
            # Calculate completeness score
            if total_expected > 0:
                valid_points = total_expected - missing_count - invalid_count
                quality_metrics['completeness_score'] = max(0.0, valid_points / total_expected)
            
            # Determine overall assessment
            if quality_metrics['completeness_score'] >= 0.95:
                quality_metrics['assessment_status'] = 'excellent'
            elif quality_metrics['completeness_score'] >= 0.85:
                quality_metrics['assessment_status'] = 'good'
            elif quality_metrics['completeness_score'] >= 0.70:
                quality_metrics['assessment_status'] = 'acceptable'
            else:
                quality_metrics['assessment_status'] = 'poor'
            
            self.logger.info(f"Data quality assessment: {quality_metrics['assessment_status']} "
                           f"(completeness: {quality_metrics['completeness_score']:.1%})")
            
        except Exception as e:
            self.logger.error(f"Error assessing data quality: {e}")
            quality_metrics['assessment_status'] = 'error'
            quality_metrics['error_message'] = str(e)
        
        return quality_metrics

    def _generate_output_formats(self, parsed_data: Dict[str, Any], metadata: Dict[str, Any],
                               output_path: str, timestamp: str, lat: float, lon: float) -> Dict[str, Any]:
        """
        Generate multiple output formats based on configuration
        
        Args:
            parsed_data: Parsed precipitation data
            metadata: Data metadata
            output_path: Output directory path
            timestamp: Timestamp for filenames
            lat: Latitude coordinate
            lon: Longitude coordinate
            
        Returns:
            Dictionary with paths to generated output files
        """
        output_files = {}
        base_filename = f"depth_duration_frequency_{lat:.4f}_{lon:.4f}_{timestamp}"
        
        try:
            # Generate JSON output if requested
            if 'json' in self.output_formats:
                json_file = os.path.join(output_path, f"{base_filename}.json")
                json_data = {
                    'metadata': metadata,
                    'precipitation_data': parsed_data
                }
                
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, default=str)
                
                output_files['json_file'] = json_file
                self.logger.info(f"Generated JSON output: {os.path.basename(json_file)}")
            
            # Generate enhanced CSV if requested
            if 'csv' in self.output_formats:
                processed_file = parsed_data.get('processed_file')
                if processed_file and os.path.exists(processed_file):
                    output_files['enhanced_csv'] = processed_file
            
            # Generate PDF report if requested
            if 'pdf' in self.output_formats:
                processed_file = parsed_data.get('processed_file')
                if processed_file and os.path.exists(processed_file):
                    try:
                        pdf_file = os.path.join(output_path, f"{base_filename}.pdf")
                        
                        # Create temporary metadata file for PDF generation
                        temp_metadata_file = os.path.join(output_path, f"{base_filename}_temp_metadata.json")
                        with open(temp_metadata_file, 'w', encoding='utf-8') as f:
                            json.dump(metadata, f, indent=2, default=str)
                        
                        if generate_precipitation_pdf(processed_file, temp_metadata_file, pdf_file):
                            output_files['pdf_report'] = pdf_file
                            self.logger.info(f"Generated PDF report: {os.path.basename(pdf_file)}")
                        else:
                            self.logger.warning("Failed to generate PDF report")
                        
                        # Clean up temporary metadata file
                        try:
                            os.remove(temp_metadata_file)
                        except:
                            pass
                    
                    except Exception as pdf_error:
                        self.logger.warning(f"PDF generation failed: {pdf_error}")
            
        except Exception as e:
            self.logger.error(f"Error generating output formats: {e}")
        
        return output_files

    def _parse_noaa_csv_enhanced(self, file_path: str) -> Dict[str, Any]:
        """
        Enhanced parsing of NOAA Atlas 14 CSV format with better error handling
        
        Args:
            file_path: Path to the NOAA CSV file
            
        Returns:
            Dictionary containing parsed data and metadata
        """
        try:
            # Try to detect encoding if not UTF-8
            with open(file_path, 'rb') as f:
                raw_content = f.read()
            
            encoding = self._detect_encoding(raw_content)
            
            with open(file_path, 'r', encoding=encoding) as f:
                lines = f.readlines()
            
            return self._parse_csv_content(lines, file_path)
            
        except Exception as e:
            self.logger.error(f"Error in enhanced CSV parsing: {e}")
            # Fallback to original parser
            return self._parse_noaa_csv(file_path)

    def _parse_csv_content(self, lines: List[str], file_path: str) -> Dict[str, Any]:
        """
        Parse the content lines of a NOAA CSV file
        
        Args:
            lines: List of CSV file lines
            file_path: Original file path for processed output
            
        Returns:
            Dictionary containing parsed data
        """
        # Parse metadata from header with enhanced extraction
        metadata = {}
        data_type = "Unknown"
        units = "Unknown"
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("Point precipitation frequency estimates"):
                # Extract units more robustly
                if "(" in line and ")" in line:
                    units_match = line.split("(")[-1].split(")")[0]
                    units = units_match if units_match else "Unknown"
            elif line.startswith("Data type:"):
                data_type = line.split(":", 1)[1].strip()
            elif line.startswith("Time series type:"):
                metadata['time_series_type'] = line.split(":", 1)[1].strip()
            elif line.startswith("Project area:"):
                metadata['project_area'] = line.split(":", 1)[1].strip()
            elif line.startswith("Latitude:"):
                lat_str = line.split(":", 1)[1].strip()
                try:
                    metadata['latitude'] = float(lat_str)
                except ValueError:
                    metadata['latitude'] = lat_str
            elif line.startswith("Longitude:"):
                lon_str = line.split(":", 1)[1].strip()
                try:
                    metadata['longitude'] = float(lon_str)
                except ValueError:
                    metadata['longitude'] = lon_str
            elif line.startswith("Elevation"):
                metadata['elevation'] = line.split(":", 1)[1].strip()
        
        # Find and parse the main data section
        main_data_start = None
        for i, line in enumerate(lines):
            if "by duration for ARI (years):" in line.strip():
                main_data_start = i
                break
        
        if main_data_start is None:
            raise ValueError("Could not find main data section in NOAA CSV")
        
        # Parse return periods from header with enhanced extraction
        header_line = lines[main_data_start].strip()
        return_periods = []
        if "," in header_line:
            parts = header_line.split(",")[1:]
            for part in parts:
                part = part.strip()
                if part.isdigit():
                    return_periods.append(int(part))
                elif part.replace('.', '').isdigit():
                    return_periods.append(float(part))
        
        # Parse precipitation data with enhanced validation
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
                            value = float(part)
                            values.append(value)
                        except ValueError:
                            # Handle non-numeric values
                            if part.lower() in ['n/a', 'na', 'null', '']:
                                values.append(None)
                            else:
                                self.logger.warning(f"Could not parse value '{part}' in duration {duration}")
                                values.append(None)
                
                if duration and values:
                    durations.append(duration)
                    estimates.append(values)
        
        # Create structured result
        result = {
            'metadata': metadata,
            'data_type': data_type,
            'units': units,
            'return_periods': return_periods,
            'durations': durations,
            'estimates': estimates
        }
        
        # Create enhanced DataFrame with better formatting
        if durations and return_periods and estimates:
            df_data = {'Duration': durations}
            for i, rp in enumerate(return_periods):
                col_name = f"{rp}_year"
                df_data[col_name] = [
                    row[i] if i < len(row) and row[i] is not None else None 
                    for row in estimates
                ]
            
            df = pd.DataFrame(df_data)
            
            # Add metadata rows at the top
            metadata_rows = pd.DataFrame({
                'Duration': ['Location', 'Data Type', 'Units', ''],
                **{col: [
                    f"Lat: {metadata.get('latitude', 'N/A')}, Lon: {metadata.get('longitude', 'N/A')}" if col == f"{return_periods[0]}_year" else '',
                    data_type if col == f"{return_periods[0]}_year" else '',
                    units if col == f"{return_periods[0]}_year" else '',
                    ''
                ] for col in df.columns[1:]}
            })
            
            final_df = pd.concat([metadata_rows, df], ignore_index=True)
            
            processed_file = file_path.replace('.csv', '_processed.csv')
            final_df.to_csv(processed_file, index=False)
            result['processed_file'] = processed_file
            
            self.logger.info(f"Created enhanced precipitation frequency table with {len(durations)} durations and {len(return_periods)} return periods")
        
        return result

    def _parse_noaa_csv(self, file_path: str) -> Dict[str, Any]:
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