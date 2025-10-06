"""
Quick test for enhanced portfolio error handling
"""
import requests

# Test with non-existent file
print("Testing with non-existent file...")
response = requests.post(
    "http://localhost:8000/portfolio/upload",
    json={
        "file_path": "nonexistent_portfolio.csv",
        "normalize_weights": True
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
print()

# Test with correct file
print("Testing with correct file...")
response = requests.post(
    "http://localhost:8000/portfolio/upload",
    json={
        "file_path": "sample_portfolio",
        "normalize_weights": True
    }
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Total holdings: {data['total_holdings']}")
    print(f"Normalized: {data['normalized']}")
    print(f"First 3 holdings: {data['rows'][:3]}")
else:
    print(f"Error: {response.json()}")
