
from __future__ import annotations

import os, json, math, time, pathlib, random
from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict, Optional

import numpy as np
import pandas as pd


# ==============================
# Parameter Set (attached to a Category / Level)
# ==============================

@dataclass(frozen=True)
class ParamSet:
    param_set_id: str           # e.g., "L03_typical_v1"
    category: str               # e.g., "Typical"
    level_rank: int             # 1..7
    # envelope controls
    drawdown: float             # positive fraction, e.g. 0.30 means -30%
    t_down: int                 # trading days to trough
    t_up: int                   # trading days to recover to 100
    # noise / smoothing
    annual_vol: float = 0.18
    df_returns: int = 5
    tanh_scale: float = 6.0
    # acceptance
    max_daily_return: float = 0.08
    min_crisis_len: int = 20
    seed_base: int = 42

    def to_json(self) -> dict:
        d = asdict(self)
        d["envelope_asym"] = round(self.t_up / max(1, self.t_down), 3)
        return d


# ==============================
# Core Path Generator
# ==============================

def _generate_full_path(ps: ParamSet, seed: int) -> pd.Series:
    """Generate full path from day 0 .. t_down+t_up-1 that starts at 100, hits trough at t_down, ends at 100.
    Noise is Student-t daily returns with tanh soft clipping, anchored via a bridge so endpoints are preserved."""
    rng = np.random.default_rng(seed)
    total = ps.t_down + ps.t_up
    trough = 100 * (1 - ps.drawdown)

    # Deterministic envelope
    env_down = 100 + (trough - 100) * np.linspace(0.0, 1.0, ps.t_down, endpoint=False)
    env_up = trough + (100 - trough) * np.linspace(0.0, 1.0, ps.t_up)
    env = np.concatenate([env_down, env_up])

    # Fat‑tailed daily innovations
    daily_vol = ps.annual_vol / np.sqrt(250.0)
    raw_r = rng.standard_t(ps.df_returns, size=total) * daily_vol
    sm_r = np.tanh(ps.tanh_scale * raw_r) / ps.tanh_scale

    # Bridge: cumulative returns, then remove linear drift so start/trough/end match envelope endpoints
    cum = 100 * np.cumprod(1 + sm_r)
    cum -= cum[0]
    bridge = cum - np.linspace(0, 1, total) * cum[-1]

    path = env + bridge
    path[0], path[ps.t_down-1], path[ps.t_down], path[-1] = 100.0, np.nan, trough, 100.0  # ps.t_down-1 not fixed
    return pd.Series(path, name="price")


def _crisis_window(path: pd.Series, ps: ParamSet) -> Tuple[pd.Series, bool]:
    """Return crisis window [first<100 .. first>=100] and acceptance flag."""
    below = np.where(path.values < 100.0)[0]
    if len(below) == 0:
        return path, False
    first_below = int(below[0])

    ge = np.where(path.values[first_below:] >= 100.0)[0]
    if len(ge) == 0:
        return path.iloc[first_below:], False
    recovery = first_below + int(ge[0])

    crisis = path.iloc[first_below: recovery + 1].reset_index(drop=True)

    # Acceptance rules
    if len(crisis) < ps.min_crisis_len:
        return crisis, False
    if crisis.pct_change().abs().max() > ps.max_daily_return:
        return crisis, False
    return crisis, True


# ==============================
# Library Generation
# ==============================

def generate_paths_for_param_set(ps: ParamSet, target: int, out_dir: str, chunk: int = 1000) -> Dict[str, str]:
    """Generate accepted crisis paths for a single ParamSet and write two CSVs: series.csv and meta.csv.
    Returns dict with file paths.
    """
    out_dir = os.path.join(out_dir, ps.param_set_id)
    os.makedirs(out_dir, exist_ok=True)

    series_path = os.path.join(out_dir, "series.csv")
    meta_path = os.path.join(out_dir, "meta.csv")
    params_json = os.path.join(out_dir, "PARAMS.json")

    # Save params for provenance
    with open(params_json, "w") as f:
        json.dump({**ps.to_json(), "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, f, indent=2)

    # Create CSVs with headers
    with open(series_path, "w") as f:
        f.write("param_set_id,category,level_rank,path_id,t_day,price\n")
    with open(meta_path, "w") as f:
        f.write("param_set_id,category,level_rank,path_id,seed,drawdown,t_down,t_up,annual_vol,df_returns,tanh_scale,max_daily_return,min_crisis_len,envelope_asym\n")

    accepted = 0
    rejected = 0
    seed = ps.seed_base

    # Generate until target accepted
    buffer_rows_series = []
    buffer_rows_meta = []
    path_id = 0

    while accepted < target:
        full = _generate_full_path(ps, seed)
        crisis, ok = _crisis_window(full, ps)
        if ok:
            # write series rows
            for t, val in enumerate(crisis.values.tolist()):
                buffer_rows_series.append(f"{ps.param_set_id},{ps.category},{ps.level_rank},{path_id},{t},{val:.8f}\n")
            # write meta row
            envelope_asym = ps.t_up / max(1, ps.t_down)
            buffer_rows_meta.append(f"{ps.param_set_id},{ps.category},{ps.level_rank},{path_id},{seed},{ps.drawdown},{ps.t_down},{ps.t_up},{ps.annual_vol},{ps.df_returns},{ps.tanh_scale},{ps.max_daily_return},{ps.min_crisis_len},{envelope_asym:.6f}\n")

            accepted += 1
            path_id += 1
        else:
            rejected += 1

        # Flush buffers occasionally
        if len(buffer_rows_series) >= chunk * 100:  # rough size heuristic
            with open(series_path, "a") as f:
                f.writelines(buffer_rows_series)
            buffer_rows_series.clear()
        if len(buffer_rows_meta) >= chunk:
            with open(meta_path, "a") as f:
                f.writelines(buffer_rows_meta)
            buffer_rows_meta.clear()

        seed += 1

    # Final flush
    if buffer_rows_series:
        with open(series_path, "a") as f:
            f.writelines(buffer_rows_series)
    if buffer_rows_meta:
        with open(meta_path, "a") as f:
            f.writelines(buffer_rows_meta)

    return {"series": series_path, "meta": meta_path, "params": params_json, "accepted": accepted, "rejected": rejected}


# ==============================
# Built-in Parameter Grid (7 levels, one canonical set each; extend as needed)
# ==============================

def default_param_sets() -> List[ParamSet]:
    """One canonical ParamSet per level. You can extend with variants per level if desired."""
    sets = [
        # level 1: Small (<25%)
        ParamSet("L01_small_v1", "Small", 1, drawdown=0.22, t_down=35, t_up=int(35*1.3), annual_vol=0.18, df_returns=6, tanh_scale=7.0),
        # level 2: Small–Typical
        ParamSet("L02_small_typical_v1", "Small–Typical", 2, drawdown=0.26, t_down=50, t_up=int(50*1.5), annual_vol=0.19, df_returns=6, tanh_scale=7.0),
        # level 3: Typical (25–35%)
        ParamSet("L03_typical_v1", "Typical", 3, drawdown=0.32, t_down=65, t_up=int(65*1.6), annual_vol=0.19, df_returns=5, tanh_scale=6.0),
        # level 4: Typical–Large
        ParamSet("L04_typical_large_v1", "Typical–Large", 4, drawdown=0.38, t_down=85, t_up=int(85*1.8), annual_vol=0.20, df_returns=5, tanh_scale=6.0),
        # level 5: Large (35–45%)
        ParamSet("L05_large_v1", "Large", 5, drawdown=0.43, t_down=95, t_up=int(95*2.0), annual_vol=0.21, df_returns=5, tanh_scale=6.0),
        # level 6: Large–Major
        ParamSet("L06_large_major_v1", "Large–Major", 6, drawdown=0.50, t_down=110, t_up=int(110*2.2), annual_vol=0.22, df_returns=4, tanh_scale=6.0),
        # level 7: Major (>45%)
        ParamSet("L07_major_v1", "Major", 7, drawdown=0.57, t_down=126, t_up=int(126*2.8), annual_vol=0.22, df_returns=4, tanh_scale=6.0),
    ]
    return sets


# ==============================
# Summary (Mean / P10 / P90) and Resampling
# ==============================

def _smooth_series(y: pd.Series, window: int = 11) -> pd.Series:
    """Simple centered moving-average smoother; fall back to ewm at edges."""
    window = max(3, window | 1)  # odd window
    sm = y.rolling(window, center=True, min_periods=1).mean()
    # Light exponential smoothing for remaining wiggles
    sm = sm.ewm(alpha=0.2, adjust=False).mean()
    return sm


def compute_summaries(series_df: pd.DataFrame, n_paths: int = 100, random_state: Optional[int] = None) -> pd.DataFrame:
    """Compute smoothed mean / P10 / P90 for a random sample of path_ids in series_df (one param_set_id at a time).
    Expects columns: ['path_id','t_day','price'] (and ignores others)."""
    rng = np.random.default_rng(random_state)
    path_ids = series_df['path_id'].unique().tolist()
    if len(path_ids) == 0:
        raise ValueError("No paths found in series_df.")
    pick = rng.choice(path_ids, size=min(n_paths, len(path_ids)), replace=False)
    sub = series_df[series_df['path_id'].isin(pick)]

    # pivot to matrix [t x paths]
    mat = sub.pivot(index='t_day', columns='path_id', values='price').sort_index()
    stats = pd.DataFrame({
        'mean': mat.mean(axis=1),
        'p10': mat.quantile(0.10, axis=1),
        'p90': mat.quantile(0.90, axis=1),
    })
    stats = stats.apply(_smooth_series)

    return stats.reset_index()


def monthly_table(stats: pd.DataFrame, max_rows: int = 16) -> pd.DataFrame:
    """Resample to monthly (~21 trading days). Stop at first time the *mean* regains 100 or max_rows."""
    stats = stats.copy()
    # find first index where mean >= 100
    rec_idx = int((stats['mean'] >= 100.0).idxmax()) if (stats['mean'] >= 100.0).any() else stats.index[-1]
    stats = stats.loc[:rec_idx]

    # take every ~21st day
    step = 21
    idx = list(range(0, len(stats), step))
    if idx[-1] != len(stats) - 1:
        idx.append(len(stats) - 1)
    mnth = stats.iloc[idx].reset_index(drop=True)

    # clamp rows
    if len(mnth) > max_rows:
        mnth = mnth.iloc[:max_rows].reset_index(drop=True)

    # Add month counter starting at 0
    mnth.insert(0, 'month', range(len(mnth)))
    return mnth


# ==============================
# Convenience: Build a small demo library (for a couple of levels)
# ==============================

def build_demo_library(out_root: str, target_per_set: int = 150, levels: List[int] = [3,4], random_state: int = 123) -> Dict[str, Dict[str, str]]:
    """Generate a small demonstration library for a couple of levels (default: 3 and 4).
    Returns mapping param_set_id -> file paths."""
    sets = {ps.level_rank: ps for ps in default_param_sets()}
    results = {}
    for L in levels:
        ps = sets[L]
        res = generate_paths_for_param_set(ps, target=target_per_set, out_dir=out_root)
        results[ps.param_set_id] = res
    return results


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Short-term crisis path generator (CSV library).")
    ap.add_argument("--out", type=str, required=True, help="Output root directory")
    ap.add_argument("--level", type=int, choices=list(range(1,8)), help="Level rank 1..7; if omitted, all levels")
    ap.add_argument("--target", type=int, default=5000, help="Accepted paths per parameter set")
    args = ap.parse_args()

    sets = default_param_sets()
    if args.level:
        sets = [ps for ps in sets if ps.level_rank == args.level]

    for ps in sets:
        print(f"Generating for {ps.param_set_id} ({ps.category}) -> {args.target} accepted paths")
        info = generate_paths_for_param_set(ps, target=args.target, out_dir=args.out)
        print(json.dumps(info, indent=2))
