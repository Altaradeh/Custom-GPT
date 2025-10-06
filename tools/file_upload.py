from pathlib import Path
import pandas as pd

def handle_portfolio_upload(path: str) -> dict:
    p = Path(path)
    if p.suffix in (".xls", ".xlsx"):
        df = pd.read_excel(p)
    else:
        df = pd.read_csv(p)
    # normalize column names
    df.columns = [c.strip().lower() for c in df.columns]
    if "ticker" not in df.columns or "weight" not in df.columns:
        raise ValueError("Expect columns 'ticker' and 'weight'")
    df = df[["ticker","weight"]].dropna()
    df["weight"] = df["weight"].astype(float)
    s = df["weight"].sum()
    if s == 0:
        raise ValueError("Weights sum to zero")
    df["weight"] = df["weight"] / s
    rows = df.to_dict(orient="records")
    return {"rows": rows, "normalized": True}
