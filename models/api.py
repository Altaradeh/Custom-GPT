from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from tools.xmetric import handle_xmetric

app = FastAPI()

class XReq(BaseModel):
    table_name: str
    date_column: str
    value_column: str
    aggregation: Optional[str] = "none"
    scale_factor: float = 1.0

@app.post("/xmetric")
def xmetric(req: XReq):
    return handle_xmetric(req.dict())
