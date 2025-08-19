"""
Enhanced Data Source Selection Interface
=======================================

Improved data source and layer selection with:
- Categorized data sources
- Layer previews and thumbnails
- Quick preset selections
- Search and filtering
- Smart recommendations
"""

import streamlit as st
from typing import Dict, List, Optional, Tuple, Any
import json
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DataSourceCategory:
    """Data source category information"""
    name: str
    description: str
    icon: str
    color: str


@dataclass
class LayerPreset:
    """Predefined layer combination"""
    name: str
    description: str
    sources: Dict[str, List[str]]  # source_id -> layer_ids
    icon: str


class EnhancedDataSelection:
    """Enhanced data source selection interface"""
    
    def __init__(self):
        self.categories = self._define_categories()
        self.presets = self._define_presets()
    
    def _define_categories(self) -> Dict[str, DataSourceCategory]:
        """Define data source categories"""
        return {
            'flood_risk': DataSourceCategory(
                name="Flood Risk & Hazards",
                description="FEMA flood zones, hazard areas, and flood insurance data",
                icon="🌊",
                color="#1f77b4"
            ),
            'elevation': DataSourceCategory(
                name="Elevation & Terrain",
                description="Digital elevation models, contours, and terrain analysis",
                icon="⛰️",
                color="#ff7f0e"
            ),
            'climate': DataSourceCategory(
                name="Climate & Weather",
                description="Precipitation, temperature, and climate data",
                icon="🌡️",
                color="#2ca02c"
            ),
            'infrastructure': DataSourceCategory(
                name="Infrastructure",
                description="Transportation, utilities, and built environment",
                icon="🏗️",
                color="#d62728"
            ),
            'boundaries': DataSourceCategory(
                name="Boundaries & Admin",
                description="Political boundaries, jurisdictions, and administrative areas",
                icon="🗺️",
                color="#9467bd"
            )
        }
    
    def _define_presets(self) -> List[LayerPreset]:
        """Define common layer combinations"""
        return [
            LayerPreset(
                name="Flood Risk Analysis",
                description="Complete flood hazard assessment package",
                sources={
                    'fema': ['S_FLD_HAZ_AR', 'S_BFE', 'S_FIRM_PAN', 'S_PLSS_AR']
                },
                icon="🌊"
            ),
            LayerPreset(
                name="Elevation Package",
                description="DEM with contours for terrain analysis",
                sources={
                    'usgs_lidar': ['DEM']
                },
                icon="⛰️"
            ),
            LayerPreset(
                name="Precipitation Analysis",
                description="Rainfall frequency and intensity data",
                sources={
                    'noaa_atlas14': ['24hr_010yr', '24hr_025yr', '24hr_050yr', '24hr_100yr']
                },
                icon="🌧️"
            ),
            LayerPreset(
                name="Complete Site Analysis",
                description="Flood risk, elevation, and precipitation data",
                sources={
                    'fema': ['S_FLD_HAZ_AR', 'S_BFE'],
                    'usgs_lidar': ['DEM'],
                    'noaa_atlas14': ['24hr_100yr']
                },
                icon="📊"
            )
        ]
    
    def categorize_sources(self, sources: Dict) -> Dict[str, List[Dict]]:
        """Categorize data sources by type"""
        categorized = {cat_id: [] for cat_id in self.categories.keys()}
        categorized['other'] = []
        
        for source_id, source_info in sources.items():
            if not source_info:
                continue
                
            # Simple categorization based on source ID and description
            category = self._determine_category(source_id, source_info)
            
            if category in categorized:
                categorized[category].append({
                    'id': source_id,
                    'info': source_info
                })
            else:
                categorized['other'].append({
                    'id': source_id,
                    'info': source_info
                })
        
        # Remove empty categories
        return {k: v for k, v in categorized.items() if v}
    
    def _determine_category(self, source_id: str, source_info: Dict) -> str:
        """Determine category for a data source"""
        source_lower = source_id.lower()
        desc_lower = source_info.get('description', '').lower()
        
        if 'fema' in source_lower or 'flood' in desc_lower or 'hazard' in desc_lower:
            return 'flood_risk'
        elif 'usgs' in source_lower or 'lidar' in source_lower or 'elevation' in desc_lower or 'dem' in desc_lower:
            return 'elevation'
        elif 'noaa' in source_lower or 'precipitation' in desc_lower or 'climate' in desc_lower:
            return 'climate'
        elif 'transport' in desc_lower or 'infrastructure' in desc_lower:
            return 'infrastructure'
        elif 'boundary' in desc_lower or 'admin' in desc_lower:
            return 'boundaries'
        else:
            return 'other'
    
    def display_selection_interface(self, sources: Dict) -> Tuple[Optional[str], Optional[List[str]], Dict]:
        """
        Display enhanced data source selection interface
        
        Returns:
            Tuple of (source_id, layer_ids, config_options)
        """
        st.subheader("📊 Data Source Selection")
        
        if not sources:
            st.warning("No data sources available. Please check API connection.")
            return None, None, {}
        
        # Create tabs for different selection methods
        tab1, tab2, tab3 = st.tabs(["🎯 Quick Presets", "📂 Browse by Category", "🔍 Advanced Search"])
        
        with tab1:
            selected_preset = self._display_presets()
            if selected_preset:
                return self._handle_preset_selection(selected_preset, sources)
        
        with tab2:
            return self._display_categorized_selection(sources)
        
        with tab3:
            return self._display_search_interface(sources)
        
        return None, None, {}
    
    def _display_presets(self) -> Optional[LayerPreset]:
        """Display quick preset selections"""
        st.write("**Choose from common data combinations:**")
        
        # Display presets in a grid
        cols = st.columns(2)
        
        for i, preset in enumerate(self.presets):
            with cols[i % 2]:
                with st.container():
                    st.markdown(f"""
                    <div style="border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 8px 0;">
                        <h4>{preset.icon} {preset.name}</h4>
                        <p style="color: #666; margin: 8px 0;">{preset.description}</p>
                        <small style="color: #888;">Sources: {', '.join(preset.sources.keys())}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Select {preset.name}", key=f"preset_{i}"):
                        return preset
        
        return None
    
    def _display_categorized_selection(self, sources: Dict) -> Tuple[Optional[str], Optional[List[str]], Dict]:
        """Display categorized data source selection"""
        categorized = self.categorize_sources(sources)
        
        if not categorized:
            st.warning("No categorized sources available")
            return None, None, {}
        
        # Category selection
        selected_category = st.selectbox(
            "Select Data Category",
            options=list(categorized.keys()),
            format_func=lambda x: f"{self.categories.get(x, DataSourceCategory('Other', '', '📁', '#666')).icon} {self.categories.get(x, DataSourceCategory('Other', 'Other data sources', '📁', '#666')).name}",
            help="Choose the type of data you need"
        )
        
        if not selected_category or not categorized[selected_category]:
            return None, None, {}
        
        # Display category info
        if selected_category in self.categories:
            category = self.categories[selected_category]
            st.info(f"{category.icon} **{category.name}**: {category.description}")
        
        # Source selection within category
        category_sources = categorized[selected_category]
        
        if len(category_sources) == 1:
            # Auto-select if only one source in category
            selected_source = category_sources[0]
        else:
            source_options = {f"{src['info']['name']} ({src['id']})": src for src in category_sources}
            selected_name = st.selectbox(
                "Select Data Source",
                options=list(source_options.keys()),
                help="Choose the specific data source"
            )
            selected_source = source_options[selected_name]
        
        return self._display_layer_selection(selected_source['id'], selected_source['info'])
    
    def _display_search_interface(self, sources: Dict) -> Tuple[Optional[str], Optional[List[str]], Dict]:
        """Display search and filter interface"""
        # Search box
        search_term = st.text_input(
            "🔍 Search data sources and layers",
            placeholder="Enter keywords like 'flood', 'elevation', 'precipitation'..."
        )
        
        if not search_term:
            st.info("Enter a search term to find relevant data sources and layers")
            return None, None, {}
        
        # Search through sources and layers
        search_results = self._search_sources_and_layers(sources, search_term.lower())
        
        if not search_results:
            st.warning(f"No results found for '{search_term}'")
            return None, None, {}
        
        st.write(f"**Found {len(search_results)} matching sources:**")
        
        # Display search results
        for i, result in enumerate(search_results):
            with st.expander(f"{result['source_info']['name']} - {len(result['matching_layers'])} matching layers"):
                st.write(f"**Description:** {result['source_info']['description']}")
                st.write(f"**Matching layers:** {', '.join([layer['name'] for layer in result['matching_layers']])}")
                
                if st.button(f"Select {result['source_info']['name']}", key=f"search_result_{i}"):
                    # Pre-select matching layers
                    matching_layer_ids = [layer['id'] for layer in result['matching_layers']]
                    return result['source_id'], matching_layer_ids, {}
        
        return None, None, {}
    
    def _search_sources_and_layers(self, sources: Dict, search_term: str) -> List[Dict]:
        """Search through sources and layers"""
        results = []
        
        for source_id, source_info in sources.items():
            if not source_info:
                continue
            
            matching_layers = []
            
            # Search in source name and description
            source_match = (search_term in source_info.get('name', '').lower() or 
                           search_term in source_info.get('description', '').lower())
            
            # Search in layers
            for layer_id, layer_info in source_info.get('layers', {}).items():
                layer_match = (search_term in layer_info.get('name', '').lower() or
                              search_term in layer_info.get('description', '').lower() or
                              search_term in layer_id.lower())
                
                if layer_match:
                    matching_layers.append({
                        'id': layer_id,
                        'name': layer_info.get('name', layer_id),
                        'description': layer_info.get('description', '')
                    })
            
            # Include source if it matches or has matching layers
            if source_match or matching_layers:
                results.append({
                    'source_id': source_id,
                    'source_info': source_info,
                    'matching_layers': matching_layers,
                    'source_match': source_match
                })
        
        # Sort by relevance (source matches first, then by number of matching layers)
        results.sort(key=lambda x: (not x['source_match'], -len(x['matching_layers'])))
        
        return results
    
    def _display_layer_selection(self, source_id: str, source_info: Dict) -> Tuple[Optional[str], Optional[List[str]], Dict]:
        """Display enhanced layer selection for a source"""
        layers = source_info.get('layers', {})
        
        if not layers:
            st.warning("No layers available for this source")
            return None, None, {}
        
        st.write(f"**{source_info['name']}**")
        st.write(source_info['description'])
        
        # Quick select all option
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**Select layers** ({len(layers)} available):")
        with col2:
            if st.button("Select All", key=f"select_all_{source_id}"):
                st.session_state[f"layers_{source_id}"] = list(layers.keys())
        
        # Layer selection with enhanced display
        selected_layers = []
        
        # Group layers if many available
        if len(layers) > 8:
            # Use multiselect for many layers
            layer_options = {f"{layer_info['name']} ({layer_id})": layer_id 
                           for layer_id, layer_info in layers.items()}
            
            selected_names = st.multiselect(
                "Choose layers",
                options=list(layer_options.keys()),
                default=st.session_state.get(f"layers_{source_id}", []),
                help="Select one or more layers to download"
            )
            
            selected_layers = [layer_options[name] for name in selected_names]
        else:
            # Use checkboxes for fewer layers
            for layer_id, layer_info in layers.items():
                col1, col2 = st.columns([1, 4])
                
                with col1:
                    selected = st.checkbox(
                        "",
                        key=f"layer_{source_id}_{layer_id}",
                        value=layer_id in st.session_state.get(f"layers_{source_id}", [])
                    )
                
                with col2:
                    if selected:
                        selected_layers.append(layer_id)
                    
                    # Enhanced layer display
                    st.markdown(f"""
                    **{layer_info['name']}**  
                    *{layer_info['description']}*  
                    `{layer_info.get('geometry_type', 'Unknown')}` | `{layer_info.get('data_type', 'Unknown')}`
                    """)
        
        # Source-specific configuration
        config_options = {}
        if source_id == 'usgs_lidar' and selected_layers:
            config_options = self._display_usgs_options()
        
        if selected_layers:
            st.success(f"✅ Selected {len(selected_layers)} layers from {source_info['name']}")
            return source_id, selected_layers, config_options
        
        return source_id, None, config_options
    
    def _display_usgs_options(self) -> Dict:
        """Display USGS-specific configuration options"""
        st.subheader("⛰️ Elevation Data Options")
        
        config = {}
        
        generate_contours = st.checkbox(
            "Generate Contour Lines",
            value=False,
            help="Create contour line shapefiles from DEM data"
        )
        
        if generate_contours:
            contour_interval = st.slider(
                "Contour Interval (feet)",
                min_value=1,
                max_value=50,
                value=5,
                step=1,
                help="Vertical spacing between contour lines"
            )
            config['contour_interval'] = contour_interval
            
            st.info(f"📏 Contours will be generated every {contour_interval} feet")
        
        return config
    
    def _handle_preset_selection(self, preset: LayerPreset, sources: Dict) -> Tuple[Optional[str], Optional[List[str]], Dict]:
        """Handle preset selection"""
        st.success(f"✅ Selected preset: {preset.icon} **{preset.name}**")
        st.write(preset.description)
        
        # For now, return the first source in the preset
        # In a full implementation, this would handle multiple sources
        first_source_id = list(preset.sources.keys())[0]
        first_layer_ids = preset.sources[first_source_id]
        
        # Display what will be downloaded
        with st.expander("📋 Preset Details"):
            for source_id, layer_ids in preset.sources.items():
                if source_id in sources and sources[source_id]:
                    st.write(f"**{sources[source_id]['name']}:**")
                    for layer_id in layer_ids:
                        if layer_id in sources[source_id]['layers']:
                            layer_info = sources[source_id]['layers'][layer_id]
                            st.write(f"  • {layer_info['name']}")
        
        return first_source_id, first_layer_ids, {}


def display_enhanced_data_selection(sources: Dict) -> Tuple[Optional[str], Optional[List[str]], Dict]:
    """
    Display the enhanced data selection interface
    
    Args:
        sources: Available data sources dictionary
        
    Returns:
        Tuple of (source_id, layer_ids, config_options)
    """
    selector = EnhancedDataSelection()
    return selector.display_selection_interface(sources)