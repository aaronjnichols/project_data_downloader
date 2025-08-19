"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_aoi_bounds() -> dict:
    """Sample AOI bounds for testing."""
    return {
        "minx": -122.5,
        "miny": 37.7,
        "maxx": -122.3,
        "maxy": 37.9,
    }


@pytest.fixture
def sample_geometry() -> dict:
    """Sample GeoJSON geometry for testing."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [-122.5, 37.7],
                [-122.3, 37.7],
                [-122.3, 37.9],
                [-122.5, 37.9],
                [-122.5, 37.7],
            ]
        ],
    }


@pytest.fixture
def mock_api_response() -> dict:
    """Mock API response for testing."""
    return {
        "job_id": "test-job-123",
        "status": "pending",
        "created_at": "2024-01-01T00:00:00Z",
    }


# Configure pytest markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (deselect with '-m \"not unit\"')"
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests (deselect with '-m \"not e2e\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )