"""
Test suite for Long-Term Financial Market Simulation API
========================================================

Basic tests to validate API functionality and data integrity.
Run with: pytest test_api.py -v
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from main import app, load_data
import pandas as pd
import os

# Create test client
client = TestClient(app)

class TestAPIEndpoints:
    """Test all API endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint returns correct information"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "endpoints" in data
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_scenarios_endpoint(self):
        """Test scenarios endpoint returns valid data"""
        response = client.get("/long_term/scenarios")
        assert response.status_code == 200
        
        scenarios = response.json()
        assert isinstance(scenarios, list)
        
        if scenarios:  # If we have data
            scenario = scenarios[0]
            required_fields = [
                "target_mean", "target_spread", "description", 
                "semantic_category", "total_paths"
            ]
            for field in required_fields:
                assert field in scenario
            
            # Validate semantic categories
            assert scenario["semantic_category"] in [
                "conservative", "moderate", "aggressive"
            ]
    
    def test_paths_endpoint_with_valid_params(self):
        """Test paths endpoint with valid parameters"""
        # First get available scenarios
        scenarios_response = client.get("/long_term/scenarios")
        assert scenarios_response.status_code == 200
        
        scenarios = scenarios_response.json()
        if not scenarios:
            pytest.skip("No scenarios available for testing")
        
        # Use first available scenario
        scenario = scenarios[0]
        mean = scenario["target_mean"]
        spread = scenario["target_spread"]
        
        # Test paths endpoint
        response = client.get(f"/long_term/paths?mean={mean}&spread={spread}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Validate response structure
        required_sections = [
            "scenario_info", "summary_statistics", 
            "envelope_chart_data", "path_details_table"
        ]
        for section in required_sections:
            assert section in data
        
        # Validate summary statistics
        stats = data["summary_statistics"]
        assert "average_annual_return" in stats
        assert "return_category" in stats
        assert "risk_category" in stats
        
        # Validate envelope data
        envelope = data["envelope_chart_data"]
        assert "years" in envelope
        assert "p05_path" in envelope
        assert "p50_path" in envelope
        assert "p95_path" in envelope
        assert len(envelope["years"]) == len(envelope["p05_path"])
    
    def test_paths_endpoint_invalid_params(self):
        """Test paths endpoint with invalid parameters"""
        # Test with out-of-range values (should return 422 validation error)
        response = client.get("/long_term/paths?mean=999&spread=999")
        assert response.status_code == 422  # Validation error for out-of-range values
        
        # Test with valid range but non-existent scenario (should return 404)
        response2 = client.get("/long_term/paths?mean=0.15&spread=4.5")
        # This might return 404 or 422 depending on available data
        assert response2.status_code in [404, 422]
    
    def test_paths_endpoint_missing_params(self):
        """Test paths endpoint with missing parameters"""
        response = client.get("/long_term/paths")
        assert response.status_code == 422  # Validation error

class TestDataIntegrity:
    """Test data loading and integrity"""
    
    def test_data_files_exist(self):
        """Test that required data files exist"""
        from pathlib import Path
        
        data_dir = Path("Long Term Model/Long Term Model")
        library_file = data_dir / "final_path_statistics_library.csv"
        param_file = data_dir / "param_library.csv"
        
        assert library_file.exists(), f"Library file not found: {library_file}"
        assert param_file.exists(), f"Parameter file not found: {param_file}"
    
    def test_data_loading(self):
        """Test data loading functionality"""
        try:
            library_df, param_df = load_data()
            
            # Validate library data
            assert isinstance(library_df, pd.DataFrame)
            assert len(library_df) > 0
            
            required_columns = [
                'path_id', 'target_mean', 'target_spread', 
                'actual_annual_return', 'max_drop', 'lost_decades'
            ]
            for col in required_columns:
                assert col in library_df.columns
            
            # Validate parameter data
            assert isinstance(param_df, pd.DataFrame)
            assert len(param_df) > 0
            
            param_columns = ['target_mean', 'target_spread', 'opt_mu', 'opt_sigma', 'opt_kappa']
            for col in param_columns:
                assert col in param_df.columns
                
        except Exception as e:
            pytest.fail(f"Data loading failed: {str(e)}")

class TestSemanticCategorization:
    """Test semantic categorization functions"""
    
    def test_return_categorization(self):
        """Test return categorization logic"""
        from main import categorize_return
        
        assert categorize_return(0.02) == "very_low"
        assert categorize_return(0.04) == "low"
        assert categorize_return(0.06) == "moderate"
        assert categorize_return(0.08) == "high"
        assert categorize_return(0.10) == "very_high"
    
    def test_drawdown_categorization(self):
        """Test drawdown categorization logic"""
        from main import categorize_drawdown
        
        assert categorize_drawdown(0.15) == "low"
        assert categorize_drawdown(0.30) == "moderate"
        assert categorize_drawdown(0.45) == "high"
        assert categorize_drawdown(0.60) == "very_high"
    
    def test_spread_categorization(self):
        """Test spread categorization logic"""
        from main import categorize_spread
        
        assert categorize_spread(1.0) == "conservative"
        assert categorize_spread(2.0) == "moderate"
        assert categorize_spread(3.0) == "aggressive"

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
