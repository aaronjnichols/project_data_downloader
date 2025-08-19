# Geospatial Data Downloader Documentation

## Project Structure

This project follows a clean architecture pattern with the following structure:

```
src/geospatial_downloader/
├── domain/              # Business logic and models
│   ├── models/         # Data models (AOI, Job, DataSource, etc.)
│   ├── services/       # Business services
│   └── repositories/   # Data access layer
├── infrastructure/     # External interfaces
│   ├── api/           # API layer (FastAPI)
│   ├── downloaders/   # Data source adapters
│   └── storage/       # File and data storage
├── presentation/      # UI layer
│   ├── streamlit/     # Streamlit components
│   │   ├── components/# Reusable UI components
│   │   └── pages/     # Page definitions
│   └── web/           # Web interface (if needed)
└── shared/            # Shared utilities
    ├── config/        # Configuration management
    ├── utils/         # Utility functions
    └── exceptions/    # Exception classes
```

## Development Setup

1. **Install dependencies**:
   ```bash
   make install-dev
   ```

2. **Setup pre-commit hooks**:
   ```bash
   make pre-commit-install
   ```

3. **Run tests**:
   ```bash
   make test
   ```

4. **Code quality checks**:
   ```bash
   make quality
   ```

## Architecture Principles

- **Separation of Concerns**: Each layer has a specific responsibility
- **Dependency Inversion**: High-level modules don't depend on low-level modules
- **Single Responsibility**: Each class/function has one reason to change
- **Open/Closed**: Open for extension, closed for modification
- **Interface Segregation**: Clients shouldn't depend on interfaces they don't use

## Next Steps

This is Phase 1 of the refactoring plan. The current legacy code will be gradually migrated to this new structure while maintaining backwards compatibility.