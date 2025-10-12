from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
import tempfile
import os
import json
from typing import List

from helpers import (
    get_stock_history,
    get_products_by_company,
    trace_supply_chain,
    scenario_trace,
    FUNCTION_DEFINITIONS,
)
from schema import (
    StockHistoryResponse,
    ProductsResponse,
    TraceResponse,
)

router = APIRouter(prefix="/supply-chain", tags=["SupplyChain"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/functions")
def functions() -> List[dict]:
    """Return function definitions usable by LLMs."""
    return FUNCTION_DEFINITIONS


@router.get("/stock-history", response_model=StockHistoryResponse)
def stock_history(
    ticker: str = Query(..., description="Stock ticker symbol"),
    period: str = Query("1y", description="Data period"),
    interval: str = Query("1d", description="Data interval"),
):
    try:
        return get_stock_history(ticker, period, interval)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products", response_model=ProductsResponse)
def products(ticker: str = Query(..., description="Company ticker")):
    try:
        df = get_products_by_company(ticker.upper())
        return {"products": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trace", response_model=TraceResponse)
def trace(
    product: str = Query(..., description="Input product name"),
    depth: str = Query("2", description="Trace depth"),
):
    try:
        result = trace_supply_chain(product, depth)
        if result.get("error"):
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ---------------------------------------------------------------------------------------------------------------------------------------------------
# --------------------------- TO BE CHANGED: remove this import and add actual authorisation/ db calls to fetch portfolio ---------------------------
# ---------------------------------------------------------------------------------------------------------------------------------------------------
from auth import login_required 

@router.post("/scenario-trace")
async def scenario_trace_endpoint(
    request: Request,
    query: str = Form(None),
    depth: int = Form(2),
    portfolio: UploadFile = File(None),
    user: dict = Depends(login_required),
):
    """
    Supports both JSON and multipart/form-data for running scenario_trace.
    """

    # Handle JSON input if Content-Type is application/json
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            data = await request.json()
            query = data.get("query")
            depth = int(data.get("depth", 2))
            portfolio_path = data.get("portfolio_path", None)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
    else:
        portfolio_path = None
        if portfolio:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp:
                    tmp.write(await portfolio.read())
                    portfolio_path = tmp.name
            except Exception as e:
                raise HTTPException(status_code=500, detail="Error saving uploaded file")

    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    try:
        result = scenario_trace(query, depth, portfolio_path)
    finally:
        # Clean up the temp portfoli file
        if portfolio_path and os.path.exists(portfolio_path):
            try:
                os.remove(portfolio_path)
            except Exception:
                pass

    return JSONResponse(content=result)
# --------------------------- TO BE CHANGED: remove this import and add actual authorisation/ db calls to fetch portfolio ---------------------------