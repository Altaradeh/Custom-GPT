from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import pandas as pd

class XMetricInput(BaseModel):
    table_name: str
    date_column: str
    value_column: str
    aggregation: Optional[str] = "none"
    scale_factor: float = 1.0

def handle_xmetric(input_json: dict, data_root: str = "data") -> dict:
    req = XMetricInput(**input_json)
    p = Path(data_root) / req.table_name
    
    # If path doesn't exist, try adding extensions
    if not p.exists():
        for ext in [".csv", ".parquet"]:
            p_with_ext = Path(data_root) / f"{req.table_name}{ext}"
            if p_with_ext.exists():
                p = p_with_ext
                break
        else:
            raise FileNotFoundError(f"File not found: {req.table_name} (tried .csv and .parquet extensions in {data_root})")
    
    if p.suffix.lower() in (".parquet",):
        df = pd.read_parquet(p)
    else:
        df = pd.read_csv(p)
    df = df[[req.date_column, req.value_column]].dropna()
    df[req.date_column] = pd.to_datetime(df[req.date_column])
    if req.aggregation.lower() != "none":
        # Map aggregation types to pandas functions (case-insensitive)
        agg_map = {
            "sum": "sum",
            "mean": "mean", 
            "max": "max",
            "min": "min"
        }
        agg_lower = req.aggregation.lower()
        if agg_lower in agg_map:
            df = df.groupby(req.date_column).agg({req.value_column: agg_map[agg_lower]}).reset_index()
        else:
            raise ValueError(f"Unsupported aggregation: {req.aggregation}. Use: none, sum, mean, max, min (case-insensitive)")
    df[req.value_column] = df[req.value_column] * req.scale_factor
    series = [{"date": d.strftime("%Y-%m-%d"), "value": float(v)} for d, v in zip(df[req.date_column], df[req.value_column])]
    summary = {"mean": float(df[req.value_column].mean()), "count": int(len(df))}
    return {"series": series, "summary": summary}
