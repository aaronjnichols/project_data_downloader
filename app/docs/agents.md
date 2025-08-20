# AI Agent Development Guide
## Multi-Source Geospatial Data Downloader

*This document serves as a comprehensive guide for AI assistants working on this codebase.*

---

## 🏗️ **Project Architecture Overview**

### Core Concept
This is a **plugin-based geospatial data downloader** that can fetch data from multiple federal sources within a user-defined Area of Interest (AOI). The architecture is designed for extensibility - adding new data sources should require minimal core code changes.

### Key Design Principles
- **Plugin Architecture**: Each data source is a separate plugin inheriting from `BaseDownloader`
- **Configuration-Driven**: YAML configs control behavior without code changes
- **AOI-Centric**: All downloads are clipped to user-defined geographic boundaries
- **Robust Error Handling**: Graceful failures with detailed logging and retry logic

### Data Flow
```
AOI Shapefile → AOI Manager → Data Processor → Downloader Plugins → Output Structure
```

---

## 📁 **Directory Structure & Conventions**

```
├── core/                    # ✅ Core framework - MODIFY CAREFULLY
│   ├── base_downloader.py   # Abstract base class for all downloaders
│   ├── aoi_manager.py       # AOI loading and validation
│   └── data_processor.py    # Data processing and output organization
├── downloaders/             # ✅ Add new data source plugins here
│   ├── __init__.py          # Plugin registration system
│   ├── fema_downloader.py   # FEMA NFHL implementation
│   └── [future_sources].py # USGS LiDAR, NLCD, NRCS Soils
├── utils/                   # ✅ Shared utility functions
│   ├── spatial_utils.py     # Spatial operations (clipping, reprojection)
│   └── download_utils.py    # HTTP handling with retry logic
├── config/                  # ✅ Configuration templates and settings
│   ├── settings.yaml        # Global application settings
│   └── project_template.yaml # Template for new projects
├── main.py                  # ✅ CLI entry point
└── requirements.txt         # ✅ Python dependencies
```

### **⚠️ CRITICAL: What NOT to Modify**
- **`core/base_downloader.py`** - Only modify to add new abstract methods needed by ALL plugins
- **`main.py`** - CLI logic is stable; changes should be rare and well-tested
- **`utils/spatial_utils.py`** - Core spatial operations used by all plugins

---

## 🔌 **Plugin Development Guide**

### Adding a New Data Source

**1. Create the Plugin Class**
```python
# downloaders/new_source_downloader.py
from core.base_downloader import BaseDownloader, LayerInfo, DownloadResult

class NewSourceDownloader(BaseDownloader):
    @property
    def source_name(self) -> str:
        return "New Data Source Name"
    
    @property 
    def source_description(self) -> str:
        return "Description of what this source provides"
    
    def get_available_layers(self) -> Dict[str, LayerInfo]:
        # Return dictionary of available layers
        pass
    
    def download_layer(self, layer_id: str, aoi_bounds: Tuple[float, float, float, float], 
                      output_path: str, **kwargs) -> DownloadResult:
        # Implementation for downloading specific layer
        pass
```

**2. Register the Plugin**
```python
# In downloaders/__init__.py, add:
from .new_source_downloader import NewSourceDownloader
register_downloader("new_source", NewSourceDownloader)
```

**3. Add Configuration Support**
```yaml
# In config/settings.yaml and project templates:
data_sources:
  new_source:
    enabled: false
    # source-specific settings
```

### **Plugin Implementation Patterns**

- **Use `self.session` from `DownloadSession`** for HTTP requests (built-in retry logic)
- **Always return `DownloadResult` objects** with success/failure status
- **Handle AOI clipping** using `utils.spatial_utils.clip_vector_to_aoi()`
- **Use `utils.spatial_utils.safe_file_name()`** for output file naming
- **Implement proper error handling** with meaningful error messages

---

## ⚙️ **Configuration Management**

### Configuration Hierarchy
1. **Global Settings** (`config/settings.yaml`) - Application-wide defaults
2. **Project Config** (`my_project.yaml`) - Project-specific overrides
3. **Plugin Config** (within project config) - Plugin-specific settings

### Configuration Patterns
```yaml
# Standard project configuration structure
project:
  name: "Project Name"
  aoi_file: "data/aoi.shp"
  output_directory: "./output"

data_sources:
  source_name:
    enabled: true/false
    layers: "all" | ["layer1", "layer2"]  # Layer selection pattern
    config:
      source_specific_key: value
```

### **⚠️ Configuration Rules**
- **Never hardcode paths** - Always use configuration
- **Provide sensible defaults** in global settings
- **Make plugin configs optional** - plugins should work with minimal config
- **Validate configuration** in plugin constructors

---

## 🛠️ **Common Development Tasks**

### **When Asked to "Add Support for [Data Source]"**
1. Research the data source API/endpoints
2. Create plugin class in `downloaders/`
3. Implement required abstract methods
4. Register plugin in `downloaders/__init__.py`
5. Add configuration templates
6. Test with dry-run mode
7. Update documentation

### **When Asked to "Fix Download Issues"**
1. Check error logs for specific failure points
2. Verify AOI bounds and CRS compatibility
3. Test API endpoints manually if needed
4. Implement better error handling/retry logic
5. Add validation for edge cases

### **When Asked to "Improve Performance"**
1. Identify bottlenecks (usually network or data processing)
2. Implement parallel downloads where appropriate
3. Add caching mechanisms
4. Optimize spatial operations
5. Consider streaming for large datasets

### **When Asked to "Add New Configuration Options"**
1. Add to appropriate YAML files
2. Update plugin constructors to use new options
3. Provide backward compatibility
4. Update documentation and templates

---

## 📝 **Code Style & Standards**

### **Naming Conventions**
- **Classes**: `PascalCase` (e.g., `FEMADownloader`)
- **Functions/Variables**: `snake_case` (e.g., `download_layer`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `NFHL_LAYERS`)
- **Files**: `snake_case.py` (e.g., `fema_downloader.py`)

### **Documentation Standards**
- **All public methods** must have docstrings
- **Use type hints** for all function parameters and returns
- **Include usage examples** in plugin docstrings
- **Comment complex spatial operations**

### **Error Handling Patterns**
```python
# Good: Specific exception handling with logging
try:
    result = risky_operation()
    return DownloadResult(success=True, ...)
except SpecificException as e:
    logger.error(f"Specific error occurred: {e}")
    return DownloadResult(success=False, error_message=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return DownloadResult(success=False, error_message="Unexpected error occurred")
```

---

## 🧪 **Testing & Validation**

### **Before Making Changes**
1. **Run dry-run tests**: `python main.py --project test_project.yaml --dry-run`
2. **Test layer listing**: `python main.py --list-layers`
3. **Verify configuration loading**: Check no YAML parsing errors

### **After Making Changes**
1. **Test affected plugins** with actual downloads
2. **Verify output structure** and file organization
3. **Check logs** for any new warnings or errors
4. **Test edge cases** (empty results, network failures, invalid AOI)

### **Testing New Plugins**
1. Start with `--list-layers [plugin_name]`
2. Use `--dry-run` to test layer selection logic
3. Test with small AOI first
4. Verify all layer types (Point, Polyline, Polygon, Raster)
5. Test error conditions (invalid layer IDs, network failures)

---

## 📚 **Key Dependencies & When to Use**

### **Core Geospatial Stack**
- **geopandas**: Vector data operations, reading/writing shapefiles
- **shapely**: Geometric operations (clipping, buffering)
- **rasterio**: Raster data processing (future NLCD, LiDAR)
- **pyproj**: Coordinate system transformations

### **HTTP & Data Handling**
- **requests**: HTTP downloads with retry logic
- **PyYAML**: Configuration file parsing

### **When to Add New Dependencies**
- **Avoid adding dependencies** for single-plugin use cases
- **Prefer standard library** when possible
- **Add to requirements.txt** with minimum version requirements
- **Document why** the dependency is needed

---

## 🐛 **Debugging & Troubleshooting**

### **Common Issues & Solutions**

**Configuration Loading Errors**
```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('config/settings.yaml'))"
```

**AOI Loading Failures**
- Verify shapefile exists and is readable
- Check CRS definition in .prj file
- Ensure geometry is valid (not self-intersecting)

**Download Failures**
- Test API endpoints manually in browser
- Check network connectivity and firewall settings
- Verify AOI intersects with data coverage area
- Increase timeout settings in configuration

**Plugin Registration Issues**
- Check import statements in `downloaders/__init__.py`
- Verify plugin class inherits from `BaseDownloader`
- Ensure all abstract methods are implemented

### **Debugging Tools**
```python
# Enable debug logging
logging.getLogger().setLevel(logging.DEBUG)

# Test individual components
from core.aoi_manager import AOIManager
aoi = AOIManager()
aoi.load_aoi_from_file("data/aoi.shp")
```

---

## 📋 **Git & Documentation Standards**

### **Commit Message Format**
```
<type>: <description>

Types:
- feat: New feature (new data source, enhancement)
- fix: Bug fix
- docs: Documentation changes
- refactor: Code refactoring
- test: Testing improvements
- config: Configuration changes
```

### **When to Update Documentation**
- **Always** when adding new plugins
- **Always** when changing configuration structure
- **Always** when modifying CLI interface
- When adding new utility functions

### **Pull Request Guidelines**
- Include example configuration for new features
- Test with multiple AOI sizes and locations
- Update README.md if user-facing changes
- Include test commands in PR description

---

## 🎯 **Priority Guidelines for AI Agents**

### **HIGH PRIORITY**
1. **Maintain plugin architecture** - Don't break the extensibility model
2. **Preserve backward compatibility** - Existing project configs should continue working
3. **Follow error handling patterns** - Always return meaningful error messages
4. **Respect spatial data integrity** - Proper CRS handling and clipping

### **MEDIUM PRIORITY**
1. **Performance optimizations** - Improve download speeds and memory usage
2. **Enhanced configuration options** - More granular control
3. **Better logging and progress reporting** - User experience improvements

### **LOW PRIORITY**
1. **Code style improvements** - Unless specifically requested
2. **Refactoring for refactoring's sake** - Focus on functionality first

---

## 🚨 **Red Flags - Stop and Ask for Clarification**

- **Modifying core spatial operations** without understanding implications
- **Changing the plugin interface** (BaseDownloader) without considering all existing plugins
- **Adding dependencies** that significantly increase installation complexity
- **Hardcoding URLs or paths** instead of using configuration
- **Breaking changes** to existing project configuration format

---

*This guide should be updated as the project evolves. When in doubt, follow existing patterns and prioritize maintainability over cleverness.* 