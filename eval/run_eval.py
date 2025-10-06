import json, os, sys
from pathlib import Path

# Add the project root to Python path BEFORE importing from tools
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import requests
from jsonschema import validate
from tools.xmetric import handle_xmetric
from tools.file_upload import handle_portfolio_upload

def run_xmetric_analysis(BASE):
    schema = json.load(open(BASE/"schemas"/"xmetric.schema.json"))
# sample test
    inp = {"table_name":"sample.csv","date_column":"date","value_column":"close"}
    try:
        out = handle_xmetric(inp, data_root=str(BASE/"data"))
        print("Xmetric output keys:", out.keys())
    # optional validation of result structure (build small schema for output)
    except Exception as e:
        print("ERROR", e)


def test_portfolio_api():
    url = "http://127.0.0.1:8000/xmetric"
    payload = {
    "table_name": "sample.csv",
    "date_column": "date",
    "value_column": "close"
    }
    r = requests.post(url, json=payload)
    print(r.status_code, json.dumps(r.json(), indent=2))

test_portfolio_api()
#run_xmetric_analysis(BASE)