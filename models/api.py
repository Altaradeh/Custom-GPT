"""
FastAPI application for Custom GPT MCP tools
Provides REST API wrappers around the MCP tool implementations
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import tempfile
import os
from pathlib import Path

# Import tool handlers
from tools.xmetric import handle_xmetric, XMetricInput
from tools.ymetric import handle_ymetric, YMetricInput  
from tools.file_upload import handle_portfolio_upload, PortfolioUploadInput

# Initialize FastAPI app
app = FastAPI(
    title="Financial Analytics Custom GPT API",
    description="REST API for XMetric, YMetric, and Portfolio analysis tools",
    version="1.0.0"
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response models
class TimeSeriesDataPoint(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    value: float = Field(..., description="Numeric value")

class MetricSummary(BaseModel):
    mean: float = Field(..., description="Mean of all values")
    count: int = Field(..., description="Number of data points")

class MetricResponse(BaseModel):
    series: List[TimeSeriesDataPoint] = Field(..., description="Time series data points")
    summary: MetricSummary = Field(..., description="Statistical summary")

class PortfolioHolding(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")
    weight: float = Field(..., ge=0, le=1, description="Portfolio weight (0-1)")

class PortfolioResponse(BaseModel):
    rows: List[PortfolioHolding] = Field(..., description="Portfolio holdings")
    normalized: bool = Field(..., description="Whether weights were normalized")
    total_holdings: int = Field(..., description="Number of holdings")

# Enhanced request models with validation
class XMetricRequest(BaseModel):
    table_name: str = Field(..., description="Name of CSV/Parquet file in data directory")
    date_column: str = Field(..., description="Column name containing date values")
    value_column: str = Field(..., description="Column name containing numeric values")
    aggregation: str = Field("none", description="Aggregation method")
    scale_factor: float = Field(1.0, ge=0, description="Scaling factor")
    
    @validator('aggregation')
    def validate_aggregation(cls, v):
        allowed = ["none", "sum", "mean", "max", "min"]
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"Aggregation must be one of: {allowed} (case-insensitive)")
        return v_lower

class YMetricRequest(BaseModel):
    table_name: str = Field(..., description="Name of CSV/Parquet file in data directory")
    date_column: str = Field(..., description="Column name containing date values")
    value_column: str = Field(..., description="Column name containing numeric values")
    aggregation: str = Field("none", description="Aggregation method")
    scale_factor: float = Field(1.0, ge=0, description="Scaling factor")
    
    @validator('aggregation')
    def validate_aggregation(cls, v):
        allowed = ["none", "sum", "mean", "max", "min"]
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"Aggregation must be one of: {allowed} (case-insensitive)")
        return v_lower

class PortfolioUploadRequest(BaseModel):
    file_path: str = Field(..., description="Path to portfolio CSV/XLSX file")
    normalize_weights: bool = Field(True, description="Whether to normalize weights to sum to 1.0")

# API Endpoints

@app.get("/")
async def root():
    """Health check and API information"""
    return {
        "message": "Financial Analytics Custom GPT API",
        "version": "1.0.0",
        "endpoints": [
            "/xmetric - Primary time series analysis",
            "/ymetric - Secondary metrics analysis", 
            "/portfolio/upload - Portfolio file processing",
            "/portfolio/upload-file - File upload endpoint"
        ]
    }

@app.post("/xmetric", response_model=MetricResponse)
async def xmetric_analysis(request: XMetricRequest):
    """
    XMetric: Primary time-series analysis with aggregation and scaling
    """
    try:
        result = handle_xmetric(request.dict(), data_root="data")
        return MetricResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Data file not found: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/ymetric", response_model=MetricResponse)
async def ymetric_analysis(request: YMetricRequest):
    """
    YMetric: Secondary metrics and cross-sectional analysis
    """
    try:
        result = handle_ymetric(request.dict(), data_root="data")
        return MetricResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Data file not found: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/portfolio/upload", response_model=PortfolioResponse)
async def portfolio_upload(request: PortfolioUploadRequest):
    """
    Portfolio Upload: Process portfolio files with weight normalization
    """
    try:
        result = handle_portfolio_upload(request.dict())
        return PortfolioResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Portfolio file not found: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid portfolio data: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/portfolio/upload-file", response_model=PortfolioResponse)
async def portfolio_upload_file(file: UploadFile = File(...), normalize_weights: bool = True):
    """
    Portfolio File Upload: Upload portfolio file directly via multipart form
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="File must be CSV or Excel format")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Process the uploaded file
            result = handle_portfolio_upload({
                "file_path": tmp_file_path,
                "normalize_weights": normalize_weights
            })
            return PortfolioResponse(**result)
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload error: {str(e)}")

# Additional utility endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "api": "Financial Analytics Custom GPT"}

@app.get("/tools")
async def list_tools():
    """List available MCP tools and their descriptions"""
    return {
        "tools": {
            "xmetric": {
                "description": "Primary time-series analysis with aggregation and scaling",
                "endpoint": "/xmetric",
                "method": "POST"
            },
            "ymetric": {
                "description": "Secondary metrics and cross-sectional analysis",
                "endpoint": "/ymetric", 
                "method": "POST"
            },
            "portfolio_upload": {
                "description": "Portfolio file processing with weight normalization",
                "endpoints": ["/portfolio/upload", "/portfolio/upload-file"],
                "method": "POST"
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
