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

class PortfolioHoldingInput(BaseModel):
    """Input model for portfolio holdings - allows any positive weight value"""
    ticker: str = Field(..., description="Stock ticker symbol")
    weight: float = Field(..., ge=0, description="Portfolio weight (can be percentage or decimal)")

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

class PortfolioDataRequest(BaseModel):
    """Request model for portfolio data sent directly as JSON"""
    holdings: List[PortfolioHoldingInput] = Field(..., description="List of portfolio holdings")
    normalize_weights: bool = Field(True, description="Whether to normalize weights to sum to 1.0")

class CSVDataPoint(BaseModel):
    """Single row of CSV data"""
    data: dict = Field(..., description="Row data as key-value pairs")

class XMetricDataRequest(BaseModel):
    """Request for xmetric analysis with inline CSV data"""
    csv_data: List[dict] = Field(..., description="List of row dictionaries from CSV")
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

class YMetricDataRequest(BaseModel):
    """Request for ymetric analysis with inline CSV data"""
    csv_data: List[dict] = Field(..., description="List of row dictionaries from CSV")
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

# API Endpoints

@app.get("/")
async def root():
    """Health check and API information"""
    return {
        "message": "Financial Analytics Custom GPT API",
        "version": "1.0.0",
        "endpoints": [
            "/xmetric - Primary time series analysis (server files)",
            "/xmetric/data - Primary analysis (user uploaded CSV data)",
            "/ymetric - Secondary metrics analysis (server files)", 
            "/ymetric/data - Secondary analysis (user uploaded CSV data)",
            "/portfolio/upload - Portfolio processing (server files)",
            "/portfolio/data - Portfolio processing (user uploaded data)",
            "/data/files - List available server files"
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

@app.post("/xmetric/data", response_model=MetricResponse)
async def xmetric_from_data(request: XMetricDataRequest):
    """
    XMetric from Data: Analyze CSV data sent directly from ChatGPT
    Use this when user uploads a CSV file to ChatGPT
    """
    try:
        import pandas as pd
        
        # Convert CSV data to DataFrame
        df = pd.DataFrame(request.csv_data)
        
        # Validate required columns exist
        if request.date_column not in df.columns:
            raise ValueError(f"Date column '{request.date_column}' not found. Available columns: {list(df.columns)}")
        if request.value_column not in df.columns:
            raise ValueError(f"Value column '{request.value_column}' not found. Available columns: {list(df.columns)}")
        
        # Process the data
        df[request.date_column] = pd.to_datetime(df[request.date_column])
        df = df.sort_values(request.date_column)
        
        # Apply aggregation
        agg_func = request.aggregation
        if agg_func != "none":
            df = df.groupby(request.date_column)[request.value_column].agg(agg_func).reset_index()
        else:
            df = df[[request.date_column, request.value_column]]
        
        # Apply scaling
        df[request.value_column] = df[request.value_column] * request.scale_factor
        
        # Build response
        series = [
            {"date": row[request.date_column].strftime("%Y-%m-%d"), "value": float(row[request.value_column])}
            for _, row in df.iterrows()
        ]
        
        summary = {
            "mean": float(df[request.value_column].mean()),
            "count": len(df)
        }
        
        return MetricResponse(series=series, summary=summary)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/ymetric/data", response_model=MetricResponse)
async def ymetric_from_data(request: YMetricDataRequest):
    """
    YMetric from Data: Analyze CSV data sent directly from ChatGPT
    Use this when user uploads a CSV file to ChatGPT
    """
    try:
        import pandas as pd
        
        # Convert CSV data to DataFrame
        df = pd.DataFrame(request.csv_data)
        
        # Validate required columns exist
        if request.date_column not in df.columns:
            raise ValueError(f"Date column '{request.date_column}' not found. Available columns: {list(df.columns)}")
        if request.value_column not in df.columns:
            raise ValueError(f"Value column '{request.value_column}' not found. Available columns: {list(df.columns)}")
        
        # Process the data
        df[request.date_column] = pd.to_datetime(df[request.date_column])
        df = df.sort_values(request.date_column)
        
        # Apply aggregation
        agg_func = request.aggregation
        if agg_func != "none":
            df = df.groupby(request.date_column)[request.value_column].agg(agg_func).reset_index()
        else:
            df = df[[request.date_column, request.value_column]]
        
        # Apply scaling
        df[request.value_column] = df[request.value_column] * request.scale_factor
        
        # Build response
        series = [
            {"date": row[request.date_column].strftime("%Y-%m-%d"), "value": float(row[request.value_column])}
            for _, row in df.iterrows()
        ]
        
        summary = {
            "mean": float(df[request.value_column].mean()),
            "count": len(df)
        }
        
        return MetricResponse(series=series, summary=summary)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/portfolio/upload", response_model=PortfolioResponse)
async def portfolio_upload(request: PortfolioUploadRequest):
    """
    Portfolio Upload: Process portfolio files with weight normalization
    """
    try:
        result = handle_portfolio_upload(request.dict(), data_root="data")
        return PortfolioResponse(**result)
    except FileNotFoundError as e:
        # Return helpful error with available files
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid portfolio data: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/portfolio/data", response_model=PortfolioResponse)
async def portfolio_from_data(request: PortfolioDataRequest):
    """
    Portfolio Data: Process portfolio data sent directly as JSON
    Use this when ChatGPT reads a user's uploaded file and sends the data
    """
    try:
        # Convert the holdings to a format we can process
        import pandas as pd
        df = pd.DataFrame([{"ticker": h.ticker, "weight": h.weight} for h in request.holdings])
        
        # Validate weights
        if len(df) == 0:
            raise ValueError("No portfolio data provided")
        
        total_weight = df["weight"].sum()
        if total_weight <= 0:
            raise ValueError("Total portfolio weights must be positive")
        
        # Normalize if requested
        was_normalized = False
        if request.normalize_weights and abs(total_weight - 1.0) > 0.001:
            df["weight"] = df["weight"] / total_weight
            was_normalized = True
        
        rows = df.to_dict(orient="records")
        
        return PortfolioResponse(
            rows=rows,
            normalized=was_normalized,
            total_holdings=len(rows)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
            }, data_root="data")
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
                "endpoints": {
                    "server_files": "/xmetric",
                    "user_uploads": "/xmetric/data"
                },
                "method": "POST"
            },
            "ymetric": {
                "description": "Secondary metrics and cross-sectional analysis",
                "endpoints": {
                    "server_files": "/ymetric",
                    "user_uploads": "/ymetric/data"
                },
                "method": "POST"
            },
            "portfolio": {
                "description": "Portfolio file processing with weight normalization",
                "endpoints": {
                    "server_files": "/portfolio/upload",
                    "user_uploads": "/portfolio/data"
                },
                "method": "POST"
            }
        },
        "usage": {
            "server_files": "Use /xmetric, /ymetric, /portfolio/upload for files in server's /data folder",
            "user_uploads": "Use /xmetric/data, /ymetric/data, /portfolio/data for files uploaded to ChatGPT"
        }
    }

@app.get("/data/files")
async def list_data_files():
    """List available data files in the data directory"""
    try:
        data_dir = Path("data")
        if not data_dir.exists():
            return {"files": [], "message": "Data directory not found"}
        
        files = []
        for file_path in data_dir.glob("*.csv"):
            files.append({
                "name": file_path.stem,  # filename without extension
                "full_name": file_path.name,
                "type": "csv",
                "size_bytes": file_path.stat().st_size
            })
        for file_path in data_dir.glob("*.parquet"):
            files.append({
                "name": file_path.stem,
                "full_name": file_path.name,
                "type": "parquet",
                "size_bytes": file_path.stat().st_size
            })
        
        return {
            "files": files,
            "count": len(files),
            "message": f"Found {len(files)} data file(s)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
