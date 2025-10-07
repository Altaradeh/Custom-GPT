"""
FastAPI Application for Long-Term Financial Path Simulations
=============================================================

This application serves pre-computed long-term financial market simulation data
through RESTful API endpoints designed for ChatGPT integration.

Key Features:
- Hybrid approach: numerical data + semantic categories
- ChatGPT function calling compatibility
- Dockerized deployment ready
- Stateless and performant data serving
- Short-Term crisis model: levels (1–7), normal vs fragile baseline, and on-demand demo summaries
Author: Syed Mohsin
Date: August 2025
"""

import os
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Any
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import logging
from functools import lru_cache
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Long-Term Financial Simulation API")
    load_data()
    logger.info("Data loaded successfully")
    yield
    # Shutdown
    logger.info("Shutting down Long-Term Financial Simulation API")

# Initialize FastAPI app
app = FastAPI(
    title="Long-Term Financial Market Simulation API",
    description="""
    This API serves pre-computed long-term financial market simulation data.
    It provides access to thousands of 40-year market path simulations with
    statistical analysis and categorization for easy interpretation.
    
    Features:
    - Scenario discovery and selection
    - Detailed path statistics and analysis
    - Hybrid numerical/semantic data representation
    - Envelope chart data for visualization
    - ChatGPT function calling compatibility
    - Short-Term crisis model: levels (1–7), normal vs fragile baseline, and on-demand demo summaries
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware for web integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data file paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LIBRARY_FILE = DATA_DIR / "final_path_statistics_library.csv"
PARAM_FILE = DATA_DIR / "param_library.csv"
SHORT_TERM_BASELINE_FILE = DATA_DIR / "normal_vs_fragile_table.csv"

# Global data storage
library_df: Optional[pd.DataFrame] = None
param_df: Optional[pd.DataFrame] = None
short_term_baseline_df: Optional[pd.DataFrame] = None

# Optional import of short-term generator utilities
try:
    from short_term_crisis_generator import (
        default_param_sets,
        compute_summaries,
        monthly_table,
        _generate_full_path,
        _crisis_window,
    )
except Exception as _e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Short-term module not fully available: {_e}")
    default_param_sets = None
    compute_summaries = None
    monthly_table = None
    _generate_full_path = None
    _crisis_window = None

# =============================================================================
# Pydantic Models for API Responses
# =============================================================================

class ScenarioInfo(BaseModel):
    """Information about an available scenario"""
    target_mean: float = Field(..., description="Target annual return (e.g., 0.06 for 6%)")
    target_spread: float = Field(..., description="Target risk/spread level")
    description: str = Field(..., description="Human-readable scenario description")
    semantic_category: str = Field(..., description="Semantic category (e.g., 'conservative', 'moderate', 'aggressive')")
    total_paths: int = Field(..., description="Number of paths available for this scenario")

class SummaryStatistics(BaseModel):
    """Aggregate statistics for a scenario"""
    average_annual_return: float = Field(..., description="Mean annual return across all paths")
    average_max_drawdown: float = Field(..., description="Mean maximum drawdown across all paths")
    min_annual_return: float = Field(..., description="Minimum annual return observed")
    max_annual_return: float = Field(..., description="Maximum annual return observed")
    average_lost_decades: float = Field(..., description="Mean number of lost decades")
    total_paths_in_scenario: int = Field(..., description="Total number of paths in this scenario")
    return_category: str = Field(..., description="Semantic return category")
    risk_category: str = Field(..., description="Semantic risk category")
    spread_range: str = Field(..., description="Human-readable spread description")

class EnvelopeChartData(BaseModel):
    """Data for creating envelope/fan charts"""
    years: List[int] = Field(..., description="Time points (years from start)")
    p05_path: List[float] = Field(..., description="5th percentile values over time")
    p50_path: List[float] = Field(..., description="Median (50th percentile) values over time")
    p95_path: List[float] = Field(..., description="95th percentile values over time")

class PathDetail(BaseModel):
    """Individual path statistics"""
    path_id: int = Field(..., description="Unique path identifier")
    actual_annual_return: float = Field(..., description="Actual annual return for this path")
    max_drop: float = Field(..., description="Maximum drawdown for this path")
    lost_decades: int = Field(..., description="Number of lost decades for this path")
    return_category: str = Field(..., description="Semantic return category")
    drawdown_category: str = Field(..., description="Semantic drawdown category")

class ScenarioDataResponse(BaseModel):
    """Complete response for scenario data"""
    scenario_info: ScenarioInfo
    summary_statistics: SummaryStatistics
    envelope_chart_data: EnvelopeChartData
    path_details_table: List[PathDetail]

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: str = Field(..., description="Detailed error information")

# =============================================================================
# Short-Term: Pydantic Models
# =============================================================================

class ShortTermLevelInfo(BaseModel):
    """Short-term crisis param set metadata"""
    param_set_id: str
    category: str
    level_rank: int
    drawdown: float
    t_down: int
    t_up: int
    envelope_asym: float
    annual_vol: float
    df_returns: int
    tanh_scale: float
    max_daily_return: float
    min_crisis_len: int

class ShortTermBaselineRow(BaseModel):
    """Monthly baseline comparison between normal and fragile"""
    month: int
    mean_normal: float
    p10_normal: float
    p90_normal: float
    mean_fragile: float
    p10_fragile: float
    p90_fragile: float

# =============================================================================
# Data Loading and Caching
# =============================================================================

@lru_cache(maxsize=1)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and cache the CSV data files"""
    global library_df, param_df
    
    try:
        # Load main statistics library
        if not LIBRARY_FILE.exists():
            raise FileNotFoundError(f"Library file not found: {LIBRARY_FILE}")
        
        library_df = pd.read_csv(LIBRARY_FILE)
        logger.info(f"Loaded library with {len(library_df)} paths")
        
        # Load parameter library
        if not PARAM_FILE.exists():
            raise FileNotFoundError(f"Parameter file not found: {PARAM_FILE}")
        
        param_df = pd.read_csv(PARAM_FILE)
        logger.info(f"Loaded parameters for {len(param_df)} scenarios")
        
        # Round numeric columns to desired precision
        library_df = library_df.round(2)
        param_df = param_df.round(2)

        return library_df, param_df

    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load data: {str(e)}")

@lru_cache(maxsize=1)
def load_short_term_baseline() -> pd.DataFrame:
    """Load and cache the short-term baseline comparison CSV."""
    global short_term_baseline_df
    try:
        if not SHORT_TERM_BASELINE_FILE.exists():
            raise FileNotFoundError(f"Short-term baseline file not found: {SHORT_TERM_BASELINE_FILE}")
        short_term_baseline_df = pd.read_csv(SHORT_TERM_BASELINE_FILE)
        return short_term_baseline_df
    except Exception as e:
        logger.error(f"Error loading short-term baseline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load short-term baseline: {str(e)}")

# =============================================================================
# Semantic Categorization Functions
# =============================================================================

def categorize_return(annual_return: float) -> str:
    """Categorize annual return into semantic categories"""
    if annual_return < 0.03:
        return "very_low"
    elif annual_return < 0.05:
        return "low"
    elif annual_return < 0.07:
        return "moderate"
    elif annual_return < 0.09:
        return "high"
    else:
        return "very_high"

def categorize_drawdown(max_drop: float) -> str:
    """Categorize maximum drawdown into semantic categories"""
    if max_drop < 0.20:
        return "low"
    elif max_drop < 0.35:
        return "moderate"
    elif max_drop < 0.50:
        return "high"
    else:
        return "very_high"

def categorize_spread(target_spread: float) -> str:
    """Categorize spread into semantic risk categories"""
    if target_spread < 1.5:
        return "conservative"
    elif target_spread < 2.5:
        return "moderate"
    else:
        return "aggressive"

def get_scenario_description(target_mean: float, target_spread: float) -> str:
    """Generate human-readable scenario description"""
    return_pct = target_mean * 100
    risk_category = categorize_spread(target_spread)
    
    return f"{risk_category.title()} Scenario ({return_pct:.1f}% Target Return)"

def get_spread_range_description(target_spread: float) -> str:
    """Get human-readable spread description"""
    if target_spread < 1.5:
        return "Low volatility range"
    elif target_spread < 2.0:
        return "Moderate volatility range"
    elif target_spread < 2.5:
        return "Moderate-high volatility range"
    elif target_spread < 3.0:
        return "High volatility range"
    else:
        return "Very high volatility range"

# =============================================================================
# Utility Functions
# =============================================================================

def generate_envelope_data(df: pd.DataFrame) -> EnvelopeChartData:
    """Generate envelope chart data from path statistics"""
    # For demonstration, create time-series data based on compound growth
    # In a real implementation, you'd need actual path data over time
    
    years = [5, 10, 15, 20, 25, 30, 35, 40]
    
    # Calculate percentiles of final values and work backwards
    annual_returns = df['actual_annual_return'].values
    
    # Calculate compound growth for each percentile
    p05_return = np.percentile(annual_returns, 5)
    p50_return = np.percentile(annual_returns, 50)
    p95_return = np.percentile(annual_returns, 95)
    
    # Generate paths assuming compound growth (starting from 1.0)
    p05_path = [(1.0 * (1 + p05_return) ** year) for year in years]
    p50_path = [(1.0 * (1 + p50_return) ** year) for year in years]
    p95_path = [(1.0 * (1 + p95_return) ** year) for year in years]
    
    return EnvelopeChartData(
        years=years,
        p05_path=p05_path,
        p50_path=p50_path,
        p95_path=p95_path
    )

def get_available_scenarios() -> List[tuple]:
    """Get all available scenario combinations"""
    library_df, param_df = load_data()
    
    scenarios = library_df[['target_mean', 'target_spread']].drop_duplicates()
    return [(row['target_mean'], row['target_spread']) for _, row in scenarios.iterrows()]

# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Long-Term Financial Market Simulation API",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "scenarios": "/long_term/scenarios",
            "paths": "/long_term/paths",
            "short_term_levels": "/short_term/levels",
            "short_term_baseline": "/short_term/baseline",
            "short_term_demo": "/short_term/demo_summary"
        }
    }

@app.get(
    "/long_term/scenarios",
    response_model=List[ScenarioInfo],
    tags=["Long-Term Analysis"],
    summary="List Available Scenarios",
    description="""
    Returns all available target mean/spread combinations with semantic categorization.
    Use this endpoint to discover what scenarios are available for analysis.
    Each scenario represents a different risk/return profile with hundreds of simulation paths.
    """
)
async def get_scenarios(response: Response):
    """
    Get all available scenarios with semantic categorization.
    
    This endpoint is designed for ChatGPT to understand available options
    in semantic terms like 'conservative', 'moderate', 'aggressive'.
    """
    try:
        logger.info("🤖 CHATGPT API CALL: get_scenarios() - Fetching all available investment scenarios")
        library_df, param_df = load_data()
        
        # Get unique scenarios
        scenarios = library_df[['target_mean', 'target_spread']].drop_duplicates()
        
        result = []
        for _, row in scenarios.iterrows():
            target_mean = row['target_mean']
            target_spread = row['target_spread']
            
            # Count paths for this scenario
            path_count = len(library_df[
                (library_df['target_mean'] == target_mean) & 
                (library_df['target_spread'] == target_spread)
            ])
            
            scenario_info = ScenarioInfo(
                target_mean=target_mean,
                target_spread=target_spread,
                description=get_scenario_description(target_mean, target_spread),
                semantic_category=categorize_spread(target_spread),
                total_paths=path_count
            )
            result.append(scenario_info)
        
        # Sort by target_mean, then target_spread
        result.sort(key=lambda x: (x.target_mean, x.target_spread))
        
        # Add custom header to prove this comes from YOUR API
        response.headers["X-Data-Source"] = "Custom-FastAPI-Server-4671-Paths"
        response.headers["X-API-Timestamp"] = str(pd.Timestamp.now())
        
        logger.info(f"🤖 CHATGPT RESPONSE: Returning {len(result)} scenarios from YOUR FastAPI server with 4,671 paths")
        return result
        
    except Exception as e:
        logger.error(f"Error in get_scenarios: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get(
    "/long_term/paths",
    response_model=ScenarioDataResponse,
    tags=["Long-Term Analysis"],
    summary="Get Detailed Scenario Data",
    description="""
    Returns comprehensive data for a specific scenario including:
    - Summary statistics with semantic categorization
    - Envelope chart data for visualization
    - Individual path details with categories
    
    This endpoint provides all data needed to analyze and visualize a scenario.
    It includes both numerical precision and semantic categories for ChatGPT interaction.
    """
)
async def get_scenario_data(
    mean: float = Query(
        ..., 
        description="Target mean annual return (e.g., 0.06 for 6%)",
        ge=0.0,
        le=0.20,
        examples=[0.06]
    ),
    spread: float = Query(
        ..., 
        description="Target spread/risk level",
        ge=0.5,
        le=5.0,
        examples=[1.5]
    )
):
    """
    Get comprehensive data for a specific scenario.
    
    This endpoint filters the path library by target mean and spread,
    then returns aggregated statistics, envelope data, and individual path details
    with both numerical precision and semantic categorization.
    """
    try:
        logger.info(f"🤖 CHATGPT API CALL: analyze_scenario(mean={mean}, spread={spread}) - Analyzing specific investment scenario")
        library_df, param_df = load_data()
        
        # Filter data for the requested scenario
        scenario_df = library_df[
            (library_df['target_mean'] == mean) & 
            (library_df['target_spread'] == spread)
        ]
        
        if scenario_df.empty:
            available_scenarios = get_available_scenarios()
            raise HTTPException(
                status_code=404, 
                detail=f"No data found for mean={mean}, spread={spread}. "
                       f"Available scenarios: {available_scenarios}"
            )
        
        # Create scenario info
        scenario_info = ScenarioInfo(
            target_mean=mean,
            target_spread=spread,
            description=get_scenario_description(mean, spread),
            semantic_category=categorize_spread(spread),
            total_paths=len(scenario_df)
        )
        
        # Calculate summary statistics
        summary_stats = SummaryStatistics(
            average_annual_return=float(scenario_df['actual_annual_return'].mean()),
            average_max_drawdown=float(scenario_df['max_drop'].mean()),
            min_annual_return=float(scenario_df['actual_annual_return'].min()),
            max_annual_return=float(scenario_df['actual_annual_return'].max()),
            average_lost_decades=float(scenario_df['lost_decades'].mean()),
            total_paths_in_scenario=len(scenario_df),
            return_category=categorize_return(scenario_df['actual_annual_return'].mean()),
            risk_category=categorize_spread(spread),
            spread_range=get_spread_range_description(spread)
        )
        
        # Generate envelope chart data
        envelope_data = generate_envelope_data(scenario_df)
        
        # Create path details (limit to first 50 for performance)
        path_details = []
        for _, row in scenario_df.head(50).iterrows():
            path_detail = PathDetail(
                path_id=int(row['path_id']),
                actual_annual_return=float(row['actual_annual_return']),
                max_drop=float(row['max_drop']),
                lost_decades=int(row['lost_decades']),
                return_category=categorize_return(row['actual_annual_return']),
                drawdown_category=categorize_drawdown(row['max_drop'])
            )
            path_details.append(path_detail)
        
        response = ScenarioDataResponse(
            scenario_info=scenario_info,
            summary_statistics=summary_stats,
            envelope_chart_data=envelope_data,
            path_details_table=path_details
        )
        
        logger.info(f"Returned data for scenario: mean={mean}, spread={spread}, paths={len(scenario_df)}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_scenario_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    try:
        library_df, param_df = load_data()
        return {
            "status": "healthy",
            "library_paths": len(library_df) if library_df is not None else 0,
            "parameter_scenarios": len(param_df) if param_df is not None else 0,
            "available_scenarios": len(get_available_scenarios())
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# =============================================================================
# Short-Term Endpoints
# =============================================================================

@app.get(
    "/short_term/levels",
    response_model=List[ShortTermLevelInfo],
    tags=["Short-Term Analysis"],
    summary="List Short-Term Crisis Levels",
    description="Returns the default 7 short-term crisis parameter levels and metadata."
)
async def get_short_term_levels():
    if default_param_sets is None:
        raise HTTPException(status_code=500, detail="Short-term generator module unavailable")
    try:
        levels = []
        for ps in default_param_sets():
            levels.append(ShortTermLevelInfo(
                param_set_id=ps.param_set_id,
                category=ps.category,
                level_rank=ps.level_rank,
                drawdown=ps.drawdown,
                t_down=ps.t_down,
                t_up=ps.t_up,
                envelope_asym=round(ps.t_up / max(1, ps.t_down), 6),
                annual_vol=ps.annual_vol,
                df_returns=ps.df_returns,
                tanh_scale=ps.tanh_scale,
                max_daily_return=ps.max_daily_return,
                min_crisis_len=ps.min_crisis_len,
            ))
        levels.sort(key=lambda x: x.level_rank)
        return levels
    except Exception as e:
        logger.error(f"Error in get_short_term_levels: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/short_term/baseline",
    response_model=List[ShortTermBaselineRow],
    tags=["Short-Term Analysis"],
    summary="Baseline: Normal vs Fragile Monthly Table",
    description="Serves the precomputed monthly comparison between 'normal' and 'fragile' regimes."
)
async def get_short_term_baseline():
    df = load_short_term_baseline()
    expected_cols = [
        'month','mean_normal','p10_normal','p90_normal','mean_fragile','p10_fragile','p90_fragile'
    ]
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise HTTPException(status_code=500, detail=f"Baseline CSV missing columns: {missing}")
    return [ShortTermBaselineRow(**{k: (int(v) if k=='month' else float(v)) for k, v in row.items()})
            for row in df[expected_cols].to_dict(orient='records')]

@app.get(
    "/short_term/demo_summary",
    tags=["Short-Term Analysis"],
    summary="Generate demo summary for a level",
    description="Generates a small in-memory set of acceptable crisis paths for a given level and returns smoothed stats and a monthly table."
)
async def short_term_demo_summary(
    level: int = Query(3, ge=1, le=7, description="Short-term level rank 1..7 (default 3)"),
    n_paths: int = Query(50, ge=10, le=200, description="Number of accepted crisis paths to sample (10..200)"),
    random_state: Optional[int] = Query(None, description="Optional RNG seed for reproducibility")
):
    # Validate module availability
    if any(x is None for x in (_generate_full_path, _crisis_window, compute_summaries, monthly_table, default_param_sets)):
        raise HTTPException(status_code=500, detail="Short-term generator utilities unavailable")

    try:
        # Pick param set for level
        ps_map = {ps.level_rank: ps for ps in default_param_sets()}
        if level not in ps_map:
            raise HTTPException(status_code=404, detail=f"Level {level} not found")
        ps = ps_map[level]

        # Generate accepted crisis windows until n_paths
        accepted = 0
        seed = ps.seed_base
        rows = []
        while accepted < n_paths:
            series = _generate_full_path(ps, seed)
            crisis, ok = _crisis_window(series, ps)
            seed += 1
            if not ok:
                continue
            for t, price in enumerate(crisis.values.tolist()):
                rows.append({"path_id": accepted, "t_day": t, "price": float(price)})
            accepted += 1

        # Build DataFrame and compute summaries
        series_df = pd.DataFrame(rows)
        stats = compute_summaries(series_df, n_paths=min(n_paths, 100), random_state=random_state)
        mn_table = monthly_table(stats)

        return {
            "param_set": {
                "param_set_id": ps.param_set_id,
                "category": ps.category,
                "level_rank": ps.level_rank,
                "drawdown": ps.drawdown,
                "t_down": ps.t_down,
                "t_up": ps.t_up,
                "envelope_asym": round(ps.t_up / max(1, ps.t_down), 6),
            },
            "stats": stats.to_dict(orient='records'),
            "monthly_table": mn_table.to_dict(orient='records')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating short-term demo summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate demo summary: {e}")

# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request, exc):
    """Handle file not found errors"""
    return HTTPException(
        status_code=500,
        detail=f"Required data file not found: {str(exc)}"
    )

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle value errors"""
    return HTTPException(
        status_code=400,
        detail=f"Invalid input value: {str(exc)}"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
