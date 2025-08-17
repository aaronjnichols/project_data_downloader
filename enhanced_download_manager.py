"""
Enhanced Download Manager
========================

Improved download functionality with:
- Automatic download initiation
- Real-time progress tracking
- Background file preparation
- Smart notifications
- Download history
"""

import streamlit as st
import time
import requests
import zipfile
import io
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class EnhancedDownloadManager:
    """Enhanced download manager with automatic downloads and better UX"""
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.max_poll_time = 600  # 10 minutes
        self.poll_interval = 2    # 2 seconds
    
    def create_and_monitor_job(self, job_data: Dict) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Create job and monitor progress with enhanced feedback
        
        Args:
            job_data: Job configuration data
            
        Returns:
            Tuple of (success, job_result, error_message)
        """
        try:
            # Create job
            with st.spinner("🚀 Creating download job..."):
                job_response = self.api_client.create_job(job_data)
                job_id = job_response['job_id']
            
            st.success(f"✅ Job created: `{job_id}`")
            
            # Monitor progress with enhanced UI
            return self._monitor_job_with_enhanced_ui(job_id)
            
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            return False, None, f"Failed to create job: {str(e)}"
    
    def _monitor_job_with_enhanced_ui(self, job_id: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Monitor job with enhanced progress UI"""
        st.subheader("📊 Download Progress")
        
        # Create progress containers
        progress_container = st.container()
        status_container = st.container()
        details_container = st.container()
        
        with progress_container:
            # Main progress bar
            main_progress = st.progress(0)
            
            # Status metrics row
            col1, col2, col3, col4 = st.columns(4)
            status_metrics = {
                'elapsed': col1.empty(),
                'estimated': col2.empty(),
                'current_task': col3.empty(),
                'data_size': col4.empty()
            }
            
            # Current status text
            current_status = st.empty()
        
        # Start monitoring
        start_time = time.time()
        attempt = 0
        max_attempts = self.max_poll_time // self.poll_interval
        
        while attempt < max_attempts:
            try:
                # Get job status
                job_status = self.api_client.get_job_status(job_id)
                status = job_status['status']
                
                # Update elapsed time
                elapsed_minutes = (time.time() - start_time) / 60
                status_metrics['elapsed'].metric("⏱️ Elapsed", f"{elapsed_minutes:.1f} min")
                
                # Update progress based on status
                progress_info = self._update_progress_display(
                    status, job_status, main_progress, status_metrics, current_status
                )
                
                # Check for completion
                if status == 'completed':
                    with status_container:
                        self._display_completion_results(job_status)
                    return True, job_status, None
                
                elif status == 'failed':
                    error_msg = job_status.get('error_message', 'Unknown error')
                    current_status.error(f"❌ Job failed: {error_msg}")
                    return False, None, error_msg
                
                # Show detailed progress if available
                if progress_info and attempt % 5 == 0:  # Update details every 10 seconds
                    with details_container:
                        self._display_progress_details(progress_info, job_status)
                
                time.sleep(self.poll_interval)
                attempt += 1
                
            except Exception as e:
                logger.error(f"Error monitoring job: {e}")
                current_status.error(f"❌ Monitoring error: {str(e)}")
                time.sleep(self.poll_interval)
                attempt += 1
        
        # Timeout
        current_status.warning("⏰ Job monitoring timed out. Job may still be running.")
        return False, None, "Monitoring timeout"
    
    def _update_progress_display(self, status: str, job_status: Dict, 
                               progress_bar, metrics: Dict, status_text) -> Optional[Dict]:
        """Update progress display elements"""
        progress_data = job_status.get('progress', {})
        
        if status == 'pending':
            progress_bar.progress(5)
            status_text.info("⏳ Job is queued and waiting to start...")
            metrics['current_task'].metric("📋 Status", "Queued")
            return None
            
        elif status == 'running':
            # Calculate progress percentage
            if 'percentage' in progress_data:
                progress_val = min(progress_data['percentage'] / 100, 0.95)
            else:
                progress_val = 0.3  # Default progress for running jobs
            
            progress_bar.progress(progress_val)
            
            # Update current task
            current_task = progress_data.get('current_task', 'Processing data...')
            status_text.info(f"🔄 {current_task}")
            metrics['current_task'].metric("🎯 Current Task", current_task)
            
            # Estimate remaining time
            if 'percentage' in progress_data and progress_data['percentage'] > 5:
                estimated_total = (time.time() - time.time()) / (progress_data['percentage'] / 100)
                estimated_remaining = estimated_total * (1 - progress_data['percentage'] / 100)
                metrics['estimated'].metric("⏳ Est. Remaining", f"{estimated_remaining/60:.1f} min")
            
            # Show data size if available
            if 'processed_features' in progress_data:
                metrics['data_size'].metric("📊 Features", progress_data['processed_features'])
            
            return progress_data
            
        elif status == 'completed':
            progress_bar.progress(100)
            status_text.success("✅ Download completed successfully!")
            metrics['current_task'].metric("🎯 Status", "Completed")
            return None
        
        return None
    
    def _display_progress_details(self, progress_info: Dict, job_status: Dict):
        """Display detailed progress information"""
        if not progress_info:
            return
        
        st.subheader("📋 Progress Details")
        
        # Create expandable details
        with st.expander("🔍 Technical Details", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                if 'layers_completed' in progress_info:
                    st.metric("Layers Completed", progress_info['layers_completed'])
                if 'current_layer' in progress_info:
                    st.write(f"**Current Layer:** {progress_info['current_layer']}")
            
            with col2:
                if 'processed_features' in progress_info:
                    st.metric("Features Processed", progress_info['processed_features'])
                if 'total_features' in progress_info:
                    st.metric("Total Features", progress_info['total_features'])
            
            # Show any additional progress info
            if 'details' in progress_info:
                st.json(progress_info['details'])
    
    def _display_completion_results(self, job_status: Dict):
        """Display completion results with enhanced download options"""
        result_summary = job_status.get('result_summary')
        if not result_summary:
            st.warning("No result summary available")
            return
        
        st.subheader("🎉 Download Complete!")
        
        # Success metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total Layers", result_summary['total_layers'])
        with col2:
            st.metric("✅ Successful", result_summary['successful_layers'])
        with col3:
            st.metric("❌ Failed", result_summary['failed_layers'])
        with col4:
            st.metric("🗂️ Features", result_summary['total_features'])
        
        # Success rate indicator
        success_rate = result_summary['success_rate'] * 100
        if success_rate == 100:
            st.success(f"🌟 Perfect! All layers downloaded successfully!")
        elif success_rate >= 75:
            st.warning(f"⚠️ Mostly successful ({success_rate:.1f}% completion rate)")
        else:
            st.error(f"❌ Multiple failures ({success_rate:.1f}% completion rate)")
        
        # Enhanced download options
        if result_summary.get('has_download'):
            self._display_enhanced_download_options(job_status)
    
    def _display_enhanced_download_options(self, job_status: Dict):
        """Display enhanced download options with automatic downloads"""
        result_summary = job_status['result_summary']
        job_id = job_status['job_id']
        
        st.subheader("💾 Download Your Data")
        
        # Main download button with automatic download
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Main ZIP download
            self._create_simple_download_button(
                result_summary['download_url'],
                f"{job_id}_geospatial_data.zip",
                "📦 Download Complete Dataset (ZIP)",
                "primary"
            )
        
        with col2:
            # Summary report download
            if 'summary_url' in result_summary:
                self._create_simple_download_button(
                    result_summary['summary_url'],
                    f"{job_id}_summary.json",
                    "📋 Download Report",
                    "secondary"
                )
        
        with col3:
            # Preview button
            if st.button("🔍 Preview Data", help="View a sample of the downloaded data"):
                self._display_data_preview(job_id)
        
        # Additional export options
        with st.expander("🛠️ Additional Export Options"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📐 Export to CAD (DXF)"):
                    self._handle_cad_export(job_id)
            
            with col2:
                if st.button("🗺️ Create Web Map"):
                    self._handle_web_map_export(job_id)
            
            with col3:
                if st.button("📊 Generate Report"):
                    self._handle_report_generation(job_id)
    
    def _create_simple_download_button(self, download_url: str, filename: str, 
                                        label: str, button_type: str = "secondary") -> bool:
        """Create simple download button that shows a link"""
        if st.button(label, type=button_type, help=f"Click to get download link for {filename}"):
            # Generate download link
            full_url = f"{self.api_client.base_url.rstrip('/')}{download_url}"
            
            st.success(f"✅ {filename} is ready!")
            st.markdown(f"""
            **📥 Click the link below to download:**
            
            [**Download {filename}**]({full_url})
            
            *Right-click and "Save As" if the file opens in browser*
            """)
            
            # Also provide direct link as backup
            st.markdown(f"**Direct URL:** `{full_url}`")
            
            return True
        
        return False
    
    def _display_data_preview(self, job_id: str):
        """Display enhanced data preview"""
        try:
            with st.spinner("Loading data preview..."):
                preview_data = self.api_client.get_job_preview(job_id)
            
            if preview_data and preview_data.get('sample_geojson'):
                st.subheader("🔍 Data Preview")
                
                # Preview statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Sample Features", preview_data['feature_count'])
                with col2:
                    st.metric("Total Features", preview_data['total_features'])
                with col3:
                    sample_ratio = preview_data['feature_count'] / max(preview_data['total_features'], 1)
                    st.metric("Sample Ratio", f"{sample_ratio:.1%}")
                
                # Display sample on map
                geojson = preview_data['sample_geojson']
                if geojson.get('features'):
                    # Use the unified map for preview
                    from unified_map import UnifiedMapInterface
                    map_interface = UnifiedMapInterface()
                    
                    # Create preview map
                    preview_map = map_interface.create_unified_map()
                    
                    # Add preview data
                    import folium
                    folium.GeoJson(
                        geojson,
                        style_function=lambda x: {
                            'fillColor': '#00ff00',
                            'color': '#0066cc',
                            'weight': 2,
                            'fillOpacity': 0.4,
                            'opacity': 0.8
                        },
                        popup="Preview Data",
                        tooltip="Downloaded Data Sample"
                    ).add_to(preview_map)
                    
                    # Display preview map
                    st_folium(preview_map, width=700, height=400)
                    
                    # Show feature attributes sample
                    if st.checkbox("📊 Show Feature Attributes"):
                        first_feature = geojson['features'][0]
                        st.json(first_feature.get('properties', {}))
                        
            else:
                st.info("No preview data available for this job")
                
        except Exception as e:
            logger.error(f"Error displaying preview: {e}")
            st.error(f"❌ Error loading preview: {str(e)}")
    
    def _handle_cad_export(self, job_id: str):
        """Handle CAD export functionality"""
        try:
            with st.spinner("Exporting to CAD format..."):
                # Import CAD export functionality
                from cad_export import export_job_to_cad_formats
                
                job_dir = Path(f"output/results/{job_id}")
                if job_dir.exists():
                    cad_files = export_job_to_cad_formats(job_id, job_dir)
                    
                    if cad_files.get('dxf'):
                        # Automatic DXF download
                        with open(cad_files['dxf'], 'rb') as f:
                            st.download_button(
                                label="📐 Download DXF File",
                                data=f.read(),
                                file_name=f"{job_id}_export.dxf",
                                mime="application/dxf"
                            )
                        st.success("✅ CAD export completed!")
                    else:
                        st.error("❌ No vector data available for CAD export")
                else:
                    st.error("❌ Job results not found")
                    
        except Exception as e:
            logger.error(f"CAD export error: {e}")
            st.error(f"❌ CAD export failed: {str(e)}")
    
    def _handle_web_map_export(self, job_id: str):
        """Handle web map export"""
        st.info("🗺️ Web map export feature coming soon!")
        # TODO: Implement web map export
    
    def _handle_report_generation(self, job_id: str):
        """Handle report generation"""
        st.info("📊 Custom report generation feature coming soon!")
        # TODO: Implement custom report generation


def create_enhanced_download_experience(api_client, job_data: Dict) -> bool:
    """
    Create enhanced download experience with automatic progress monitoring
    
    Args:
        api_client: API client instance
        job_data: Job configuration data
        
    Returns:
        bool: Success status
    """
    download_manager = EnhancedDownloadManager(api_client)
    success, result, error = download_manager.create_and_monitor_job(job_data)
    
    if not success and error:
        st.error(f"❌ Download failed: {error}")
    
    return success