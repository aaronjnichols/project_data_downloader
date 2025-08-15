"""
CAD Export Functionality for Geospatial Data
============================================

This module provides CAD export capabilities including:
- DXF export for shapefiles and geospatial data
- DWG export (where possible)
- Professional CAD layer organization
- Coordinate system handling for CAD
"""

import ezdxf
from ezdxf import units
from ezdxf.addons import geo
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon
from pathlib import Path
import tempfile
import zipfile
import logging
from typing import List, Dict, Optional, Tuple, Any
import os

logger = logging.getLogger(__name__)


class CADExporter:
    """Handles export of geospatial data to CAD formats"""
    
    def __init__(self):
        self.supported_formats = ['dxf']  # DWG requires additional libraries
        self.layer_styles = {
            'flood_zones': {'color': 1, 'linetype': 'CONTINUOUS'},  # Red
            'elevation': {'color': 3, 'linetype': 'CONTINUOUS'},    # Green
            'contours': {'color': 4, 'linetype': 'CONTINUOUS'},     # Cyan
            'streams': {'color': 5, 'linetype': 'CONTINUOUS'},      # Blue
            'boundaries': {'color': 7, 'linetype': 'DASHED'},       # White/Black
            'default': {'color': 7, 'linetype': 'CONTINUOUS'}       # White/Black
        }
    
    def export_job_to_cad(self, job_id: str, job_dir: Path, output_format: str = 'dxf') -> Optional[Path]:
        """
        Export all geospatial data from a job to CAD format
        
        Args:
            job_id: Job identifier
            job_dir: Directory containing job results
            output_format: CAD format ('dxf' or 'dwg')
            
        Returns:
            Path to created CAD file or None if failed
        """
        try:
            if output_format.lower() not in self.supported_formats:
                logger.error(f"Unsupported CAD format: {output_format}")
                return None
            
            # Create new DXF document
            doc = ezdxf.new('R2010')  # AutoCAD 2010 format for compatibility
            doc.units = units.M  # Set units to meters
            
            msp = doc.modelspace()
            
            # Find all vector data files in the job directory
            vector_files = self._find_vector_files(job_dir)
            
            if not vector_files:
                logger.warning(f"No vector data files found in job {job_id}")
                return None
            
            # Process each vector file
            features_added = 0
            for file_path in vector_files:
                try:
                    features_count = self._add_shapefile_to_cad(doc, msp, file_path)
                    features_added += features_count
                    logger.info(f"Added {features_count} features from {file_path.name}")
                except Exception as e:
                    logger.warning(f"Error processing {file_path}: {e}")
                    continue
            
            if features_added == 0:
                logger.warning(f"No features were added to CAD file for job {job_id}")
                return None
            
            # Add title block and metadata
            self._add_title_block(doc, msp, job_id, features_added)
            
            # Save CAD file
            output_path = job_dir / f"{job_id}_export.{output_format.lower()}"
            doc.saveas(str(output_path))
            
            logger.info(f"Successfully exported {features_added} features to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error exporting job {job_id} to CAD: {e}")
            return None
    
    def _find_vector_files(self, directory: Path) -> List[Path]:
        """Find all vector data files in directory"""
        vector_extensions = ['.shp', '.geojson', '.gpkg']
        vector_files = []
        
        for ext in vector_extensions:
            vector_files.extend(directory.glob(f"*{ext}"))
        
        return vector_files
    
    def _add_shapefile_to_cad(self, doc: ezdxf.document.Drawing, msp: Any, file_path: Path) -> int:
        """
        Add shapefile data to CAD document
        
        Args:
            doc: DXF document
            msp: Model space
            file_path: Path to vector file
            
        Returns:
            Number of features added
        """
        try:
            # Read geospatial data
            gdf = gpd.read_file(file_path)
            
            if gdf.empty:
                return 0
            
            # Reproject to appropriate coordinate system for CAD
            # Convert to a local projected coordinate system if needed
            if gdf.crs and gdf.crs.is_geographic:
                # Find appropriate UTM zone for the data
                centroid = gdf.geometry.centroid.iloc[0]
                utm_crs = self._get_utm_crs(centroid.y, centroid.x)
                gdf = gdf.to_crs(utm_crs)
                logger.info(f"Reprojected {file_path.name} to {utm_crs}")
            
            # Determine layer name and style
            layer_name, layer_style = self._get_layer_info(file_path.name)
            
            # Create CAD layer
            cad_layer = doc.layers.new(name=layer_name)
            cad_layer.color = layer_style['color']
            
            # Add features to CAD
            features_added = 0
            for idx, row in gdf.iterrows():
                try:
                    geometry = row.geometry
                    attributes = row.drop('geometry').to_dict()
                    
                    self._add_geometry_to_cad(msp, geometry, layer_name, attributes)
                    features_added += 1
                    
                except Exception as e:
                    logger.warning(f"Error adding feature {idx} from {file_path.name}: {e}")
                    continue
            
            return features_added
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return 0
    
    def _get_utm_crs(self, lat: float, lon: float) -> str:
        """Get appropriate UTM CRS for given coordinates"""
        # Calculate UTM zone
        zone = int((lon + 180) / 6) + 1
        
        # Determine hemisphere
        if lat >= 0:
            return f"EPSG:{32600 + zone}"  # Northern hemisphere
        else:
            return f"EPSG:{32700 + zone}"  # Southern hemisphere
    
    def _get_layer_info(self, filename: str) -> Tuple[str, Dict]:
        """Determine CAD layer name and style based on filename"""
        filename_lower = filename.lower()
        
        # FEMA flood data
        if 'flood' in filename_lower or 'fema' in filename_lower:
            if 'zone' in filename_lower or 'fld_haz' in filename_lower:
                return 'FLOOD_ZONES', self.layer_styles['flood_zones']
            elif 'bfe' in filename_lower:
                return 'BASE_FLOOD_ELEVATION', self.layer_styles['elevation']
            elif 'stream' in filename_lower or 'xs' in filename_lower:
                return 'STREAMS', self.layer_styles['streams']
            else:
                return 'FLOOD_DATA', self.layer_styles['flood_zones']
        
        # USGS elevation data
        elif 'contour' in filename_lower:
            return 'CONTOURS', self.layer_styles['contours']
        elif 'dem' in filename_lower or 'elevation' in filename_lower:
            return 'ELEVATION', self.layer_styles['elevation']
        
        # NOAA precipitation data
        elif 'noaa' in filename_lower or 'precip' in filename_lower:
            return 'PRECIPITATION', self.layer_styles['default']
        
        # Boundaries and other
        elif 'boundary' in filename_lower or 'aoi' in filename_lower:
            return 'BOUNDARIES', self.layer_styles['boundaries']
        
        else:
            # Use filename as layer name
            layer_name = Path(filename).stem.upper().replace(' ', '_')
            return layer_name, self.layer_styles['default']
    
    def _add_geometry_to_cad(self, msp: Any, geometry: Any, layer: str, attributes: Dict):
        """Add a single geometry to CAD model space"""
        try:
            if isinstance(geometry, Point):
                self._add_point_to_cad(msp, geometry, layer, attributes)
            
            elif isinstance(geometry, LineString):
                self._add_linestring_to_cad(msp, geometry, layer, attributes)
            
            elif isinstance(geometry, Polygon):
                self._add_polygon_to_cad(msp, geometry, layer, attributes)
            
            elif isinstance(geometry, (MultiPoint, MultiLineString, MultiPolygon)):
                # Handle multi-geometries by processing each component
                for geom in geometry.geoms:
                    self._add_geometry_to_cad(msp, geom, layer, attributes)
            
            else:
                logger.warning(f"Unsupported geometry type: {type(geometry)}")
                
        except Exception as e:
            logger.warning(f"Error adding geometry to CAD: {e}")
    
    def _add_point_to_cad(self, msp: Any, point: Point, layer: str, attributes: Dict):
        """Add point geometry to CAD"""
        # Add point as a small circle or block
        msp.add_circle(
            center=(point.x, point.y, 0),
            radius=1.0,  # 1 meter radius
            dxfattribs={'layer': layer}
        )
        
        # Add text label if there are meaningful attributes
        label_text = self._create_label_text(attributes)
        if label_text:
            msp.add_text(
                text=label_text,
                dxfattribs={
                    'layer': layer,
                    'height': 2.0,  # 2 meter text height
                    'insert': (point.x + 2, point.y + 2, 0)
                }
            )
    
    def _add_linestring_to_cad(self, msp: Any, linestring: LineString, layer: str, attributes: Dict):
        """Add linestring geometry to CAD with embedded elevation data"""
        # Extract elevation data first
        elevation = self._extract_elevation_value(attributes)
        
        # Convert coordinates to 3D - use elevation as Z value if available
        if elevation is not None:
            try:
                elev_float = float(elevation)
                coords_3d = [(x, y, elev_float) for x, y in linestring.coords]
            except (ValueError, TypeError):
                coords_3d = [(x, y, 0) for x, y in linestring.coords]
        else:
            coords_3d = [(x, y, 0) for x, y in linestring.coords]
        
        # Create DXF attributes with embedded data
        dxf_attribs = {'layer': layer}
        
        # Add polyline (use POLYLINE for 3D, LWPOLYLINE for 2D)
        if elevation is not None:
            # 3D polyline with elevation
            polyline = msp.add_polyline3d(points=coords_3d, dxfattribs=dxf_attribs)
        else:
            # 2D lightweight polyline
            coords_2d = [(x, y) for x, y in linestring.coords]
            polyline = msp.add_lwpolyline(points=coords_2d, dxfattribs=dxf_attribs)
        
        # Add extended entity data (XData) for elevation and other attributes
        if elevation is not None:
            try:
                self._add_elevation_xdata(polyline, elevation, attributes)
            except Exception as e:
                logger.warning(f"Could not add elevation XData: {e}")
        
        # Add visible text labels for contours
        if 'contour' in layer.lower() and elevation is not None:
            # Add text at multiple points along the line for long contours
            self._add_contour_labels(msp, linestring, elevation, layer)
    
    def _extract_elevation_value(self, attributes: Dict) -> Optional[float]:
        """Extract elevation value from feature attributes"""
        # Try different common elevation attribute names
        elevation_fields = [
            'ELEVATION', 'elevation', 'Elevation',
            'CONTOUR', 'contour', 'Contour', 
            'ELEV', 'elev', 'Elev',
            'Z', 'z', 'HEIGHT', 'height',
            'Value', 'VALUE', 'value'
        ]
        
        for field in elevation_fields:
            if field in attributes and attributes[field] is not None:
                try:
                    value = float(attributes[field])
                    return value
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _add_elevation_xdata(self, entity: Any, elevation: float, attributes: Dict):
        """Add elevation and attribute data as Extended Entity Data (XData)"""
        try:
            # Register application name for XData
            if not hasattr(entity.doc, '_geospatial_xdata_registered'):
                entity.doc.appids.new('GEOSPATIAL')
                entity.doc._geospatial_xdata_registered = True
            
            # Create XData list
            xdata = [
                (1001, 'GEOSPATIAL'),  # Application name
                (1040, elevation),     # Elevation as real number
                (1000, f'ELEVATION={elevation}'),  # Elevation as string
            ]
            
            # Add additional attributes
            for key, value in attributes.items():
                if key.upper() not in ['GEOMETRY'] and value is not None:
                    try:
                        # Try to add as real number first
                        float_val = float(value)
                        xdata.append((1040, float_val))
                    except (ValueError, TypeError):
                        # Add as string
                        str_val = str(value)[:255]  # DXF string length limit
                        if str_val:
                            xdata.append((1000, f'{key}={str_val}'))
            
            # Apply XData to entity
            entity.set_xdata('GEOSPATIAL', xdata)
            
        except Exception as e:
            logger.warning(f"Error adding XData: {e}")
    
    def _add_contour_labels(self, msp: Any, linestring: LineString, elevation: float, layer: str):
        """Add elevation labels along contour lines"""
        try:
            line_length = linestring.length
            
            # Determine label spacing based on line length
            if line_length > 500:  # Long lines (>500m) - label every 200m
                label_interval = 0.4  # 40% along the line
                positions = [0.2, 0.6]  # Multiple labels
            elif line_length > 100:  # Medium lines - label at middle and ends
                positions = [0.25, 0.75]
            else:  # Short lines - single label at middle
                positions = [0.5]
            
            for pos in positions:
                point = linestring.interpolate(pos, normalized=True)
                
                # Add text label
                msp.add_text(
                    text=f'{elevation:.0f}',  # Format elevation (no decimals for contours)
                    dxfattribs={
                        'layer': layer,
                        'height': max(2.0, line_length / 100),  # Scale text size to line length
                        'insert': (point.x, point.y, elevation if elevation else 0),
                        'rotation': self._calculate_text_rotation(linestring, pos)
                    }
                )
                
        except Exception as e:
            logger.warning(f"Error adding contour labels: {e}")
    
    def _calculate_text_rotation(self, linestring: LineString, position: float) -> float:
        """Calculate text rotation to align with contour line direction"""
        try:
            # Get a small segment around the position for direction calculation
            start_pos = max(0, position - 0.05)
            end_pos = min(1, position + 0.05)
            
            start_point = linestring.interpolate(start_pos, normalized=True)
            end_point = linestring.interpolate(end_pos, normalized=True)
            
            # Calculate angle in degrees
            import math
            dx = end_point.x - start_point.x
            dy = end_point.y - start_point.y
            
            if dx == 0 and dy == 0:
                return 0
            
            angle = math.degrees(math.atan2(dy, dx))
            
            # Keep text readable (not upside down)
            if angle > 90:
                angle -= 180
            elif angle < -90:
                angle += 180
                
            return angle
            
        except Exception:
            return 0  # Default to horizontal if calculation fails
    
    def _add_polygon_to_cad(self, msp: Any, polygon: Polygon, layer: str, attributes: Dict):
        """Add polygon geometry to CAD"""
        # Add exterior boundary
        exterior_coords = [(x, y, 0) for x, y in polygon.exterior.coords]
        msp.add_lwpolyline(
            points=exterior_coords,
            close=True,
            dxfattribs={'layer': layer}
        )
        
        # Add interior holes if any
        for interior in polygon.interiors:
            interior_coords = [(x, y, 0) for x, y in interior.coords]
            msp.add_lwpolyline(
                points=interior_coords,
                close=True,
                dxfattribs={'layer': layer}
            )
        
        # Add label at centroid
        label_text = self._create_label_text(attributes)
        if label_text:
            centroid = polygon.centroid
            msp.add_text(
                text=label_text,
                dxfattribs={
                    'layer': layer,
                    'height': 2.0,
                    'insert': (centroid.x, centroid.y, 0)
                }
            )
    
    def _create_label_text(self, attributes: Dict) -> str:
        """Create label text from feature attributes"""
        # Priority attributes for labeling
        priority_attrs = [
            'NAME', 'name', 'Name',
            'LABEL', 'label', 'Label',
            'FLD_ZONE', 'ZONE_SUBTY', 'flood_zone',
            'ELEVATION', 'elevation', 'CONTOUR',
            'OBJECTID', 'FID', 'id'
        ]
        
        for attr in priority_attrs:
            if attr in attributes and attributes[attr] is not None:
                value = str(attributes[attr])
                if value and value != 'nan':
                    return value[:50]  # Limit text length
        
        return ""  # No meaningful label found
    
    def _add_title_block(self, doc: ezdxf.document.Drawing, msp: Any, job_id: str, feature_count: int):
        """Add title block with project information"""
        try:
            # Create title block layer
            title_layer = doc.layers.new(name='TITLE_BLOCK')
            title_layer.color = 7  # White/Black
            
            # Get drawing extents to position title block
            try:
                # This is a simplified approach - in practice you'd calculate actual extents
                x_pos = 0
                y_pos = 0
            except:
                x_pos = 0
                y_pos = 0
            
            # Add title block border (simple rectangle)
            title_width = 200
            title_height = 50
            
            msp.add_lwpolyline([
                (x_pos, y_pos),
                (x_pos + title_width, y_pos),
                (x_pos + title_width, y_pos + title_height),
                (x_pos, y_pos + title_height),
                (x_pos, y_pos)
            ], close=True, dxfattribs={'layer': 'TITLE_BLOCK'})
            
            # Add title text
            msp.add_text(
                'GEOSPATIAL DATA EXPORT',
                dxfattribs={
                    'layer': 'TITLE_BLOCK',
                    'height': 8,
                    'insert': (x_pos + 10, y_pos + 35)
                }
            )
            
            # Add job information
            msp.add_text(
                f'Job ID: {job_id}',
                dxfattribs={
                    'layer': 'TITLE_BLOCK',
                    'height': 4,
                    'insert': (x_pos + 10, y_pos + 25)
                }
            )
            
            msp.add_text(
                f'Features: {feature_count}',
                dxfattribs={
                    'layer': 'TITLE_BLOCK',
                    'height': 4,
                    'insert': (x_pos + 10, y_pos + 18)
                }
            )
            
            # Add coordinate system info
            msp.add_text(
                'Coordinate System: Local Projection',
                dxfattribs={
                    'layer': 'TITLE_BLOCK',
                    'height': 3,
                    'insert': (x_pos + 10, y_pos + 11)
                }
            )
            
            # Add generation date
            from datetime import datetime
            date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
            msp.add_text(
                f'Generated: {date_str}',
                dxfattribs={
                    'layer': 'TITLE_BLOCK',
                    'height': 3,
                    'insert': (x_pos + 10, y_pos + 4)
                }
            )
            
        except Exception as e:
            logger.warning(f"Error adding title block: {e}")


def export_job_to_cad_formats(job_id: str, job_directory: Path) -> Dict[str, Optional[Path]]:
    """
    Export job data to multiple CAD formats
    
    Args:
        job_id: Job identifier
        job_directory: Directory containing job results
        
    Returns:
        Dictionary mapping format names to file paths
    """
    exporter = CADExporter()
    results = {}
    
    # Export to DXF
    try:
        dxf_path = exporter.export_job_to_cad(job_id, job_directory, 'dxf')
        results['dxf'] = dxf_path
        if dxf_path:
            logger.info(f"Successfully exported job {job_id} to DXF: {dxf_path}")
    except Exception as e:
        logger.error(f"Failed to export job {job_id} to DXF: {e}")
        results['dxf'] = None
    
    # Future: Export to DWG (requires additional libraries like ODA File Converter)
    # results['dwg'] = None
    
    return results


def create_cad_export_zip(job_id: str, cad_files: Dict[str, Optional[Path]]) -> Optional[Path]:
    """
    Create a ZIP file containing all CAD exports
    
    Args:
        job_id: Job identifier
        cad_files: Dictionary of CAD format files
        
    Returns:
        Path to ZIP file or None if failed
    """
    try:
        # Filter out None values (failed exports)
        valid_files = {fmt: path for fmt, path in cad_files.items() if path and path.exists()}
        
        if not valid_files:
            logger.warning(f"No valid CAD files to zip for job {job_id}")
            return None
        
        # Create temporary ZIP file
        zip_path = Path(tempfile.gettempdir()) / f"{job_id}_cad_export.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for format_name, file_path in valid_files.items():
                # Add file to ZIP with descriptive name
                zipf.write(file_path, f"{job_id}_export.{format_name}")
                
        logger.info(f"Created CAD export ZIP: {zip_path}")
        return zip_path
        
    except Exception as e:
        logger.error(f"Error creating CAD export ZIP for job {job_id}: {e}")
        return None