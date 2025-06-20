#!/usr/bin/env python3
"""
Multi-Source Geospatial Data Downloader
Main entry point for the application.
"""
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import yaml
from core.aoi_manager import AOIManager
from core.data_processor import DataProcessor
from core.base_downloader import DownloadResult
from downloaders import get_downloader, list_downloaders


def setup_logging(config: Dict) -> None:
    """Setup logging configuration"""
    log_config = config.get('logging', {})
    
    level = getattr(logging, log_config.get('level', 'INFO').upper())
    format_str = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[]
    )
    
    logger = logging.getLogger()
    
    # Console handler
    if log_config.get('console_logging', True):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(format_str))
        logger.addHandler(console_handler)
    
    # File handler
    if log_config.get('file_logging', False):
        log_file = log_config.get('log_file_name', 'downloader.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(format_str))
        logger.addHandler(file_handler)


def load_config(config_path: str) -> Dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)


def load_project_config(project_config_path: str) -> Dict:
    """Load project-specific configuration"""
    try:
        with open(project_config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading project configuration: {e}")
        sys.exit(1)


def list_available_layers(source_name: str = None) -> None:
    """List available layers for data sources"""
    print("AVAILABLE DATA SOURCES AND LAYERS")
    print("=" * 50)
    
    downloaders = list_downloaders()
    
    if source_name:
        if source_name not in downloaders:
            print(f"Unknown data source: {source_name}")
            print(f"Available sources: {', '.join(downloaders.keys())}")
            return
        sources_to_show = {source_name: downloaders[source_name]}
    else:
        sources_to_show = downloaders
    
    for name, downloader_class in sources_to_show.items():
        try:
            downloader = downloader_class()
            print(f"\n{downloader.source_name}")
            print("-" * len(downloader.source_name))
            print(f"Description: {downloader.source_description}")
            
            layers = downloader.get_available_layers()
            print(f"Available layers: {len(layers)}")
            
            for layer_id, layer_info in layers.items():
                print(f"  {layer_id}: {layer_info.description} ({layer_info.geometry_type})")
                
        except Exception as e:
            print(f"Error listing layers for {name}: {e}")


def run_download(project_config: Dict, global_config: Dict, dry_run: bool = False,
                sources_filter: List[str] = None) -> bool:
    """Run the download process"""
    
    logger = logging.getLogger(__name__)
    logger.info("Starting multi-source geospatial data download")
    
    # Load AOI
    aoi_manager = AOIManager()
    aoi_file = project_config['project']['aoi_file']
    
    if not aoi_manager.load_aoi_from_file(aoi_file):
        logger.error(f"Failed to load AOI from {aoi_file}")
        return False
    
    if not aoi_manager.validate_aoi():
        logger.error("AOI validation failed")
        return False
    
    # Setup data processor and output structure
    output_dir = project_config['project'].get('output_directory', './output')
    processor = DataProcessor(output_dir)
    output_structure = processor.create_output_structure(
        project_config['project'].get('name')
    )
    
    # Get AOI bounds
    aoi_bounds = aoi_manager.get_bounds()
    
    # Process each enabled data source
    all_results = []
    
    data_sources = project_config.get('data_sources', {})
    
    for source_name, source_config in data_sources.items():
        if not source_config.get('enabled', False):
            logger.info(f"Skipping disabled source: {source_name}")
            continue
            
        if sources_filter and source_name not in sources_filter:
            logger.info(f"Skipping filtered source: {source_name}")
            continue
        
        logger.info(f"Processing data source: {source_name}")
        
        try:
            # Get downloader for this source
            downloader_class = get_downloader(source_name)
            downloader = downloader_class(source_config.get('config', {}))
            
            # Get layers to download
            available_layers = downloader.get_available_layers()
            layers_to_download = source_config.get('layers', 'all')
            
            if layers_to_download == 'all':
                target_layers = list(available_layers.keys())
            else:
                target_layers = layers_to_download
            
            # Download each layer
            source_output_dir = output_structure.get(source_name, output_structure['base'])
            
            for layer_id in target_layers:
                if layer_id not in available_layers:
                    logger.warning(f"Unknown layer {layer_id} for source {source_name}")
                    continue
                
                layer_info = available_layers[layer_id]
                logger.info(f"Downloading layer {layer_id}: {layer_info.description}")
                
                if dry_run:
                    logger.info(f"DRY RUN: Would download {layer_info.description}")
                    continue
                
                # Download the layer
                result = downloader.download_layer(
                    layer_id=layer_id,
                    aoi_bounds=aoi_bounds,
                    output_path=str(source_output_dir),
                    aoi_gdf=aoi_manager.aoi_gdf
                )
                
                all_results.append(result)
                
                if result.success:
                    logger.info(f"✓ Successfully downloaded {layer_info.description}")
                    logger.info(f"  Features: {result.feature_count}")
                    logger.info(f"  File: {result.file_path}")
                    
                    # Check for additional generated files (like PDF reports)
                    if hasattr(result, 'metadata') and result.metadata:
                        # Check for processed CSV
                        processed_csv = result.file_path.replace('.csv', '_processed.csv')
                        if os.path.exists(processed_csv):
                            logger.info(f"  Processed CSV: {os.path.basename(processed_csv)}")
                        
                        # Check for PDF report
                        pdf_report = result.file_path.replace('.csv', '_report.pdf')
                        if os.path.exists(pdf_report):
                            file_size = os.path.getsize(pdf_report) / 1024
                            logger.info(f"  📊 PDF Report: {os.path.basename(pdf_report)} ({file_size:.1f} KB)")
                        
                        # Check for metadata
                        metadata_file = result.file_path.replace('.csv', '_metadata.json')
                        if os.path.exists(metadata_file):
                            logger.info(f"  Metadata: {os.path.basename(metadata_file)}")
                else:
                    logger.error(f"✗ Failed to download {layer_info.description}: {result.error_message}")
        
        except Exception as e:
            logger.error(f"Error processing source {source_name}: {e}")
    
    if not dry_run:
        # Generate summary report
        summary_file = processor.generate_download_summary(
            all_results, output_structure, aoi_manager
        )
        
        # Print final summary
        successful = sum(1 for r in all_results if r.success)
        total = len(all_results)
        total_features = sum(r.feature_count for r in all_results if r.success and r.feature_count)
        
        logger.info(f"\nDOWNLOAD COMPLETE!")
        logger.info(f"Success rate: {successful}/{total} layers")
        logger.info(f"Total features downloaded: {total_features:,}")
        logger.info(f"Output directory: {output_structure['base']}")
        logger.info(f"Summary report: {summary_file}")
    
    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Multi-Source Geospatial Data Downloader',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all configured sources
  python main.py --project my_project.yaml
  
  # Download only FEMA data
  python main.py --project my_project.yaml --sources fema
  
  # List available layers for FEMA
  python main.py --list-layers fema
  
  # Dry run (preview what would be downloaded)
  python main.py --project my_project.yaml --dry-run
        """
    )
    
    parser.add_argument('--project', '-p', type=str,
                       help='Path to project configuration file')
    parser.add_argument('--config', '-c', type=str, default='config/settings.yaml',
                       help='Path to global configuration file')
    parser.add_argument('--list-layers', '-l', type=str, nargs='?', const='all',
                       help='List available layers (optionally for specific source)')
    parser.add_argument('--sources', '-s', type=str, nargs='+',
                       help='Specific data sources to download')
    parser.add_argument('--dry-run', '-d', action='store_true',
                       help='Preview what would be downloaded without actually downloading')
    
    args = parser.parse_args()
    
    # Load global configuration
    global_config = load_config(args.config)
    setup_logging(global_config)
    
    # Handle list layers command
    if args.list_layers:
        source = None if args.list_layers == 'all' else args.list_layers
        list_available_layers(source)
        return
    
    # Require project configuration for download operations
    if not args.project:
        parser.error("Project configuration file is required for download operations")
    
    if not os.path.exists(args.project):
        print(f"Error: Project configuration file not found: {args.project}")
        sys.exit(1)
    
    # Load project configuration
    project_config = load_project_config(args.project)
    
    # Run the download process
    success = run_download(
        project_config=project_config,
        global_config=global_config,
        dry_run=args.dry_run,
        sources_filter=args.sources
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main() 