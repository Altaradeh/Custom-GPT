"""
Tests for Short-Term endpoints in the FastAPI app
"""

import pytest
from fastapi.testclient import TestClient
from main import app
import pandas as pd


client = TestClient(app)


class TestShortTermEndpoints:
    def test_levels_endpoint(self):
        resp = client.get("/short_term/levels")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 7  # 7 default levels

        first = data[0]
        for key in [
            "param_set_id","category","level_rank","drawdown","t_down","t_up",
            "envelope_asym","annual_vol","df_returns","tanh_scale","max_daily_return","min_crisis_len"
        ]:
            assert key in first

        # Ensure sorted by level_rank ascending
        levels = [row["level_rank"] for row in data]
        assert levels == sorted(levels)

    def test_baseline_endpoint(self):
        # Read expected row count from CSV to validate the endpoint mirrors it
        df = pd.read_csv("normal_vs_fragile_table.csv")
        expected_rows = len(df)

        resp = client.get("/short_term/baseline")
        assert resp.status_code == 200
        rows = resp.json()

        assert isinstance(rows, list)
        assert len(rows) == expected_rows
        r0 = rows[0]
        for key in [
            "month","mean_normal","p10_normal","p90_normal","mean_fragile","p10_fragile","p90_fragile"
        ]:
            assert key in r0

    def test_demo_summary_endpoint(self):
        # Keep this small for speed
        resp = client.get("/short_term/demo_summary?level=3&n_paths=12&random_state=42")
        assert resp.status_code == 200
        data = resp.json()

        # Validate param_set info
        assert "param_set" in data
        assert data["param_set"]["level_rank"] == 3

        # Validate stats structure
        assert "stats" in data and isinstance(data["stats"], list) and len(data["stats"]) > 0
        s0 = data["stats"][0]
        for key in ["t_day","mean","p10","p90"]:
            assert key in s0

        # Validate monthly table structure
        assert "monthly_table" in data and isinstance(data["monthly_table"], list) and len(data["monthly_table"]) > 0
        m0 = data["monthly_table"][0]
        for key in ["month","mean","p10","p90"]:
            assert key in m0


if __name__ == "__main__":
    # Allow running directly: python test_short_term_api.py
    import sys, pytest
    sys.exit(pytest.main([__file__, "-v"]))
