"""
Enhanced evaluation script with comprehensive testing
"""
import json
import os
import sys
from pathlib import Path

# Add the project root to Python path
BASE = Path(__file__).resolve().parents[2] 
sys.path.insert(0, str(BASE))

import requests
from jsonschema import validate
from tools.xmetric import handle_xmetric
from tools.ymetric import handle_ymetric
from tools.file_upload import handle_portfolio_upload

def load_schema(schema_name: str) -> dict:
    """Load JSON schema for validation"""
    schema_path = BASE / "schemas" / f"{schema_name}.schema.json"
    with open(schema_path) as f:
        return json.load(f)

def test_xmetric_tool():
    """Test XMetric tool with sample data"""
    print("🧪 Testing XMetric Tool...")
    
    schema = load_schema("xmetric")
    test_input = {
        "table_name": "sample.csv",
        "date_column": "date", 
        "value_column": "close",
        "aggregation": "none",
        "scale_factor": 1.0
    }
    
    # Validate input against schema
    try:
        validate(test_input, schema)
        print("✅ Input validation passed")
    except Exception as e:
        print(f"❌ Input validation failed: {e}")
        return None
    
    # Test tool execution
    try:
        result = handle_xmetric(test_input, data_root=str(BASE / "data"))
        print(f"✅ XMetric executed successfully")
        print(f"   Series points: {len(result['series'])}")
        print(f"   Mean value: {result['summary']['mean']:.2f}")
        print(f"   Data count: {result['summary']['count']}")
        return result
    except Exception as e:
        print(f"❌ XMetric execution failed: {e}")
        return None

def test_ymetric_tool():
    """Test YMetric tool with sample data"""
    print("\n🧪 Testing YMetric Tool...")
    
    schema = load_schema("ymetric") 
    test_input = {
        "table_name": "sample.csv",
        "date_column": "date",
        "value_column": "close", 
        "aggregation": "Mean",  # Test case-insensitive
        "scale_factor": 1.2
    }
    
    # Validate input against schema (normalize aggregation case first)
    validation_input = test_input.copy()
    if 'aggregation' in validation_input:
        validation_input['aggregation'] = validation_input['aggregation'].lower()
    
    try:
        validate(validation_input, schema)
        print("✅ Input validation passed")
    except Exception as e:
        print(f"❌ Input validation failed: {e}")
        return None
    
    # Test tool execution
    try:
        result = handle_ymetric(test_input, data_root=str(BASE / "data"))
        print(f"✅ YMetric executed successfully")
        print(f"   Series points: {len(result['series'])}")
        print(f"   Scaled mean: {result['summary']['mean']:.2f}")
        print(f"   Data count: {result['summary']['count']}")
        return result
    except Exception as e:
        print(f"❌ YMetric execution failed: {e}")
        return None

def test_portfolio_upload():
    """Test portfolio upload functionality"""
    print("\n🧪 Testing Portfolio Upload...")
    
    # Create sample portfolio data
    sample_portfolio_path = BASE / "data" / "test_portfolio.csv"
    with open(sample_portfolio_path, 'w') as f:
        f.write("ticker,weight\n")
        f.write("AAPL,0.3\n")
        f.write("MSFT,0.25\n")
        f.write("GOOGL,0.2\n")
        f.write("TSLA,0.15\n")
        f.write("NVDA,0.1\n")
    
    try:
        result = handle_portfolio_upload(str(sample_portfolio_path))
        print("✅ Portfolio upload successful")
        print(f"   Normalized: {result['normalized']}")
        print(f"   Holdings: {len(result['rows'])}")
        
        # Verify weights sum to 1.0
        total_weight = sum(row['weight'] for row in result['rows'])
        assert abs(total_weight - 1.0) < 0.001, f"Weights don't sum to 1.0: {total_weight}"
        print(f"   Weight validation: ✅ (sum = {total_weight:.3f})")
        
        # Clean up test file
        sample_portfolio_path.unlink()
        
    except Exception as e:
        print(f"❌ Portfolio upload failed: {e}")

def test_api_endpoint():
    """Test API endpoint if running"""
    print("\n🧪 Testing API Endpoint...")
    
    url = "http://127.0.0.1:8000/xmetric"
    payload = {
        "table_name": "sample.csv",
        "date_column": "date", 
        "value_column": "close"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print("✅ API endpoint responsive")
            result = response.json()
            print(f"   Response keys: {list(result.keys())}")
        else:
            print(f"⚠️  API returned status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("⚠️  API endpoint not running (this is OK for testing)")
    except Exception as e:
        print(f"❌ API test failed: {e}")

def run_basic_analysis():
    """Run basic XMetric analysis (from original run_eval.py)"""
    print("\n🧪 Testing Basic XMetric Analysis...")
    
    try:
        schema = json.load(open(BASE/"schemas"/"xmetric.schema.json"))
        inp = {"table_name":"sample.csv","date_column":"date","value_column":"close"}
        out = handle_xmetric(inp, data_root=str(BASE/"data"))
        print("✅ Basic analysis successful")
        print(f"   Output keys: {list(out.keys())}")
        return out
    except Exception as e:
        print(f"❌ Basic analysis failed: {e}")
        return None

def validate_project_structure():
    """Validate that all required files and directories exist"""
    print("\n🧪 Validating Project Structure...")
    
    required_paths = [
        "tools/xmetric.py",
        "tools/ymetric.py", 
        "tools/file_upload.py",
        "schemas/xmetric.schema.json",
        "schemas/ymetric.schema.json",
        "schemas/portfolio.schema.json",
        "mcp/xmetric_manifest.json",
        "mcp/ymetric_manifest.json", 
        "mcp/portfolio_manifest.json",
        "gpt/system_prompt.md",
        "gpt/prompt_cards.md",
        "data/sample.csv",
        "config.md"
    ]
    
    missing_files = []
    for path in required_paths:
        full_path = BASE / path
        if not full_path.exists():
            missing_files.append(path)
        else:
            print(f"✅ {path}")
    
    if missing_files:
        print(f"\n❌ Missing files: {missing_files}")
        return False
    else:
        print("\n✅ All required files present")
        return True

def main():
    """Run comprehensive evaluation"""
    print("🚀 Starting Custom GPT Evaluation")
    print("=" * 50)
    
    # Validate project structure
    if not validate_project_structure():
        print("❌ Project structure validation failed")
        return 1
    
    # Test individual tools
    xmetric_result = test_xmetric_tool()
    ymetric_result = test_ymetric_tool()
    
    # Test basic analysis (from original run_eval.py)
    run_basic_analysis()
    
    # Test portfolio upload
    test_portfolio_upload()
    
    # Test API endpoint
    test_api_endpoint()
    
    print("\n" + "=" * 50)
    print("🎉 Evaluation Complete!")
    print("\n💡 Next Steps:")
    print("1. Configure Custom GPT in ChatGPT interface")
    print("2. Upload system prompt and tool manifests")
    print("3. Set up File Search with financial corpus")
    print("4. Test conversation starters")
    print("5. Validate chart rendering in GPT artifacts")
    
    return 0

if __name__ == "__main__":
    exit(main())