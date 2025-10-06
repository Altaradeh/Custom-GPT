"""
Run API on multiple ports for separate ngrok tunnels
Usage: python run_api_multi_port.py [port]
"""
import sys
import uvicorn
from models.api import app

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    
    print(f"🚀 Starting Financial Analytics API on port {port}")
    print(f"🌐 Server: http://localhost:{port}")
    print(f"📖 Docs: http://localhost:{port}/docs")
    
    uvicorn.run(
        "models.api:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=["models", "tools"]
    )
