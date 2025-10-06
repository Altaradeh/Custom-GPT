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
    if not p.exists():
        raise FileNotFoundError(f"{p} not found")
    if p.suffix.lower() in (".parquet",):
        df = pd.read_parquet(p)
    else:
        df = pd.read_csv(p)
    df = df[[req.date_column, req.value_column]].dropna()
    df[req.date_column] = pd.to_datetime(df[req.date_column])
    if req.aggregation != "none":
        df = df.groupby(req.date_column).agg({req.value_column: req.aggregation}).reset_index()
    df[req.value_column] = df[req.value_column] * req.scale_factor
    series = [{"date": d.strftime("%Y-%m-%d"), "value": float(v)} for d, v in zip(df[req.date_column], df[req.value_column])]
    summary = {"mean": float(df[req.value_column].mean()), "count": int(len(df))}
    return {"series": series, "summary": summary}
