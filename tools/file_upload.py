from pathlib import Path
import pandas as pd
from pydantic import BaseModel
from typing import Optional

class PortfolioUploadInput(BaseModel):
    file_path: str
    normalize_weights: bool = True

def handle_portfolio_upload(input_data: dict) -> dict:
    """
    Handle portfolio file upload with validation and normalization
    
    Args:
        input_data: Dict with file_path and optional normalize_weights
        
    Returns:
        Dict with normalized portfolio data
    """
    # Handle both old format (direct path string) and new format (dict)
    if isinstance(input_data, str):
        # Backward compatibility
        file_path = input_data
        normalize_weights = True
    else:
        # New format with validation
        req = PortfolioUploadInput(**input_data)
        file_path = req.file_path
        normalize_weights = req.normalize_weights
    
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Portfolio file not found: {file_path}")
    
    # Read file based on extension
    if p.suffix.lower() in (".xls", ".xlsx"):
        df = pd.read_excel(p)
    else:
        df = pd.read_csv(p)
    
    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]
    
    # Validate required columns
    if "ticker" not in df.columns or "weight" not in df.columns:
        raise ValueError("Expected columns 'ticker' and 'weight' not found. Available columns: " + str(list(df.columns)))
    
    # Clean and process data
    df = df[["ticker", "weight"]].dropna()
    df["weight"] = df["weight"].astype(float)
    
    # Validate weights
    if len(df) == 0:
        raise ValueError("No valid portfolio data found after cleaning")
    
    total_weight = df["weight"].sum()
    if total_weight <= 0:
        raise ValueError("Total portfolio weights must be positive")
    
    # Normalize weights if requested
    was_normalized = False
    if normalize_weights and abs(total_weight - 1.0) > 0.001:
        df["weight"] = df["weight"] / total_weight
        was_normalized = True
    
    # Convert to output format
    rows = df.to_dict(orient="records")
    
    return {
        "rows": rows,
        "normalized": was_normalized,
        "total_holdings": len(rows)
    }
