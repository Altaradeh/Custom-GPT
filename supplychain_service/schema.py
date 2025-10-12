from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class StockHistoryRequest(BaseModel):
    ticker: str
    period: str = "1y"
    interval: str = "1d"

class StockHistoryResponse(BaseModel):
    sub_type: str
    prices: List[Dict[str, Any]]
    xKey: str
    yKey: str
    ticker: str
    period: str
    interval: str

class ProductsResponse(BaseModel):
    products: List[Dict[str, Any]]

class TraceResponse(BaseModel):
    product: str
    trace_depth: str
    results: Optional[List[Dict[str, Any]]]
    tier_1_locations: Optional[List[Dict[str, Any]]]
    main_product_locations: Optional[List[Dict[str, Any]]]
    tier_2_product: Optional[str]
    main_products_info: Optional[List[Dict[str, Any]]]
