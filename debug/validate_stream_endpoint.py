#!/usr/bin/env python3
"""Quick validation script for stream endpoint functionality.

Run this after starting the server to verify the stream endpoint works correctly.

Usage:
    python debug/validate_stream_endpoint.py [BASE_URL]

Example:
    python debug/validate_stream_endpoint.py http://localhost:7000
"""
import sys
import json
import urllib.request
import urllib.error


def test_endpoint(base_url: str, endpoint: str, description: str) -> bool:
    """Test a single endpoint and print results."""
    url = f"{base_url}{endpoint}"
    print(f"\n🧪 Testing: {description}")
    print(f"   URL: {url}")
    
    try:
        with urllib.request.urlopen(url) as response:
            status = response.status
            data = json.loads(response.read().decode())
            
            print(f"   ✅ Status: {status}")
            print(f"   📦 Response: {json.dumps(data, indent=2)}")
            return True
            
    except urllib.error.HTTPError as e:
        print(f"   ❌ HTTP Error {e.code}: {e.reason}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    """Run all validation tests."""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:7000"
    
    print("=" * 70)
    print("🎬 Stremio HU Live Movies - Stream Endpoint Validation")
    print("=" * 70)
    print(f"Target: {base_url}")
    
    tests = [
        ("/manifest.json", "Manifest includes stream resource"),
        ("/stream/movie/musortv:rtl:1234567890:test.json", "Stream endpoint with valid ID"),
        ("/stream/movie/invalid-id.json", "Stream endpoint with invalid ID"),
        ("/healthz", "Health check endpoint"),
    ]
    
    results = []
    for endpoint, description in tests:
        result = test_endpoint(base_url, endpoint, description)
        results.append((description, result))
    
    print("\n" + "=" * 70)
    print("📊 Summary")
    print("=" * 70)
    
    for description, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {description}")
    
    total = len(results)
    passed = sum(1 for _, result in results if result)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    # Special validation for manifest
    print("\n" + "=" * 70)
    print("🔍 Manifest Validation")
    print("=" * 70)
    
    try:
        with urllib.request.urlopen(f"{base_url}/manifest.json") as response:
            manifest = json.loads(response.read().decode())
            
            print(f"ID: {manifest.get('id')}")
            print(f"Name: {manifest.get('name')}")
            print(f"Version: {manifest.get('version')}")
            print(f"Resources: {manifest.get('resources')}")
            
            if "stream" in manifest.get("resources", []):
                print("\n✅ Stream resource is declared in manifest")
            else:
                print("\n❌ WARNING: Stream resource NOT declared in manifest")
                
            if "catalog" in manifest.get("resources", []):
                print("✅ Catalog resource is declared in manifest")
            else:
                print("❌ WARNING: Catalog resource NOT declared in manifest")
                
    except Exception as e:
        print(f"❌ Could not validate manifest: {e}")
    
    print("\n" + "=" * 70)
    
    # Exit code based on results
    sys.exit(0 if all(result for _, result in results) else 1)


if __name__ == "__main__":
    main()
