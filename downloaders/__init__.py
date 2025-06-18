# Downloaders package - Plugin registration for data source downloaders
from typing import Dict, Type
from core.base_downloader import BaseDownloader

# Registry of available downloaders
_downloader_registry: Dict[str, Type[BaseDownloader]] = {}

def register_downloader(name: str, downloader_class: Type[BaseDownloader]):
    """Register a downloader plugin"""
    _downloader_registry[name] = downloader_class

def get_downloader(name: str) -> Type[BaseDownloader]:
    """Get a downloader class by name"""
    if name not in _downloader_registry:
        raise ValueError(f"Unknown downloader: {name}")
    return _downloader_registry[name]

def list_downloaders() -> Dict[str, Type[BaseDownloader]]:
    """Get all registered downloaders"""
    return _downloader_registry.copy()

# Import all downloader modules to trigger registration
try:
    from .fema_downloader import FEMADownloader
    register_downloader("fema", FEMADownloader)
except ImportError:
    pass

# Future downloaders will be imported here
# from .usgs_lidar_downloader import USGSLidarDownloader
# from .nlcd_downloader import NLCDDownloader
# from .nrcs_soils_downloader import NRCSSoilsDownloader 