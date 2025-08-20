#!/usr/bin/env python3
"""
Test script for the Multi-Source Geospatial Data Downloader API
"""
import requests
import json
import time
import sys
from typing import Dict, Any

API_BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("🏥 Testing health check...")
    response = requests.get(f"{API_BASE_URL}/health")
    
    if response.status_code == 200:
        print("✅ Health check passed")
        return True
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return False

def test_get_downloaders():
    """Test getting available downloaders"""
    print("\n📡 Testing get downloaders...")
    response = requests.get(f"{API_BASE_URL}/downloaders")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {len(data)} downloaders:")
        for downloader_id, info in data.items():
            print(f"   - {downloader_id}: {info['name']} ({len(info['layers'])} layers)")
        return data
    else:
        print(f"❌ Failed to get downloaders: {response.status_code}")
        return None

def test_get_layers(downloader_id: str):
    """Test getting layers for a specific downloader"""
    print(f"\n🗂️  Testing get layers for {downloader_id}...")
    response = requests.get(f"{API_BASE_URL}/downloaders/{downloader_id}/layers")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {len(data)} layers for {downloader_id}")
        return data
    else:
        print(f"❌ Failed to get layers: {response.status_code}")
        return None

def test_create_job(downloader_id: str, layer_ids: list):
    """Test creating a download job"""
    print(f"\n🚀 Testing job creation for {downloader_id}...")
    
    # Use a small test area around Boulder, CO
    job_request = {
        "downloader_id": downloader_id,
        "layer_ids": layer_ids[:1],  # Just test one layer
        "aoi_bounds": {
            "minx": -105.3,
            "miny": 39.9,
            "maxx": -105.1,
            "maxy": 40.1
        },
        "config": {
            "timeout": 30
        }
    }
    
    response = requests.post(
        f"{API_BASE_URL}/jobs",
        json=job_request,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        job_id = data["job_id"]
        print(f"✅ Job created successfully: {job_id}")
        return job_id
    else:
        print(f"❌ Failed to create job: {response.status_code}")
        if response.text:
            print(f"   Error: {response.text}")
        return None

def test_job_status(job_id: str):
    """Test getting job status"""
    print(f"\n📊 Testing job status for {job_id}...")
    
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:
        response = requests.get(f"{API_BASE_URL}/jobs/{job_id}")
        
        if response.status_code == 200:
            data = response.json()
            status = data["status"]
            print(f"   Status: {status}")
            
            if "progress" in data and data["progress"]:
                progress = data["progress"]
                if "percent_complete" in progress:
                    print(f"   Progress: {progress['percent_complete']:.1f}%")
            
            if status == "completed":
                print("✅ Job completed successfully!")
                return data
            elif status == "failed":
                error = data.get("error_message", "Unknown error")
                print(f"❌ Job failed: {error}")
                return data
            elif status in ["pending", "running"]:
                print(f"   Job {status}, waiting...")
                time.sleep(3)
                attempt += 1
            else:
                print(f"❌ Unknown status: {status}")
                return data
        else:
            print(f"❌ Failed to get job status: {response.status_code}")
            return None
    
    print("⏰ Job did not complete within expected time")
    return None

def test_preview(downloader_id: str, layer_id: str):
    """Test the preview functionality"""
    print(f"\n👀 Testing preview for {downloader_id}/{layer_id}...")
    
    preview_request = {
        "downloader_id": downloader_id,
        "layer_id": layer_id,
        "aoi_bounds": {
            "minx": -105.3,
            "miny": 39.9,
            "maxx": -105.1,
            "maxy": 40.1
        },
        "max_features": 10
    }
    
    response = requests.post(
        f"{API_BASE_URL}/preview",
        json=preview_request,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        feature_count = data["feature_count"]
        print(f"✅ Preview successful: {feature_count} features")
        return True
    else:
        print(f"❌ Preview failed: {response.status_code}")
        if response.text:
            print(f"   Error: {response.text}")
        return False

def main():
    """Run all tests"""
    print("🧪 Starting API Tests")
    print("=" * 50)
    
    # Test 1: Health check
    if not test_health_check():
        print("\n❌ API is not running. Start the API first with: python start_api.py")
        sys.exit(1)
    
    # Test 2: Get downloaders
    downloaders = test_get_downloaders()
    if not downloaders:
        print("\n❌ Cannot proceed without downloaders")
        sys.exit(1)
    
    # Test 3: Get layers for first downloader
    first_downloader = list(downloaders.keys())[0]
    layers = test_get_layers(first_downloader)
    if not layers:
        print(f"\n❌ Cannot get layers for {first_downloader}")
        sys.exit(1)
    
    # Test 4: Preview functionality
    first_layer = list(layers.keys())[0]
    test_preview(first_downloader, first_layer)
    
    # Test 5: Create and monitor job
    layer_ids = list(layers.keys())
    job_id = test_create_job(first_downloader, layer_ids)
    
    if job_id:
        job_result = test_job_status(job_id)
        
        if job_result and job_result.get("status") == "completed":
            print(f"\n🎉 Full test completed successfully!")
            if job_result.get("result_summary"):
                summary = job_result["result_summary"]
                print(f"   Total features: {summary.get('total_features', 0)}")
                print(f"   Success rate: {summary.get('success_rate', 0):.1%}")
        else:
            print(f"\n⚠️  Job did not complete successfully")
    
    print("\n" + "=" * 50)
    print("🏁 API Tests Complete")

if __name__ == "__main__":
    main() 