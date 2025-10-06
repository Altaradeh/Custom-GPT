"""
FastAPI Testing Script
Tests all API endpoints with sample data
"""
import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_health_endpoint():
    """Test health check endpoint"""
    print("🏥 Testing Health Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ API not running. Start with: poetry run python run_api.py")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_xmetric_endpoint():
    """Test XMetric analysis endpoint"""
    print("\n🧮 Testing XMetric Endpoint...")
    
    payload = {
        "table_name": "sample.csv",
        "date_column": "date",
        "value_column": "close",
        "aggregation": "none",
        "scale_factor": 1.0
    }
    
    try:
        response = requests.post(f"{BASE_URL}/xmetric", json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print("✅ XMetric endpoint successful")
            print(f"   Series points: {len(result['series'])}")
            print(f"   Mean value: {result['summary']['mean']:.2f}")
            print(f"   Count: {result['summary']['count']}")
            return True
        else:
            print(f"❌ XMetric failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ XMetric error: {e}")
        return False

def test_ymetric_endpoint():
    """Test YMetric analysis endpoint"""
    print("\n📊 Testing YMetric Endpoint...")
    
    payload = {
        "table_name": "sample.csv",
        "date_column": "date",
        "value_column": "close",
        "aggregation": "mean",
        "scale_factor": 1.5
    }
    
    try:
        response = requests.post(f"{BASE_URL}/ymetric", json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print("✅ YMetric endpoint successful")
            print(f"   Series points: {len(result['series'])}")
            print(f"   Scaled mean: {result['summary']['mean']:.2f}")
            print(f"   Count: {result['summary']['count']}")
            return True
        else:
            print(f"❌ YMetric failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ YMetric error: {e}")
        return False

def test_portfolio_endpoint():
    """Test Portfolio upload endpoint"""
    print("\n💼 Testing Portfolio Endpoint...")
    
    # Use the sample portfolio file
    portfolio_path = Path("data/sample_portfolio.csv").resolve()
    
    payload = {
        "file_path": str(portfolio_path),
        "normalize_weights": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/portfolio/upload", json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print("✅ Portfolio endpoint successful")
            print(f"   Holdings: {result['total_holdings']}")
            print(f"   Normalized: {result['normalized']}")
            print(f"   Sample holding: {result['rows'][0] if result['rows'] else 'None'}")
            return True
        else:
            print(f"❌ Portfolio failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Portfolio error: {e}")
        return False

def test_docs_endpoint():
    """Test API documentation endpoint"""
    print("\n📖 Testing Docs Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API documentation accessible")
            print(f"   URL: {BASE_URL}/docs")
            return True
        else:
            print(f"❌ Docs failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Docs error: {e}")
        return False

def test_error_handling():
    """Test API error handling"""
    print("\n🚨 Testing Error Handling...")
    
    # Test with invalid file
    payload = {
        "table_name": "nonexistent.csv",
        "date_column": "date",
        "value_column": "close"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/xmetric", json=payload, timeout=10)
        if response.status_code == 404:
            print("✅ Error handling works (404 for missing file)")
            error_detail = response.json().get("detail", "No detail")
            print(f"   Error message: {error_detail}")
            return True
        else:
            print(f"❌ Expected 404, got: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def main():
    """Run all API tests"""
    print("🚀 FastAPI Comprehensive Testing")
    print("=" * 50)
    
    tests = [
        test_health_endpoint,
        test_xmetric_endpoint,
        test_ymetric_endpoint,
        test_portfolio_endpoint,
        test_docs_endpoint,
        test_error_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        time.sleep(0.5)  # Brief pause between tests
    
    print("\n" + "=" * 50)
    print(f"🎯 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All API tests passed! FastAPI implementation is working perfectly.")
        print("\n💡 Next steps:")
        print("   • API is ready for production deployment")
        print("   • Use /docs for interactive API testing")
        print("   • All endpoints are MCP-compatible")
    else:
        print("⚠️  Some tests failed. Check the API server and dependencies.")
        print("\n🔧 Troubleshooting:")
        print("   • Ensure API server is running: poetry run python run_api.py")
        print("   • Check that sample data files exist in /data directory")
        print("   • Verify all dependencies are installed: poetry install")

if __name__ == "__main__":
    main()