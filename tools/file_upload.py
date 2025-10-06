from pathlib import Path
import pandas as pd
from pydantic import BaseModel
from typing import Optional

class PortfolioUploadInput(BaseModel):
    file_path: str
    normalize_weights: bool = True

def handle_portfolio_upload(input_data: dict, data_root: str = "data") -> dict:
    """
    Handle portfolio file upload with validation and normalization
    
    Args:
        input_data: Dict with file_path and optional normalize_weights
        data_root: Root directory for data files (default: "data")
        
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
    
    # Clean up the file path
    # Remove leading /data/ or data/ if present
    cleaned_path = file_path.strip()
    if cleaned_path.startswith("/data/"):
        cleaned_path = cleaned_path[6:]  # Remove /data/
    elif cleaned_path.startswith("data/"):
        cleaned_path = cleaned_path[5:]  # Remove data/
    elif cleaned_path.startswith("/"):
        cleaned_path = cleaned_path[1:]  # Remove leading /
    
    # Try to find the file
    p = Path(cleaned_path)
    
    # If absolute path and exists, use it
    if p.is_absolute() and p.exists():
        pass  # Use the path as-is
    else:
        # Try as filename in data directory
        p = Path(data_root) / cleaned_path
        
        # If still doesn't exist, try adding extensions
        if not p.exists():
            # First try the exact filename without extension
            base_name = cleaned_path
            if base_name.endswith((".csv", ".xlsx", ".xls")):
                # Remove extension to try others
                base_name = Path(cleaned_path).stem
            
            for ext in [".csv", ".xlsx", ".xls"]:
                p_with_ext = Path(data_root) / f"{base_name}{ext}"
                if p_with_ext.exists():
                    p = p_with_ext
                    break
            else:
                # Still not found - gather available portfolio files to suggest
                available_files = []
                data_dir = Path(data_root)
                if data_dir.exists():
                    for portfolio_ext in [".csv", ".xlsx", ".xls"]:
                        available_files.extend([f.name for f in data_dir.glob(f"*portfolio*{portfolio_ext}")])
                        available_files.extend([f.name for f in data_dir.glob(f"*{portfolio_ext}")])
                    # Remove duplicates and limit to unique files
                    available_files = sorted(set(available_files))[:5]  # Show max 5 suggestions
                
                error_msg = f"Portfolio file not found: {file_path}"
                if available_files:
                    error_msg += f". Available files: {', '.join(available_files)}"
                else:
                    error_msg += f" (checked in {data_root} with .csv, .xlsx, .xls extensions)"
                
                raise FileNotFoundError(error_msg)
    
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
