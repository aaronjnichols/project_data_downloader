"""
Settings Manager
===============

Handles user preferences, smart defaults, and settings persistence.
"""

import streamlit as st
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class UserPreferences:
    """User preference settings"""
    # Map preferences
    default_map_mode: str = "view"
    default_tile_layer: str = "OpenStreetMap"
    default_zoom: int = 4
    
    # Data preferences
    preferred_data_sources: List[str] = None
    last_used_layers: Dict[str, List[str]] = None
    favorite_presets: List[str] = None
    
    # Download preferences
    auto_generate_contours: bool = False
    default_contour_interval: int = 5
    preferred_download_format: str = "shapefile"
    
    # UI preferences
    show_advanced_options: bool = False
    remember_aoi: bool = True
    show_tutorials: bool = True
    
    def __post_init__(self):
        if self.preferred_data_sources is None:
            self.preferred_data_sources = []
        if self.last_used_layers is None:
            self.last_used_layers = {}
        if self.favorite_presets is None:
            self.favorite_presets = []


class SettingsManager:
    """Manages user settings and smart defaults"""
    
    def __init__(self):
        self.settings_file = Path("user_settings.json")
        self.session_key = "user_preferences"
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from file and session state"""
        # Load from file if exists
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    settings_dict = json.load(f)
                    preferences = UserPreferences(**settings_dict)
            except Exception as e:
                logger.warning(f"Error loading settings: {e}")
                preferences = UserPreferences()
        else:
            preferences = UserPreferences()
        
        # Store in session state
        if self.session_key not in st.session_state:
            st.session_state[self.session_key] = preferences
    
    def save_settings(self):
        """Save current settings to file"""
        try:
            preferences = st.session_state.get(self.session_key, UserPreferences())
            settings_dict = asdict(preferences)
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings_dict, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
    
    def get_preferences(self) -> UserPreferences:
        """Get current user preferences"""
        return st.session_state.get(self.session_key, UserPreferences())
    
    def update_preference(self, key: str, value: Any):
        """Update a specific preference"""
        preferences = self.get_preferences()
        if hasattr(preferences, key):
            setattr(preferences, key, value)
            st.session_state[self.session_key] = preferences
            self.save_settings()
    
    def add_to_recent_sources(self, source_id: str):
        """Add source to recently used list"""
        preferences = self.get_preferences()
        if source_id not in preferences.preferred_data_sources:
            preferences.preferred_data_sources.insert(0, source_id)
            # Keep only last 5
            preferences.preferred_data_sources = preferences.preferred_data_sources[:5]
            st.session_state[self.session_key] = preferences
            self.save_settings()
    
    def update_last_used_layers(self, source_id: str, layer_ids: List[str]):
        """Update last used layers for a source"""
        preferences = self.get_preferences()
        preferences.last_used_layers[source_id] = layer_ids
        st.session_state[self.session_key] = preferences
        self.save_settings()
    
    def get_smart_defaults(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get smart defaults based on context and user history"""
        preferences = self.get_preferences()
        defaults = {}
        
        # AOI-based recommendations
        if 'aoi_area_km2' in context:
            area = context['aoi_area_km2']
            if area < 1:  # Small area
                defaults['recommended_sources'] = ['usgs_lidar', 'fema']
                defaults['suggested_layers'] = {
                    'usgs_lidar': ['DEM'],
                    'fema': ['S_FLD_HAZ_AR']
                }
            elif area < 100:  # Medium area
                defaults['recommended_sources'] = ['fema', 'noaa_atlas14']
                defaults['suggested_layers'] = {
                    'fema': ['S_FLD_HAZ_AR', 'S_BFE'],
                    'noaa_atlas14': ['24hr_100yr']
                }
            else:  # Large area
                defaults['recommended_sources'] = ['fema']
                defaults['suggested_layers'] = {
                    'fema': ['S_FLD_HAZ_AR']
                }
        
        # Location-based recommendations
        if 'aoi_center' in context:
            lat, lon = context['aoi_center']
            if 25 <= lat <= 50 and -125 <= lon <= -65:  # Continental US
                defaults['tile_layer'] = 'Topographic'
                defaults['show_usgs_data'] = True
        
        # User history-based defaults
        if preferences.preferred_data_sources:
            defaults['default_source'] = preferences.preferred_data_sources[0]
        
        if preferences.last_used_layers:
            defaults['recent_layers'] = preferences.last_used_layers
        
        return defaults
    
    def display_settings_panel(self):
        """Display settings configuration panel"""
        st.subheader("⚙️ User Preferences")
        
        preferences = self.get_preferences()
        
        with st.expander("🗺️ Map Settings", expanded=False):
            # Map preferences
            new_map_mode = st.selectbox(
                "Default Map Mode",
                ["view", "draw"],
                index=0 if preferences.default_map_mode == "view" else 1,
                help="Default mode when opening the map"
            )
            
            new_tile_layer = st.selectbox(
                "Default Tile Layer",
                ["OpenStreetMap", "Satellite", "Topographic", "Terrain"],
                index=["OpenStreetMap", "Satellite", "Topographic", "Terrain"].index(preferences.default_tile_layer),
                help="Default background map layer"
            )
            
            new_zoom = st.slider(
                "Default Zoom Level",
                min_value=1,
                max_value=15,
                value=preferences.default_zoom,
                help="Default zoom level for new maps"
            )
        
        with st.expander("📊 Data Preferences", expanded=False):
            # Data preferences
            new_auto_contours = st.checkbox(
                "Auto-generate contours for elevation data",
                value=preferences.auto_generate_contours,
                help="Automatically generate contour lines when downloading DEM data"
            )
            
            if new_auto_contours:
                new_contour_interval = st.slider(
                    "Default Contour Interval (feet)",
                    min_value=1,
                    max_value=50,
                    value=preferences.default_contour_interval,
                    help="Default spacing between contour lines"
                )
            else:
                new_contour_interval = preferences.default_contour_interval
            
            new_download_format = st.selectbox(
                "Preferred Download Format",
                ["shapefile", "geojson", "kml"],
                index=["shapefile", "geojson", "kml"].index(preferences.preferred_download_format),
                help="Default format for downloaded data"
            )
        
        with st.expander("🎛️ Interface Settings", expanded=False):
            # UI preferences
            new_show_advanced = st.checkbox(
                "Show advanced options by default",
                value=preferences.show_advanced_options,
                help="Display advanced configuration options without expanding"
            )
            
            new_remember_aoi = st.checkbox(
                "Remember AOI between sessions",
                value=preferences.remember_aoi,
                help="Keep your area of interest when you return"
            )
            
            new_show_tutorials = st.checkbox(
                "Show tutorial hints",
                value=preferences.show_tutorials,
                help="Display helpful tips and tutorials"
            )
        
        # Update preferences
        updated_preferences = UserPreferences(
            default_map_mode=new_map_mode,
            default_tile_layer=new_tile_layer,
            default_zoom=new_zoom,
            auto_generate_contours=new_auto_contours,
            default_contour_interval=new_contour_interval,
            preferred_download_format=new_download_format,
            show_advanced_options=new_show_advanced,
            remember_aoi=new_remember_aoi,
            show_tutorials=new_show_tutorials,
            preferred_data_sources=preferences.preferred_data_sources,
            last_used_layers=preferences.last_used_layers,
            favorite_presets=preferences.favorite_presets
        )
        
        # Save button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("💾 Save Settings"):
                st.session_state[self.session_key] = updated_preferences
                self.save_settings()
                st.success("✅ Settings saved!")
        
        with col2:
            if st.button("🔄 Reset to Defaults"):
                st.session_state[self.session_key] = UserPreferences()
                self.save_settings()
                st.success("✅ Settings reset to defaults!")
                st.rerun()
        
        with col3:
            if st.button("📤 Export Settings"):
                settings_json = json.dumps(asdict(updated_preferences), indent=2)
                st.download_button(
                    label="📥 Download Settings File",
                    data=settings_json,
                    file_name="geospatial_downloader_settings.json",
                    mime="application/json"
                )
        
        # Display current usage statistics
        self._display_usage_stats()
    
    def _display_usage_stats(self):
        """Display usage statistics"""
        preferences = self.get_preferences()
        
        st.subheader("📈 Usage Statistics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Recently Used Data Sources:**")
            if preferences.preferred_data_sources:
                for i, source in enumerate(preferences.preferred_data_sources[:3], 1):
                    st.write(f"{i}. {source}")
            else:
                st.write("No recent sources")
        
        with col2:
            st.write("**Layer Usage:**")
            if preferences.last_used_layers:
                total_layers = sum(len(layers) for layers in preferences.last_used_layers.values())
                st.metric("Total Layers Used", total_layers)
                st.metric("Sources Used", len(preferences.last_used_layers))
            else:
                st.write("No layer usage data")


class SmartDefaults:
    """Provides intelligent defaults based on context and user behavior"""
    
    def __init__(self, settings_manager: SettingsManager):
        self.settings_manager = settings_manager
    
    def suggest_data_sources(self, aoi_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest appropriate data sources based on AOI context"""
        suggestions = []
        
        area_km2 = aoi_context.get('area_km2', 0)
        center = aoi_context.get('center', {})
        
        # Area-based suggestions
        if area_km2 < 1:  # Small area - detailed data
            suggestions.append({
                'source_id': 'usgs_lidar',
                'reason': 'High-resolution elevation data recommended for small areas',
                'confidence': 0.9,
                'layers': ['DEM']
            })
        
        if area_km2 < 100:  # Medium area - flood risk analysis
            suggestions.append({
                'source_id': 'fema',
                'reason': 'Flood hazard mapping for detailed analysis',
                'confidence': 0.8,
                'layers': ['S_FLD_HAZ_AR', 'S_BFE']
            })
        
        # Location-based suggestions (if in US)
        lat = center.get('lat', 0)
        lon = center.get('lon', 0)
        
        if 25 <= lat <= 50 and -125 <= lon <= -65:  # Continental US
            suggestions.append({
                'source_id': 'noaa_atlas14',
                'reason': 'Precipitation data available for US locations',
                'confidence': 0.7,
                'layers': ['24hr_100yr']
            })
        
        # User history-based suggestions
        preferences = self.settings_manager.get_preferences()
        for source in preferences.preferred_data_sources[:2]:
            if not any(s['source_id'] == source for s in suggestions):
                suggestions.append({
                    'source_id': source,
                    'reason': 'Based on your recent usage',
                    'confidence': 0.6,
                    'layers': preferences.last_used_layers.get(source, [])
                })
        
        return sorted(suggestions, key=lambda x: x['confidence'], reverse=True)
    
    def get_recommended_layers(self, source_id: str, aoi_context: Dict[str, Any]) -> List[str]:
        """Get recommended layers for a specific source"""
        preferences = self.settings_manager.get_preferences()
        
        # Check user history first
        if source_id in preferences.last_used_layers:
            return preferences.last_used_layers[source_id]
        
        # Default recommendations based on source and context
        area_km2 = aoi_context.get('area_km2', 0)
        
        if source_id == 'fema':
            if area_km2 < 10:
                return ['S_FLD_HAZ_AR', 'S_BFE', 'S_FIRM_PAN']
            else:
                return ['S_FLD_HAZ_AR']
        
        elif source_id == 'usgs_lidar':
            return ['DEM']
        
        elif source_id == 'noaa_atlas14':
            return ['24hr_100yr']
        
        return []


# Global settings manager instance
settings_manager = SettingsManager()
smart_defaults = SmartDefaults(settings_manager)