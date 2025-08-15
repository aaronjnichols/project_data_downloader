#!/usr/bin/env python3
"""
Startup script for the Multi-Source Geospatial Data Downloader API
"""
import os
import sys
import uvicorn
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Start the FastAPI server"""
    
    # Create necessary directories
    os.makedirs("output/jobs", exist_ok=True)
    os.makedirs("output/results", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Configuration
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"
    log_level = os.getenv("API_LOG_LEVEL", "info")
    
    print(f"Starting Multi-Source Geospatial Data Downloader API")
    print(f"Server: http://{host}:{port}")
    print(f"Documentation: http://{host}:{port}/docs")
    print(f"OpenAPI Schema: http://{host}:{port}/openapi.json")
    print(f"Health Check: http://{host}:{port}/health")
    
    # Start the server
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        access_log=True
    )

if __name__ == "__main__":
    main() 